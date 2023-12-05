#!/bin/sh

# This script is used to deploy the application to the server.
docker compose stop
docker compose down
rm ./logs/cv_reconstruction.log
mkdir -p logs
touch ./logs/cv_reconstruction.log
docker compose -f docker-compose.yml up -d --build --remove-orphans
nohup saw watch /aws/lambda/reconstruction-pipeline-prod-reconstruct --expand >> ./logs/cv_reconstruction.log &
