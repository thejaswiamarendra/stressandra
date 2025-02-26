import time
import random
import uuid
import threading
from cassandra.cluster import Cluster
from cassandra import ConsistencyLevel
from cassandra.query import SimpleStatement

# Cassandra nodes and ports
CASSANDRA_NODES = ["localhost"]
PORTS = [9042, 9043, 9044]
CONSISTENCY_LEVELS = [ConsistencyLevel.ANY, ConsistencyLevel.ONE, ConsistencyLevel.QUORUM, ConsistencyLevel.ALL]

# Connect to Cassandra
port = random.choice(PORTS)
cluster = Cluster(CASSANDRA_NODES, port=port)
session = cluster.connect()

# Set keyspace and create table
session.execute("CREATE KEYSPACE IF NOT EXISTS test_keyspace WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};")
session.set_keyspace("test_keyspace")
session.execute("CREATE TABLE IF NOT EXISTS test_table (id UUID PRIMARY KEY, value TEXT);")

# Insert and read statements with placeholders
insert_stmt = session.prepare("INSERT INTO test_table (id, value) VALUES (?, ?)")
select_stmt = session.prepare("SELECT * FROM test_table LIMIT ?")

# Track statistics
stats = {"writes": 0, "reads": 0, "write_errors": 0, "read_errors": 0}

def write_data(num_writes, consistency):
    """Performs stress test by inserting data at high rates."""
    start_time = time.time()
    for _ in range(num_writes):
        try:
            uid = uuid.uuid4()
            value = f"value-{random.randint(1, 1000000)}"
            query = SimpleStatement(
                "INSERT INTO test_table (id, value) VALUES (%s, %s)",
                consistency_level=consistency
            )
            session.execute(query, (uid, value))
            stats["writes"] += 1
        except Exception as e:
            stats["write_errors"] += 1
            print(f"Write Error: {e}")
    end_time = time.time()
    print(f"[WRITE] {num_writes} inserts at {consistency}: {end_time - start_time:.4f} sec")

def read_data(num_reads, consistency):
    """Performs stress test by querying data at high rates."""
    start_time = time.time()
    try:
        query = SimpleStatement(
            "SELECT * FROM test_table LIMIT %s",
            # consistency_level=consistency
        )
        rows = session.execute(query, (num_reads,))
    except Exception as e:
        stats["read_errors"] += 1
        print(f"Read Error: {e}")
    end_time = time.time()
    print(f"[READ] {num_reads} selects at {consistency}: {end_time - start_time:.4f} sec")

def stress_test(threads=10, ops_per_thread=1000, consistency=ConsistencyLevel.ONE):
    """Launches multiple threads to stress test reads and writes."""
    write_threads = []
    read_threads = []
    
    for _ in range(threads):
        w_thread = threading.Thread(target=write_data, args=(ops_per_thread, consistency))
        r_thread = threading.Thread(target=read_data, args=(ops_per_thread, consistency))
        write_threads.append(w_thread)
        read_threads.append(r_thread)
    
    for t in write_threads + read_threads:
        t.start()
    
    for t in write_threads + read_threads:
        t.join()

# Run stress test for all consistency levels
for level in CONSISTENCY_LEVELS:
    print(f"\n--- Stress Testing with Consistency: {level} ---")
    stress_test(threads=20, ops_per_thread=500, consistency=level)  # 20 threads, 500 ops each

# Print final stats
print("\nFinal Stats:", stats)
