#!/bin/bash

echo "🔍 Checking Iceberg Setup..."

# Check if MinIO is running
echo "1. Checking MinIO..."
if curl -s http://localhost:9000/minio/health/live > /dev/null; then
    echo "✅ MinIO is running"
else
    echo "❌ MinIO is not accessible"
fi

# Check if bucket exists
echo "2. Checking Iceberg bucket..."
docker exec github-events-minio mc ls minio/iceberg 2>/dev/null && echo "✅ Iceberg bucket exists" || echo "❌ Iceberg bucket not found"

# Check Spark connection to Iceberg
echo "3. Checking Spark Iceberg integration..."
docker exec github-events-spark-master spark-sql \
    --packages org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.2 \
    --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
    --conf spark.sql.catalog.github_events=org.apache.iceberg.spark.SparkCatalog \
    --conf spark.sql.catalog.github_events.type=hadoop \
    --conf spark.sql.catalog.github_events.warehouse=s3a://iceberg/warehouse \
    -e "SHOW DATABASES;" 2>/dev/null && echo "✅ Spark can connect to Iceberg" || echo "❌ Spark Iceberg connection failed"

# Check if table exists and has data
echo "4. Checking table data..."
curl -s "http://localhost:8000/stats" | grep -q "total_events" && echo "✅ Iceberg table has data" || echo "⚠️  No data in Iceberg table yet"

echo ""
echo "🗂️  Access Iceberg data:"
echo "   MinIO Console: http://localhost:9001"
echo "   API Stats: http://localhost:8000/stats"
echo "   API Events: http://localhost:8000/events"
