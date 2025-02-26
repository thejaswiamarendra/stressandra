import argparse
# import threading
# import time
# from stressandra import stress, jmx
# import pkg_resources
import yaml
import datetime
# import os
# from tqdm import tqdm
# from cassandra import ConsistencyLevel
# import re
# import logging
# from cassandra.cluster import Cluster

# def get_version():
#     try:
#         return pkg_resources.get_distribution("stressandra").version
#     except pkg_resources.DistributionNotFound:
#         return "dev"

# def run_stressandra(config_path):
#     ts = datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S")
#     metrics_dir = f"./metrics/{ts}"
#     os.makedirs(f"{metrics_dir}/csv", exist_ok=True)
#     os.makedirs(f"{metrics_dir}/json", exist_ok=True)

#     with open(config_path, "r") as config_file:
#         config = yaml.safe_load(config_file)

#     replication_factor = config['replication_factor']
#     hostIPs = [host['host'] for host in config['hosts']]
#     hostPorts = [host['port'] for host in config['hosts']]
#     hostJMXPorts = [host['jmx_port'] for host in config['hosts']]
#     rate = config['rate']
#     duration = config['duration']
#     consistency = config['consistency']
#     jmx_metrics = config['jmx_metrics']

#     metrics_stop_events = []

#     print(f"Running stress test with rate - {rate}, duration - {duration}, consistency - {consistency}, replication - {replication_factor}")

#     warmup_threads = []
#     for i in range(len(config['hosts'])):
#         print(f"Warming up node {hostIPs[i]}:{hostPorts[i]} for 600s with replication factor 3 before stress test...")
#         thread = threading.Thread(target=stress.run_stress_test, args=(hostIPs[i], hostPorts[i], 50, 300, 'ANY', replication_factor))
#         warmup_threads.append(thread)
#         thread.start()

#     total_progress = 600  # Total duration of the stress test
#     with tqdm(total=total_progress, desc="Warmup Progress", unit="s") as pbar:
#         start_time = time.time()
#         while time.time() - start_time < duration:
#             remaining_time = duration - (time.time() - start_time)
#             pbar.update(1)  # Update progress bar every second
#             time.sleep(1)  # Sleep for 1 second

#     for i, thread in enumerate(warmup_threads):
#         thread.join()
#         print(f"Stopping warm up on host {hostIPs[i]}:{hostPorts[i]}...")

#     for i in range(len(config['hosts'])):
#         print(f"Starting JMX metrics collection for host {hostIPs[i]}:{hostPorts[i]}...")
#         stop_event = threading.Event()
#         metrics_stop_events.append(stop_event)
#         metrics_thread = threading.Thread(target=jmx.collect_metrics_thread, args=(hostJMXPorts[i], stop_event, jmx_metrics, consistency, duration, rate, hostIPs[i], metrics_dir))
#         metrics_thread.start()
    
#     stress_threads = []
#     for i in range(len(config['hosts'])):
#         print(f"Starting stress test on host {hostIPs[i]}:{hostPorts[i]}...")
#         thread = threading.Thread(target=stress.run_stress_test, args=(hostIPs[i], hostPorts[i], rate, duration, consistency, replication_factor))
#         stress_threads.append(thread)
#         thread.start()

#     total_progress = duration  # Total duration of the stress test
#     with tqdm(total=total_progress, desc="Stress Test Progress", unit="s") as pbar:
#         start_time = time.time()
#         while time.time() - start_time < duration:
#             remaining_time = duration - (time.time() - start_time)
#             pbar.update(1)  # Update progress bar every second
#             time.sleep(1)  # Sleep for 1 second

#     for i, thread in enumerate(stress_threads):
#         thread.join()
#         print(f"Stopping stress test on host {hostIPs[i]}:{hostPorts[i]}...")

#     for i, stop_event in enumerate(metrics_stop_events):
#         stop_event.set()
#         print(f"Stopping JMX metrics collection for host {hostIPs[i]}:{hostPorts[i]}...")

# def main():
#     parser = argparse.ArgumentParser(description="Stressandra: A Cassandra Stress Testing Tool")
#     parser.add_argument("-v", "--version", action="store_true", help="Show the version of Stressandra")

#     subparsers = parser.add_subparsers(dest="command")

#     run_parser = subparsers.add_parser("run", help="Run the Cassandra stress test")
#     run_parser.add_argument("--config", type=str, default="./default_config.yaml", help="Input YAML file with the required configuration")

#     args = parser.parse_args()

#     if args.version:
#         print(f"Stressandra version {get_version()}")
#         return

#     if args.command == "run":
#         run_stressandra(args.config)
#     else:
#         parser.print_help()  # Prints description if no subcommand is given

# if __name__ == "__main__":
#     main()
from .stressandra import Stressandra
from .config import Config
from .db import get_session

def main():
    parser = argparse.ArgumentParser(description="Stressandra: A Cassandra Stress Testing Tool")
    parser.add_argument("-v", "--version", action="store_true", help="Show the version of Stressandra")

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the Cassandra stress test")
    run_parser.add_argument("--config", type=str, default="./default_config.yaml", help="Input YAML file with the required configuration")

    args = parser.parse_args()

    if args.version:
        print(f"Stressandra version {get_version()}")
        return

    if args.command == "run":
        with open(args.config, "r") as config_file:
            config_yaml = yaml.safe_load(config_file)

        stressandra = Stressandra(
            hostIPs=[host['host'] for host in config_yaml['hosts']],
            hostPorts=[host['port'] for host in config_yaml['hosts']],
            hostJMXPorts=[host['jmx_port'] for host in config_yaml['hosts']],
            rate=config_yaml['rate'],
            duration=config_yaml['duration'],
            warmup_duration=config_yaml['warmup_duration'],
            consistency=config_yaml['consistency'],
            jmx_metrics=config_yaml['jmx_metrics'],
            replication_factor=config_yaml['replication_factor'],
            keyspace=config_yaml['keyspace'],
            table=config_yaml['table'],
            write_test=config_yaml['write_test'],
            read_test=config_yaml['read_test']
        )

        stressandra.run()
    else:
        parser.print_help()  # Prints description if no subcommand is given

if __name__ == "__main__":
    main()