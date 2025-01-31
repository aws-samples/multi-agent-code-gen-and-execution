import os
import sys
import ast
import json
import time
import boto3
import logging
import tempfile
import subprocess
from typing import Dict, Any, Optional

BEDROCK_RUNTIME: str = "bedrock-runtime"

# set a logger
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def get_named_parameter(event, name):
    """
    Extract named parameter from event
    """
    try:
        return next(item for item in event['parameters'] if item['name'] == name)['value']
    except:
        return None

def populate_function_response(event, response_body):
    """
    Format the response according to the expected structure
    """
    return {
        'response': {
            'actionGroup': event['actionGroup'],
            'function': event['function'],
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': str(response_body)
                    }
                }
            }
        }
    }

def query_knowledge_base(query: str) -> tuple:
    """
    Queries another Lambda function to get information from the knowledge base
    """
    lambda_client = boto3.client('lambda', region_name=os.environ.get("REGION"))
    payload = {
        'body': json.dumps({
            'query': query,
            'kb_id': os.environ.get("KB_ID"),
            'region': os.environ.get("REGION"),
            'num_results': 5
        })
    }
    response = lambda_client.invoke(
        FunctionName=os.environ.get('HOME_NETWORK_KB_LAMBDA_FUNCTION_NAME'),
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    response_data = json.loads(response['Payload'].read())
    kb_response = json.loads(response_data['body'])
    
    retrieved_chunks = []
    for chunk in kb_response.get('chunks', []):
        chunk_info = {
            'text': chunk.get('text'),
            'score': chunk.get('score')
        }
        retrieved_chunks.append(chunk_info)
    print(f"Retrieved information from the KB: {retrieved_chunks}")
    return retrieved_chunks, query

def _get_prompt_template(prompt_id: str) -> str:
    """
    Get prompt template from Bedrock prompt manager
    """
    try:
        bedrock_agent = boto3.client(service_name="bedrock-agent", region_name=os.environ["REGION"])
        response = bedrock_agent.get_prompt(promptIdentifier=prompt_id)
        return response['variants'][0]['templateConfiguration']['text']['text']
    except Exception as e:
        logger.error(f"Error getting prompt template: {str(e)}")
        raise

def _invoke_bedrock_converse(
    endpoint_name: str,
    messages: list,
    temperature: float,
    max_tokens: int,
    top_p: float,
    system_prompts: list = [{"text": "You are a helpful AI assistant."}]
) -> Dict:
    """
    Simple function to invoke Bedrock's converse API.
    """
    bedrock_client = boto3.client(BEDROCK_RUNTIME)
    inference_config = {
        "temperature": temperature,
        "maxTokens": max_tokens,
        "topP": top_p,
    }
    st = time.perf_counter()
    response = bedrock_client.converse(
        modelId=endpoint_name,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config
    )
    latency = time.perf_counter() - st
    return response, latency

def generate_code(chunks: list, query: str, input_params: str) -> str:
    """
    Generate code using Bedrock
    """
    try:
        # Get environment variables and convert to appropriate types
        bedrock_model = os.environ["code_generation_model"]
        temperature = float(os.environ["temperature"])
        top_p = float(os.environ["top_p"])
        max_tokens = int(os.environ["max_tokens"])
        prompt_id = os.environ["CODE_GEN_PROMPT_ID"]  
        print(f"Reading the prompt from bedrock prompt management using the prompt id: {prompt_id}")
        PROMPT = _get_prompt_template(prompt_id)
        print(f"Prompt used for code generation: {PROMPT}")
        kb_content = "\n".join([chunk['text'] for chunk in chunks])
        # inject the kb content, user query and input params required to generate fully executable code into the prompt
        user_message = PROMPT.format(kb_content=kb_content, user_query=query, input_params=input_params, auth_token=os.environ["HOME_NETWORK_AUTH_TOKEN"])
        messages = [{"role": "user", "content": [{"text": user_message}]}]
        logger.info(f"Messages: {messages}")
        
        system_prompts = [{"text": "You are an AI assistant specialized in generating Python code for Home Networking API interactions."}]
        response, latency = _invoke_bedrock_converse(
            endpoint_name=bedrock_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            system_prompts=system_prompts
        )
        generated_code = response['output']['message']['content'][0]['text']
        print(f"Generated code with latency {latency} seconds")
        return generated_code
    except Exception as e:
        logger.error(f"Error generating code: {e}")
        raise

def save_generated_code(code_content: str) -> str:
    """
    Save the generated code to a temporary file
    """
    try:
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, 'generated_code.py')
        with open(file_path, 'w') as f:
            f.write(code_content)
        print(f"Code saved to: {file_path}")
        return file_path
    except Exception as e:
        print(f"Error saving generated code: {str(e)}")
        raise

