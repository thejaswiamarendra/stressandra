import argparse
import threading
import time
from stressandra import stress, jmx
import pkg_resources
import yaml
import datetime
import os
from tqdm import tqdm
from cassandra import ConsistencyLevel
import re
from cassandra.cluster import Cluster
from .jmx import JMXMetrics
from .db import get_session
from .config import Config

class Stressandra(Config):
    def __init__(self, hostIPs=[], hostPorts=[], hostJMXPorts=[], rate=50, duration=30, warmup_duration=300,
                 consistency='ONE', jmx_metrics=[], replication_factor=1, keyspace='stressandra_test_ks',
                 table="stressandra_test_table", write_test=False, read_test=False):
        super().__init__(hostIPs, hostPorts, hostJMXPorts, rate, duration, warmup_duration, consistency,
            jmx_metrics, replication_factor, keyspace, table, write_test, read_test)
        self.sessions = {}
        self.warmup_threads = []
        self.stress_threads = []
        self.jmx_metric_objs = []

    def run(self):
        self.get_sessions()
        self.make_dirs()
        self.validate_cluster_size()
        self.create_keyspace()
        self.create_table()
        self.run_warmup()
        for i in range(self.cluster_size):
            stop_event = threading.Event()
            jmx_metric = JMXMetrics(self, self.hostIPs[i], self.hostJMXPorts[i], self.metrics_dir, stop_event)
            self.jmx_metric_objs.append(jmx_metric)
            metrics_thread = threading.Thread(target=jmx_metric.run)
            metrics_thread.start()
        self.run_stress_test()
        for jmx_metric in self.jmx_metric_objs:
            jmx_metric.stop_event.set()
        self.save_config()

    def make_dirs(self):
        os.mkdir(self.logs_dir)
        os.mkdir(self.metrics_dir)

    def get_sessions(self):
        for host, port in zip(self.hostIPs, self.hostPorts):
            print(f"Creating session for node {host}:{port}")
            self.sessions[f"{host}:{port}"] = get_session(host, port)

    def validate_cluster_size(self):
        print("Validating cluster size...")
        
        rows = list(self.sessions.values())[0].execute("SELECT peer FROM system.peers")
        discovered_ips = [row.peer for row in rows]
        discovered_ips.append(list(self.sessions.values())[0].execute("SELECT broadcast_address FROM system.local").one().broadcast_address)

        node_count = len(discovered_ips)

        if node_count < self.cluster_size:
            print(f"Cluster size validation failed. Expected: {self.cluster_size}, Found: {node_count}")
            raise ValueError("Cluster does not have the required number of nodes.")

        print(f"Cluster size validated: {node_count} nodes available.")

        # Compare discovered IPs with expected host IPs
        expected_ips = set(self.hostIPs)
        discovered_ips_set = set(discovered_ips)

        if expected_ips != discovered_ips_set:
            print(f"Discovered cluster IPs {discovered_ips_set} do not match expected IPs {expected_ips}.")
        else:
            print("Cluster IPs match expected configuration.")


    def create_keyspace(self):
        print(f"Creating keyspace '{self.keyspace}' with replication factor {self.replication_factor}...")
        query = f"""
        CREATE KEYSPACE IF NOT EXISTS {self.keyspace}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': {self.replication_factor} }};
        """
        list(self.sessions.values())[0].execute(query)
        time.sleep(2)  # Allow time for propagation

        # Validate keyspace creation
        result = list(self.sessions.values())[0].execute("SELECT keyspace_name, replication FROM system_schema.keyspaces WHERE keyspace_name = %s", [self.keyspace]).one()
        
        if result and result.keyspace_name == self.keyspace:
            print(f"Keyspace '{self.keyspace}' created successfully.")
        else:
            print(f"Failed to create keyspace '{self.keyspace}'.")
            raise RuntimeError("Keyspace creation validation failed.")

    def create_table(self):
        print(f"Creating table '{self.keyspace}.{self.table}'...")
        query = f"""
        CREATE TABLE IF NOT EXISTS {self.keyspace}.{self.table} (
            id UUID PRIMARY KEY,
            value TEXT
        );
        """
        list(self.sessions.values())[0].execute(query)
        print(f"Table '{self.table}' created successfully.")


    def run_warmup(self):
        print("Starting warmup phase...")
        for i in range(self.cluster_size):
            print(f"Warming up node {self.hostIPs[i]}:{self.hostPorts[i]} for {self.warmup_duration}s with replication factor {self.replication_factor} before stress test...")
            thread = threading.Thread(target=stress.run_stress_writes, args=(self.sessions[f"{self.hostIPs[i]}:{self.hostPorts[i]}"],
                self.hostIPs[i], self.hostPorts[i], 50, self.warmup_duration, ConsistencyLevel.ONE, self.keyspace, self.table))
            self.warmup_threads.append(thread)
            thread.start()

        self.progress_bar(self.warmup_duration, "Warmup")
        self.end_warmup()

    def end_warmup(self):
        for i, thread in enumerate(self.warmup_threads):
            thread.join()
            print(f"Stopping warmup on host {self.hostIPs[i]}:{self.hostPorts[i]}")
        self.warmup_threads = []
        print("Warmup phase completed.")

    def run_stress_test(self):
        print("Starting stress test...")

        if self.write_test:
            print("Running write test on all nodes.")
            for i in range(self.cluster_size):
                print(f"Starting write stress test on host {self.hostIPs[i]}:{self.hostPorts[i]}")
                thread = threading.Thread(target=stress.run_stress_writes, args=(self.sessions[f"{self.hostIPs[i]}:{self.hostPorts[i]}"],
                    self.hostIPs[i], self.hostPorts[i], self.rate, self.duration, self.consistency, self.keyspace, self.table))
                self.stress_threads.append(thread)
                thread.start()

            self.progress_bar(self.duration, "Write Stress Test")
            self.end_stress_test()

        if self.read_test:
            print("Running read test on all nodes.")
            for i in range(self.cluster_size):
                print(f"Starting read stress test on host {self.hostIPs[i]}:{self.hostPorts[i]}")
                thread = threading.Thread(target=stress.run_stress_reads, args=(self.sessions[f"{self.hostIPs[i]}:{self.hostPorts[i]}"],
                    self.hostIPs[i], self.hostPorts[i], self.rate, self.duration, self.consistency, self.keyspace, self.table))
                self.stress_threads.append(thread)
                thread.start()

            self.progress_bar(self.duration, "Read Stress Test")
            self.end_stress_test()

        print("Stress test completed.")

    def end_stress_test(self):
        for i, thread in enumerate(self.stress_threads):
            thread.join()
            print(f"Stopping stress test on host {self.hostIPs[i]}:{self.hostPorts[i]}")
        self.stress_threads = []

    def progress_bar(self, total_progress, desc):
        with tqdm(total=total_progress, desc=desc, unit="s") as pbar:
            start_time = time.time()
            while time.time() - start_time < total_progress:
                remaining_time = total_progress - (time.time() - start_time)
                pbar.update(1)
                time.sleep(1)
            pbar.update(total_progress - pbar.n)

    def save_config(self):
        filename = f"{self.logs_dir}/config.json"
        data = {
            "Consistency": self.consistency,
            "Replication": self.replication,
            "Rate": self.rate,
            "Duration": self.duration,
            "Cluster Size": self.cluster_size
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)