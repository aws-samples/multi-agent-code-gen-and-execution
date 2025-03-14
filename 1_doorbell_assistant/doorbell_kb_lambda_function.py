# This lambda function contains code to 
# set the bedrock client, and then query the search
# results from a knowledge base based on the user query. 
import json
import logging
import boto3
from typing import Optional
from botocore.config import Config
# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_bedrock_client(region: str) -> boto3.client:
    """
    Create and return a Bedrock client with the specified configuration
    """
    config = Config(
        region_name=region,
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        }
    )
    return boto3.client('bedrock-agent-runtime', config=config)

def query_knowledge_base(query: str, kb_id: str, region: str, num_results: int = 5) -> Optional[dict]:
    """
    Query the knowledge base using Retrieve API and return results
    Args:
        query (str): The query to send to the knowledge base
        kb_id (str): Knowledge base ID
        region (str): AWS region
        num_results (int): Number of results to retrieve
    Returns:
        dict: Dictionary containing retrieved chunks and their scores
    """
    try:
        result: Optional[dict] = None
        bedrock_client = get_bedrock_client(region)
        
        response_ret = bedrock_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': num_results,
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

def lambda_handler(event, context):
    """
    AWS Lambda handler function
    """
    try:
        # Extract parameters from event
        body = json.loads(event.get('body', '{}'))
        query = body.get('query')
        kb_id = body.get('kb_id')
        region = body.get('region', 'us-east-1') 
        num_results = body.get('num_results', 5)  
        
        # Validate required parameters
        if not query:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Query parameter is required'
                })
            }
            
        if not kb_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Knowledge base ID is required'
                })
            }

        # Query the knowledge base
        result = query_knowledge_base(
            query=query,
            kb_id=kb_id,
            region=region,
            num_results=num_results
        )
        
        if result is None:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Failed to query knowledge base'
                })
            }

        # Return successful response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }