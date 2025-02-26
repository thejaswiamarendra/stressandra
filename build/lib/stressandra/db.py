from cassandra.cluster import Cluster

def get_session(host, port):
    cluster = Cluster([host], port=port)
    session = cluster.connect()
    return session