# add logger statements here
def execute_generated_code(file_path: str) -> Dict:
    try:
        temp_dir = os.path.dirname(file_path)
        # print out the content of the file to double check 
        # Execute the generated code using the current Python interpreter
        
        from pathlib import Path
        print(f"code=\n{Path(file_path).read_text()}")
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=int(os.environ["code_execution_timeout"]),
            env={**os.environ, 'PYTHONPATH': temp_dir}
        )
        print(f"Result from executing the generated code: {result.stdout}, {result.stderr}")
        execution_result = {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode,
            'success': result.returncode == 0
        }
        print(f"Code execution completed with return code: {result.returncode}")
        return execution_result
        
    except subprocess.TimeoutExpired:
        logger.error("Code execution timed out")
        return {
            'stdout': '',
            'stderr': 'Execution timed out',
            'return_code': -1,
            'success': False
        }
    except Exception as e:
        logger.error(f"Error executing code: {e}")
        return {
            'stdout': '',
            'stderr': str(e),
            'return_code': -1,
            'success': False}

def lambda_handler(event, context):
    try:
        print(f"Received event: {event}")
        query = get_named_parameter(event, 'query')
        input_params = get_named_parameter(event, 'input_params')
        if input_params is None:
            print(f"Input params provided: {input_params}")
        parameters = event.get('parameters', [])
        function = event.get('function', '')
        print(f"Processing query: {query}, function: {function}, input parameters from user: {input_params}, parameters: {parameters}")
        if function == 'query_knowledge_base':
            chunks, user_query = query_knowledge_base(query)
            response_data = {
                'chunks': chunks,
                'user_query': user_query,
                'status': 'KB content retrieved successfully.'
            }
            
        elif function == 'generate_code':
            chunks_str = next((param['value'] for param in parameters if param['name'] == 'chunks'), None)
            query = next((param['value'] for param in parameters if param['name'] == 'query'), None)
            
            # Clean up the chunks string before parsing
            if chunks_str:
                # Remove any leading/trailing whitespace
                chunks_str = chunks_str.strip()
                # Replace single quotes with double quotes for JSON compatibility
                chunks_str = chunks_str.replace("'", '"')
                # Handle escaped quotes
                chunks_str = chunks_str.replace('\\"', '"')
                
                try:
                    chunks = json.loads(chunks_str)
                except Exception as e:
                    logger.error(f"Error parsing chunks with json.loads: {e}")
                    try:
                        # If json.loads fails, try ast.literal_eval
                        chunks = ast.literal_eval(chunks_str)
                    except Exception as e:
                        logger.error(f"Error parsing chunks with ast.literal_eval: {e}")
                        # Create a basic structure from the text
                        chunks = [{'text': chunks_str}]
            else:
                chunks = None
            
            print(f"Chunks retrieved (after parsing): {chunks}")
            print(f"Query to generate code on: {query}")
            
            generated_code = generate_code(chunks, query, input_params)
            response_data = {
                'original_generated_code': generated_code,
                'input_params': input_params,
                'status': 'Code generated successfully'
            }
            
        elif function == 'save_generated_code':
            code_content = next((param['value'] for param in parameters if param['name'] == 'code_content'), None)
            
            code_file_path = save_generated_code(code_content)
            response_data = {
                'file_path': code_file_path,
                'status': f'Code is saved to {code_file_path}'
            }
            
        elif function == 'execute_generated_code':
            code_file_path = next((param['value'] for param in parameters if param['name'] == 'file_path'), None)
            execution_result = execute_generated_code(code_file_path)
            response_data = {
                'execution_result': execution_result,
            }
            
        else:
            raise ValueError(f"Unknown function: {function}")
        print(f"Received response data: {response_data}")
        return populate_function_response(event, response_data)
    except Exception as e:
        error_message = f"Error processing request: {str(e)}"
        logger.error(error_message)
        return populate_function_response(event, {'error': error_message, 'status': 'Error occurred'})