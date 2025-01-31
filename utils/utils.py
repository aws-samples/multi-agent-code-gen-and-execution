# This file contain utility functions that are used across the mutli agent
# solution
import re
import os
import json
import yaml
import time
import boto3
import zipfile
import logging
import requests
from globals import *
from io import BytesIO
from pathlib import Path
from typing import Union, Dict, Optional
from botocore.exceptions import ClientError

# set a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PYTHON_TIMEOUT: int = 180
PYTHON_RUNTIME: str = "python3.12"

def get_aws_region():
    """Retrieve the AWS region from environment, session, or EC2 metadata."""
    try:
        region: Optional[str] = None
        # Use IMDSv2 to fetch region from EC2 metadata
        token = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=2
        ).text
        region = requests.get(
            "http://169.254.169.254/latest/meta-data/placement/region",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=2
        ).text
    except requests.RequestException:
        region = None
    return region

region_name = get_aws_region()
region_name = "us-east-1" if region_name is None else region_name
# Initialize S3 client
s3_client = boto3.client('s3', region_name=region_name)
# Initialize the bedrock runtime client. This is used to 
# query search results from the KBs
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', region_name=region_name) 

def load_config(config_file: Union[Path, str]) -> Optional[Dict]:
    """
    Load configuration from a local file.

    :param config_file: Path to the local file
    :return: Dictionary with the loaded configuration
    """
    try:
        config_data: Optional[Dict] = None
        logger.info(f"Loading config from local file system: {config_file}")
        content = Path(config_file).read_text()
        config_data = yaml.safe_load(content)
        logger.info(f"Loaded config from local file system: {config_data}")
    except Exception as e:
        logger.error(f"Error loading config from local file system: {e}")
        config_data = None
    return config_data

def upload_file_to_s3(file_path, bucket_name):
    """
    Upload a single file to S3 bucket
    """
    # Get the filename from the path
    file_name = os.path.basename(file_path)
    try:
        logger.info(f"Uploading file {file_name} to bucket {bucket_name}")
        s3_client.upload_file(file_path, bucket_name, file_name)
        logger.info(f"Successfully uploaded {file_name}")
    except Exception as e:
        logger.info(f"Error uploading file: {str(e)}")
        raise

def create_s3_bucket_for_kb(s3_bucket_name: str, region: str) -> bool:
    """
    Create an S3 bucket for the knowledge base and verify its existence

    Args:
        s3_bucket_name (str): Name of the S3 bucket to create
        region (str): AWS region where the bucket should be created
    
    Returns:
        bool: True if bucket exists and is accessible, False otherwise
    """
    try:
        # First try to check if bucket exists
        try:
            s3_bucket_exists: bool = False
            s3_client.head_bucket(Bucket=s3_bucket_name)
            logger.info(f"Bucket {s3_bucket_name} already exists and is accessible")
            s3_bucket_exists=True
        except ClientError as e:
            if e.response['Error']['Code'] != '404':
                logger.error(f"Error checking bucket existence: {str(e)}")
                return s3_bucket_exists
        # Bucket doesn't exist, create it
        logger.info(f"Creating S3 bucket {s3_bucket_name} in region {region}")
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=s3_bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=s3_bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': region
                }
            )   
        # Verify the bucket was created successfully by checking it exists
        s3_client.head_bucket(Bucket=s3_bucket_name)
        logger.info(f"Successfully created and verified S3 bucket {s3_bucket_name}")
        s3_bucket_exists=True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou':
            logger.info(f"Bucket {s3_bucket_name} already exists and is owned by you")
            s3_bucket_exists=True
        elif error_code == 'BucketAlreadyExists':
            logger.error(f"Bucket {s3_bucket_name} already exists but is owned by another account")
        else:
            logger.error(f"Error creating/verifying S3 bucket: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error creating/verifying S3 bucket: {str(e)}")
    return s3_bucket_exists

