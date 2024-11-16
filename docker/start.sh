#!/bin/bash

# Pull latest image
docker-compose pull

# Stop and remove existing containers
docker-compose down

# Start service
docker-compose up -d

echo "Milvus is starting... It may take a few moments."
echo "Milvus will be available at localhost:19530"