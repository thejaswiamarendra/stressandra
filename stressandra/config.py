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

def is_valid_ip(ip):
    return bool(re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", ip))

def is_valid_port(port):
    return isinstance(port, int) and 1 <= port <= 65535

def make_consistency(consistency: str):
    return getattr(ConsistencyLevel, consistency.upper(), ConsistencyLevel.ONE)

class Config:
    def __init__(self, hostIPs=[], hostPorts=[], hostJMXPorts=[], rate=50, duration=30, warmup_duration=300,
                 consistency='ONE', jmx_metrics=[], replication_factor=1, keyspace='stressandra_test_ks',
                 table="stressandra_test_table", write_test=False, read_test=False):
        self.hostIPs = hostIPs
        self.hostPorts = hostPorts
        self.hostJMXPorts = hostJMXPorts
        self.rate = rate
        self.duration = duration
        self.warmup_duration = warmup_duration
        self.consistency = make_consistency(consistency)
        self.jmx_metrics = jmx_metrics
        self.replication_factor = replication_factor
        self.keyspace = keyspace
        self.table = table
        self.write_test = write_test
        self.read_test = read_test
        self.logs_dir = f'./logs/{datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S")}'
        self.metrics_dir = f'{self.logs_dir}/metrics'
        self.cluster_size = len(hostIPs)
        self.validate()  # Auto-validate upon initialization

    def validate(self):
        if not all(is_valid_ip(ip) for ip in self.hostIPs):
            raise ValueError("Invalid IP address in hostIPs.")
        
        if not all(is_valid_port(port) for port in self.hostPorts):
            raise ValueError("Invalid port in hostPorts.")

        if not all(is_valid_port(port) for port in self.hostJMXPorts):
            raise ValueError("Invalid port in hostJMXPorts.")

        if not isinstance(self.rate, int) or self.rate <= 0:
            raise ValueError("Rate must be a positive integer.")

        if not isinstance(self.duration, int) or self.duration <= 0:
            raise ValueError("Duration must be a positive integer.")

        if not isinstance(self.warmup_duration, int) or self.warmup_duration < 0:
            raise ValueError("Warmup duration must be a non-negative integer.")

        if not isinstance(self.replication_factor, int) or self.replication_factor <= 0:
            raise ValueError("Replication factor must be a positive integer.")

        if not isinstance(self.keyspace, str) or not self.keyspace:
            raise ValueError("Keyspace must be a non-empty string.")

        if not isinstance(self.table, str) or not self.table:
            raise ValueError("Table must be a non-empty string.")

        if not isinstance(self.write_test, bool) or not isinstance(self.read_test, bool):
            raise ValueError("write_test and read_test must be boolean values.")
        
        if len(self.hostIPs) != self.cluster_size or len(self.hostPorts) != self.cluster_size or len(self.hostJMXPorts) != self.cluster_size:
            raise ValueError("Length of hostIPs, Ports and JMX Ports must be the same")

        if self.consistency == "ANY" and self.read_test:
            print("ANY consistency is invalid for read operations, skipping read test...")
            self.read_test = False
