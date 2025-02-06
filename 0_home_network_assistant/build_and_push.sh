#!/bin/bash
                set -e
                REGION=us-east-1
                ACCOUNT_ID=218208277580
                REPO_NAME=lambda-home-network-assistant_lambda
                IMAGE_NAME=lambda-home-network-assistant_lambda:latest
                IMAGE_URI=218208277580.dkr.ecr.us-east-1.amazonaws.com/lambda-home-network-assistant_lambda
                ARCH=linux/amd64
                aws configure set region $REGION
                aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
                aws ecr describe-repositories --repository-names $REPO_NAME > /dev/null 2>&1 || aws ecr create-repository --repository-name $REPO_NAME
                docker build --platform $ARCH . -t $IMAGE_NAME
                docker tag $IMAGE_NAME $IMAGE_URI
                docker push $IMAGE_URI
                