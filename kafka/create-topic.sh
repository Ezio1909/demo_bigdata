#!/bin/bash

# Create Kafka topic for GitHub events (microservices container name)
docker exec github-events-kafka kafka-topics --create \
  --topic github-events \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=7200000 \
  --config segment.ms=3600000 \
  --config cleanup.policy=delete

# Verify topic creation
docker exec github-events-kafka kafka-topics --describe \
  --topic github-events \
  --bootstrap-server localhost:9092

echo "GitHub events topic created successfully!"
