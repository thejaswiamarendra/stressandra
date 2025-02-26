# stressandra
## python based cli tool to stress test a cassandra cluster.

1. Clone repo
2. Run `./scripts/setup.sh`
3. Get a cluster running.
    - For a basic test cluster,
    a. Get docker on your system
    b. `cd ./cassandra/cassandra_3node` (if you have a good setup, go nuts with 4 node.)
    c. Modify `default_config.yaml` however needed
4. `stressandra run`
5. logs, stats, metrics is stored under `./logs`

thejaswiamarendra