def create_kb_lambda(
    lambda_function_name: str,
    source_code_file: str,
    region: str,
    kb_id: str) -> str:
    """
    Creates a Lambda function for knowledge base queries
    
    Args:
        lambda_function_name (str): Name of the Lambda function to create
        source_code_file (str): Name of the file containing the Lambda source code
        region (str): AWS region for the Lambda
        kb_id (str): Knowledge base ID
    
    Returns:
        str: ARN of the created Lambda function
    """
    try:
        # Initialize Lambda client
        lambda_client = boto3.client('lambda', region_name=region)
        iam = boto3.client('iam', region_name=region)
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']

        # Create IAM role for Lambda
        role_name = f"{lambda_function_name}-role"
        try:
            role = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }]
                })
            )

            iam.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{lambda_function_name}-policy",
                PolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            "Resource": [
                                f"arn:aws:logs:{region}:{account_id}:log-group:/aws/lambda/{lambda_function_name}:*"
                            ]
                        },
                        {
                            "Effect": "Allow",
                            "Action": [
                                "bedrock:*",
                                "bedrock-runtime:*",
                                "bedrock-agent-runtime:*"
                            ],
                            "Resource": "*"
                        },
                        {
                            "Effect": "Allow",
                            "Action": [
                                "bedrock:Retrieve",
                            ],
                            "Resource": [
                                f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/{kb_id}",
                                f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/{kb_id}/*"
                            ]
                        }
                    ]
                })
            )

            # Attach AWS managed policies
            managed_policies = [
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
            ]
            
            for policy in managed_policies:
                iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy
                )

            # Wait for role to propagate
            time.sleep(10)

        except iam.exceptions.EntityAlreadyExistsException:
            # If role exists, get its ARN
            role = iam.get_role(RoleName=role_name)

        # Package the Lambda code
        _base_filename = source_code_file.split(".py")[0]
        s = BytesIO()
        with zipfile.ZipFile(s, "w") as z:
            z.write(f"{source_code_file}")
        zip_content = s.getvalue()

        # Set environment variables
        env_variables = {
            "Variables": {
                "KB_ID": kb_id,
                "REGION": region
            }
        }

        # Create Lambda function
        lambda_function = lambda_client.create_function(
            FunctionName=lambda_function_name,
            Runtime=PYTHON_RUNTIME,
            Timeout=PYTHON_TIMEOUT,
            Role=role['Role']['Arn'],
            Code={"ZipFile": zip_content},
            Handler=f"{_base_filename}.lambda_handler",
            Environment=env_variables
        )

        print(f"Lambda function created successfully: {lambda_function['FunctionArn']}")
        return lambda_function["FunctionArn"]

    except Exception as e:
        print(f"Error creating Lambda function: {str(e)}")
        raise

def query_knowledge_base(query: str, kb_id: str, kb_info: Dict) -> Optional[dict]:
    """
    Query the knowledge base using Retrieve API and return results
    Args:
        query (str): The query to send to the knowledge base
    Returns:
        dict: Dictionary containing retrieved chunks and their scores
        {
            'chunks': list of retrieved text chunks,
            'raw_response': complete API response
        }
    """
    try:
        result: Optional[dict] = None
        response_ret = bedrock_agent_runtime_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': kb_info.get('num_retrieved_results', 5),
                    'overrideSearchType': 'HYBRID'
                }
            }
        )
        contexts = []
        if 'retrievalResults' in response_ret:
            for chunk in response_ret['retrievalResults']:
                contexts.append({
                    'text': chunk['content']['text'],
                    'location': chunk['location'],
                    'score': chunk.get('score', 0),
                    'metadata': chunk.get('metadata', {})
                })
        result = {
            'chunks': contexts,
            'raw_response': response_ret
        }
    except Exception as e:
        logger.error(f"Error querying knowledge base: {str(e)}")
        result = None
    return result

def query_lambda(query: str, region: str, kb_id: str, lambda_fn_name: str):
    """
    Simple Lambda test function that matches local testing style
    """
    lambda_client = boto3.client('lambda', region_name=region)
    payload = {
        'body': json.dumps({
            'query': query,
            'kb_id': kb_id,
            'region': region,
            'num_results': 5
        })
    }
    response = lambda_client.invoke(
        FunctionName=lambda_fn_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    return json.loads(json.loads(response['Payload'].read())['body'])