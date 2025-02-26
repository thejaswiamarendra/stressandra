import time
from jmxquery import JMXConnection, JMXQuery
import json
import math
import statistics
import os
import csv
from .config import Config

def save_dict_to_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def is_valid_json_value(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    try:
        json.dumps(value)  # Ensure it's JSON-serializable
        return True
    except (TypeError, ValueError):
        return False

def save_dict_to_csv(data, filename, fill_value="N/A"):
    max_length = max(len(v) for v in data.values())
    for key in data:
        data[key] += [fill_value] * (max_length - len(data[key]))

    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(data.keys())  
        writer.writerows(zip(*data.values()))  

class JMXMetric:
    def __init__(self, name, mbean, unit):
        self.name = name
        self.mbean = mbean
        self.unit = unit

class JMXMetrics():
    def __init__(self, config, host, jmx_port, metrics_dir, stop_event, max_retries=5, retry_delay=2):
        self.jmxmetrics = [JMXMetric(metric['name'], metric['mbean'], metric['unit']) for metric in config.jmx_metrics]
        self.host = f"{host}:{jmx_port}"
        self.metrics_dir = metrics_dir
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.metrics = {}
        self.metrics_name_map = {}
        self.queries = [JMXQuery(jmx_metric.mbean) for jmx_metric in self.jmxmetrics]
        self.stats = {}
        self.errors = []
        self.stop_event = stop_event

    def run(self):
        print(f"Starting JMX Metrics collection on node {self.host}...")
        self.collect_metrics_per_node()
        self.save_csv()
        self.save_stats()
        print(f"Stopping JMX Metrics collection on node {self.host}")

    def collect_metrics_per_node(self):
        jmx_url = f"service:jmx:rmi:///jndi/rmi://{self.host}/jmxrmi"
        results = []

        while not self.stop_event.is_set():
            retries = 0
            while retries <= self.max_retries:
                try:
                    jmx_conn = JMXConnection(jmx_url)
                    results.append(jmx_conn.query(self.queries))
                    break  # Success, exit retry loop
                except Exception as e:
                    print(f"Error collecting JMX metrics from {self.host}:{self.jmx_port}: {e}. Retry {retries + 1}/{self.max_retries}.")
                    retries += 1
                    if retries <= self.max_retries:
                        time.sleep(self.retry_delay)
                    else:
                        print(f"Max retries reached for {self.host}:{self.jmx_port}. Continuing collection.")
                        self.errors.append(f"Max retries reached for {self.host}:{self.jmx_port}. Continuing collection.")
                        break #max retries reached, continue the main loop.
            time.sleep(0.1)

        self.extract_metrics(results)
        self.generate_stats()

    def extract_metrics(self, results):
        for result in results:
            for metric in result:
                if not is_valid_json_value(metric.value):
                    continue
                if metric.to_query_string() in self.metrics.keys():
                    self.metrics[metric.to_query_string()].append(metric.value)
                else:
                    self.metrics[metric.to_query_string()] = [metric.value]

    def generate_stats(self):
        for metric_name, metric_value in self.metrics.items():
            try:
                mean = sum(metric_value) / len(metric_value)
                minimum = min(metric_value)
                maximum = max(metric_value)
                median = statistics.median(metric_value)
                stddev = statistics.stdev(metric_value) if len(metric_value) > 1 else 0
                self.stats[metric_name] = {
                    "Mean": mean,
                    "Min": minimum,
                    "Max": maximum,
                    "Median": median,
                    "StdDev": stddev,
                }
            except Exception as e:
                print(e)
                self.errors.append(e)
                continue
    
    def save_csv(self):
        print(f"Saving JMX metrics CSV at {self.metrics_dir}/{self.host}.csv")
        save_dict_to_csv(self.metrics, f"{self.metrics_dir}/{self.host}.csv")

    def save_stats(self):
        print(f"Saving JMX metrics Stats at {self.metrics_dir}/{self.host}-stats.json")
        save_dict_to_json(self.stats, f"{self.metrics_dir}/{self.host}-stats.json")
