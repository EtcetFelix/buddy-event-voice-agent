#!/bin/bash
set -e

INSTANCE_IP=$(terraform output -raw ec2_public_ip)
ECR_REPO=$(terraform output -raw ecr_repository_url)

# Build and push
docker build -t buddy-agent:latest .
docker tag buddy-agent:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# Deploy to EC2
ssh ec2-user@$INSTANCE_IP << 'ENDSSH'
  cd /home/ec2-user/app
  ./ecr-login.sh
  docker-compose pull
  docker-compose up -d
ENDSSH