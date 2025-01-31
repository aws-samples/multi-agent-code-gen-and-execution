# This file contains parameters that are used across the multi agent solution
# for example, model ids for each sub agents, associated directories that contain
# results, data, etc.
CONFIG_FNAME: str = "config.yaml"

# These are the names of the sub agents that are used across the multi agent solution
# These are used to identify the sub agents in the multi agent solution
HOME_NETWORK_AGENT_NAME: str = "home-network-assistant"
HOME_NETWORK_LAMBDA_FUNCTION_NAME: str = "fn-home-network-assistant"
HOME_NETWORK_AGENT_ROLE_NAME: str = 'AmazonBedrockExecutionRoleForAgents_homenetwork'
DOORBELL_AGENT_NAME: str = "doorbell-assistant"

# Home network knowledge base name
HOME_NETWORK_KB_NAME: str = "home-network-kb"
HOME_NETWORK_KB_DESCRIPTION: str = "Home Network Knowledge Base containing home network API specs"
HOME_NETWORK_KB_LAMBDA_FUNCTION_NAME: str = "kb-query-function-home-network"
HOME_NETWORK_AGENT_LAMBDA_FUNCTION_NAME: str = "home_network_agent_lambda_function.py"
HOME_NETWORK_ACTION_GROUP_NAME : str = "homenetwork-ag"

# Doorbell Knowledge base 
DOORBELL_KB_NAME: str = "doorbell-kb"
DOORBELL_KB_DESCRIPTION: str = "doorbell Knowledge Base containing doorbell related API specs"
DOORBELL_KB_LAMBDA_FUNCTION_NAME: str = "kb-query-function-doorbell"
DOORBELL_AGENT_LAMBDA_FUNCTION_NAME: str = "doorbell_agent_lambda_function.py"
DOORBELL_ACTION_GROUP_NAME : str = "doorbellag"

# Multi agent variables
MULTI_AGENT_NAME: str = "multi-agent-homenetwork-doorbell"

# Models on Amazon Bedrock
BEDROCK_MODEL_NOVA_PRO: str = "amazon.nova-pro-v1:0"
BEDROCK_MODEL_NOVA_MICRO: str = "amazon.nova-micro-v1:0"
BEDROCK_MODEL_NOVA_LITE: str = "amazon.nova-lite-v1:0"
BEDROCK_MODEL_CLAUDE_3_HAIKU: str = "anthropic.claude-3-haiku-20240307-v1:0"

# KB lambda functions for home network and doorbell knowledge bases
HOME_NETWORK_KB_LAMBDA_FUNCTION: str = "home_network_kb_lambda_function.py"
DOORBELL_KB_LAMBDA_FUNCTION: str = "doorbell_kb_lambda_function.py"