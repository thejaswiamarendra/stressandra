FROM python:3.9
WORKDIR /app
COPY cassandra_rw_test.py .
COPY deps/ /deps/
RUN pip install --no-index --find-links=/deps cassandra-driver
CMD ["python", "cassandra_rw_test.py"]
