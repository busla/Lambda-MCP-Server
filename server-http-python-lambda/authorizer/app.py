import os
import json

def lambda_handler(event, context):
    """Lambda authorizer for API Gateway."""
    
    # Get the Authorization header from the event
    auth_header = event.get('authorizationToken', '')
    method_arn = event['methodArn']
    
    # Check if it's a Bearer token
    if not auth_header.startswith('Bearer '):
        return {
            'principalId': 'unauthorized',
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Deny',
                    'Resource': method_arn
                }]
            }
        }
        
    # Extract and validate token
    token = auth_header.split(' ')[1]
    expected_token = os.environ.get('MCP_AUTH_TOKEN')
    
    if not expected_token or token != expected_token:
        return {
            'principalId': 'unauthorized',
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Deny',
                    'Resource': method_arn
                }]
            }
        }
        
    # Generate the IAM policy
    return {
        'principalId': 'user',
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': 'Allow',
                'Resource': method_arn
            }]
        }
    }  