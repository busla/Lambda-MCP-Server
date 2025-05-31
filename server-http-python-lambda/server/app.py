from lambda_mcp.lambda_mcp import LambdaMCPServer
from datetime import datetime, timezone
import random
import boto3
import os
import requests
from bs4 import BeautifulSoup
import json
# Get session table name from environment variable
session_table = os.environ.get('MCP_SESSION_TABLE', 'mcp_sessions')

# Create the MCP server instance
mcp_server = LambdaMCPServer(name="mcp-lambda-server", version="1.0.0", session_table=session_table)

@mcp_server.tool()
def get_time() -> str:
    """Get the current UTC date and time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

@mcp_server.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a city.
    
    Args:
        city: Name of the city to get weather for
        
    Returns:
        A string describing the weather
    """
    temp = random.randint(15, 35)
    return f"The temperature in {city} is {temp}°C"

@mcp_server.tool()
def count_s3_buckets() -> int:
    """Count the number of S3 buckets."""
    s3 = boto3.client('s3')
    response = s3.list_buckets()
    return len(response['Buckets'])

@mcp_server.tool()
def google_search_and_scrape(query: str, num_results: int = 3) -> str:
    """Search Google and scrape content from the top results.
    
    Args:
        query: The search query to execute
        num_results: Number of results to return and scrape (default 3, max 10)
        
    Returns:
        JSON string containing search results with scraped content
    """
    api_key = os.environ.get('GOOGLE_API_KEY')
    search_engine_id = os.environ.get('GOOGLE_SEARCH_ENGINE_ID')
    
    if not api_key or not search_engine_id:
        return json.dumps({"error": "Google API credentials not configured"})
    
    num_results = min(max(1, num_results), 10)
    
    try:
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': num_results
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        search_data = response.json()
        
        results = []
        
        for item in search_data.get('items', []):
            result = {
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'scraped_content': ''
            }
            
            try:
                page_response = requests.get(result['url'], timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; MCP-Server/1.0)'
                })
                page_response.raise_for_status()
                
                soup = BeautifulSoup(page_response.content, 'html.parser')
                
                for script in soup(["script", "style"]):
                    script.decompose()
                
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                result['scraped_content'] = text[:2000] + ('...' if len(text) > 2000 else '')
                
            except Exception as scrape_error:
                result['scraped_content'] = f"Error scraping content: {str(scrape_error)}"
            
            results.append(result)
        
        return json.dumps({
            'query': query,
            'total_results': len(results),
            'results': results
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"})

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    return mcp_server.handle_request(event, context)  