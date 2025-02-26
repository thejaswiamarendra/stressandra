import time
import concurrent.futures
import uuid
from .db import get_session
from cassandra import ConsistencyLevel
from cassandra.cluster import Session
from cassandra.query import SimpleStatement

def set_keyspace(session, keyspace):
    session.set_keyspace(keyspace)

def run_stress_writes(session, host, port, rate, duration, consistency, keyspace, table, cleanup_interval=10, cleanup_batch_size=1000):
    """
    Runs a Cassandra write stress test on the given host and port.

    Parameters:
    - session (Session): Cassandra session object.
    - host (str): IP address of the Cassandra node.
    - port (int): Port number for CQL connections.
    - rate (int): Number of requests per second.
    - duration (int): Duration of the test in seconds.
    - consistency (str): Write consistency level.
    - cleanup_interval (int): Interval (in seconds) to clean up old data.
    - cleanup_batch_size (int): Number of records to delete per cleanup batch.
    """
    set_keyspace(session, keyspace)  # Ensure keyspace exists


    with concurrent.futures.ThreadPoolExecutor(max_workers=rate) as executor:
        start_time = time.time()
        cleanup_time = start_time + cleanup_interval
        inserted_ids = []

        while time.time() - start_time < duration:
            new_id = uuid.uuid4()
            
            insert_query = SimpleStatement(
                f"INSERT INTO {table} (id, value) VALUES (%s, %s)", 
                consistency_level=consistency
            )

            try:
                future = executor.submit(session.execute, insert_query, (new_id, "stress_test"))
                result = future.result()
            except Exception as e:
                print(f"Write failed on {host}:{port} during query {insert_query} - {e}")

            if time.time() >= cleanup_time:
                cleanup_list = inserted_ids[:cleanup_batch_size]
                for id_to_delete in cleanup_list:
                    delete_query = SimpleStatement(f"DELETE FROM {table} WHERE id = %s", consistency_level=consistency)
                    try:
                        future = executor.submit(session.execute, delete_query, (id_to_delete,))
                        result = future.result()  # Ensure deletion is successful
                        inserted_ids.remove(id_to_delete)
                    except Exception as e:
                        print(f"Delete failed for {id_to_delete} on {host}:{port} during query {delete_query} - {e}")

                cleanup_time += cleanup_interval

            time.sleep(1 / rate)

    print(f"Write stress test completed on {host}:{port} for {duration}s at {rate} ops/sec.")


def run_stress_reads(session, host, port, rate, duration, consistency, keyspace, table):
    session = get_session(host, port)

    select_query = "SELECT id, value FROM test WHERE id = %s"

    with concurrent.futures.ThreadPoolExecutor(max_workers=rate) as executor:
        start_time = time.time()
        while time.time() - start_time < duration:
            random_id = uuid.uuid4()  # Simulating a lookup for a random ID
            executor.submit(session.execute, select_query, (random_id,))
            time.sleep(1 / rate)  # Control request rate