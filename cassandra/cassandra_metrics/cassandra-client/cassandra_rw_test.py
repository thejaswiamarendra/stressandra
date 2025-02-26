import time
import random
import uuid
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from cassandra import ConsistencyLevel

# Connect to Cassandra
port = random.choice([9042, 9043, 9044])
cluster = Cluster(["localhost"], port=port)
session = cluster.connect()

# Create keyspace and table
session.execute("CREATE KEYSPACE IF NOT EXISTS test_keyspace WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};")
session.set_keyspace("test_keyspace")
session.execute("CREATE TABLE IF NOT EXISTS test_table (id UUID PRIMARY KEY, value TEXT);")

def write_data(num_writes=100):
    start_time = time.time()
    for _ in range(num_writes):
        uid = uuid.uuid4()
        value = f"value-{random.randint(1, 1000000)}"
        query = SimpleStatement(
            "INSERT INTO test_table (id, value) VALUES (%s, %s)",
            consistency_level=ConsistencyLevel.ALL
        )
        session.execute(query, (uid, value))
    end_time = time.time()
    print(f"Write Time for {num_writes} inserts: {end_time - start_time:.4f} seconds")

def read_data(num_reads=100):
    start_time = time.time()
    query = SimpleStatement(
        "SELECT * FROM test_table LIMIT %s",
        consistency_level=ConsistencyLevel.ALL
    )
    rows = session.execute(query, (num_reads,))
    end_time = time.time()
    print(f"Read Time for {num_reads} selects: {end_time - start_time:.4f} seconds")

# Run Read/Write tests
for i in range(100):
    time.sleep(1)
    write_data(100)
    read_data(100)
