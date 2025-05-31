from lambda_mcp.lambda_mcp import LambdaMCPServer
from datetime import datetime, timezone
import random
import boto3
import os
import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
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
def google_search_and_scrape(query: str, num_results: int = 3, use_playwright: bool = False, use_rag: bool = False, chunk_size: int = 500) -> str:
    """Search Google and scrape content from the top results with optional RAG processing.
    
    Args:
        query: The search query to execute
        num_results: Number of results to return and scrape (default 3, max 10)
        use_playwright: Whether to use Playwright for JavaScript-rendered content (default False)
        use_rag: Whether to apply RAG processing with chunking and relevance scoring (default False)
        chunk_size: Size of text chunks for RAG processing (default 500 characters)
        
    Returns:
        JSON string containing search results with scraped content and optional RAG analysis
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
                'scraped_content': '',
                'scraping_method': 'playwright' if use_playwright else 'requests'
            }
            
            if use_playwright:
                result['scraped_content'] = _scrape_with_playwright(result['url'])
            else:
                result['scraped_content'] = _scrape_with_requests(result['url'])
            
            results.append(result)
        
        response_data = {
            'query': query,
            'total_results': len(results),
            'results': results
        }
        
        if use_rag and results:
            rag_analysis = _apply_rag_processing(query, results, chunk_size)
            response_data['rag_analysis'] = rag_analysis
        
        return json.dumps(response_data, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"})

def _scrape_with_requests(url: str) -> str:
    """Scrape content using requests + BeautifulSoup (fast, no JavaScript)"""
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; MCP-Server/1.0)'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text[:2000] + ('...' if len(text) > 2000 else '')
        
    except Exception as scrape_error:
        return f"Error scraping content: {str(scrape_error)}"


def _scrape_with_playwright(url: str) -> str:
    """Scrape content using Playwright (slower, supports JavaScript)"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _scrape_with_requests(url) + " [Note: Using requests fallback - Playwright not available]"
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            is_lambda = bool(os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
            
            if is_lambda and os.path.exists('/opt/chrome/chrome'):
                browser = p.chromium.launch(
                    executable_path='/opt/chrome/chrome',
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--single-process',
                        '--no-zygote',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding'
                    ]
                )
            else:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-web-security'
                    ]
                )
            
            try:
                page = browser.new_page()
                page.set_default_timeout(15000)
                
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                
                response = page.goto(url, wait_until='domcontentloaded')
                
                if response and response.status >= 400:
                    if response.status == 403:
                        return f"Access denied (403): Website blocks automated access. Try using snippet instead."
                    elif response.status == 404:
                        return f"Page not found (404): The URL may have moved or been deleted."
                    elif response.status == 429:
                        return f"Rate limited (429): Too many requests. Try again later."
                    elif response.status >= 500:
                        return f"Server error ({response.status}): The website is experiencing issues."
                    else:
                        return f"HTTP error ({response.status}): Unable to access page."
                
                page.wait_for_timeout(3000)
                
                try:
                    page.wait_for_selector('body', timeout=5000)
                except:
                    pass
                
                text = page.evaluate('() => document.body.innerText || document.body.textContent || ""')
                
                if not text or len(text.strip()) < 50:
                    html = page.content()
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    for script in soup(["script", "style"]):
                        script.decompose()
                    text = soup.get_text()
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text[:2000] + ('...' if len(text) > 2000 else '')
                
            finally:
                browser.close()
                
    except ImportError:
        return "Playwright not installed. Install with: pip install playwright && playwright install chromium"
    except Exception as scrape_error:
        return f"Playwright scraping error: {str(scrape_error)}"


def _apply_rag_processing(query: str, results: List[Dict], chunk_size: int = 500) -> Dict:
    """Apply RAG processing with content chunking and relevance scoring using LangChain."""
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.schema import Document
        from langchain_community.vectorstores import FAISS
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_size // 4,  # 25% overlap
            add_start_index=True
        )
        
        all_documents = []
        for i, result in enumerate(results):
            content = result.get('scraped_content', '')
            if content and not content.startswith('Error'):
                doc = Document(
                    page_content=content,
                    metadata={
                        'source_url': result.get('url', ''),
                        'title': result.get('title', ''),
                        'snippet': result.get('snippet', ''),
                        'result_index': i,
                        'scraping_method': result.get('scraping_method', 'unknown')
                    }
                )
                all_documents.append(doc)
        
        if not all_documents:
            return {
                'status': 'no_content',
                'message': 'No valid content found for RAG processing',
                'chunks': [],
                'relevance_scores': []
            }
        
        chunks = text_splitter.split_documents(all_documents)
        
        try:
            embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight model
        except Exception as e:
            return _apply_tfidf_rag_processing(query, chunks)
        
        vector_store = FAISS.from_documents(
            chunks, 
            embeddings_model
        )
        
        relevant_chunks = vector_store.similarity_search_with_score(
            query, 
            k=min(5, len(chunks))  # Top 5 most relevant chunks
        )
        
        rag_results = []
        for chunk, score in relevant_chunks:
            rag_results.append({
                'content': chunk.page_content,
                'relevance_score': float(1 - score),  # Convert distance to similarity
                'metadata': chunk.metadata,
                'chunk_index': len(rag_results)
            })
        
        top_content = ' '.join([r['content'] for r in rag_results[:3]])
        summary = _create_content_summary(query, top_content)
        
        return {
            'status': 'success',
            'total_chunks': len(chunks),
            'relevant_chunks': len(rag_results),
            'chunks': rag_results,
            'summary': summary,
            'query_analysis': {
                'original_query': query,
                'chunk_size': chunk_size,
                'embedding_model': 'all-MiniLM-L6-v2'
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'RAG processing failed: {str(e)}',
            'chunks': [],
            'fallback_used': True
        }


def _apply_tfidf_rag_processing(query: str, chunks: List) -> Dict:
    """Fallback RAG processing using TF-IDF when embeddings are not available."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        chunk_texts = [chunk.page_content for chunk in chunks]
        
        if not chunk_texts:
            return {
                'status': 'no_content',
                'message': 'No chunks available for TF-IDF processing'
            }
        
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        all_texts = chunk_texts + [query]
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        
        query_vector = tfidf_matrix[-1]  # Last item is the query
        chunk_vectors = tfidf_matrix[:-1]  # All except the query
        
        similarities = cosine_similarity(query_vector, chunk_vectors).flatten()
        
        chunk_scores = list(zip(chunks, similarities))
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        
        rag_results = []
        for chunk, score in chunk_scores[:5]:  # Top 5 chunks
            rag_results.append({
                'content': chunk.page_content,
                'relevance_score': float(score),
                'metadata': chunk.metadata,
                'chunk_index': len(rag_results)
            })
        
        return {
            'status': 'success_tfidf',
            'total_chunks': len(chunks),
            'relevant_chunks': len(rag_results),
            'chunks': rag_results,
            'summary': f'Found {len(rag_results)} relevant chunks using TF-IDF similarity',
            'query_analysis': {
                'original_query': query,
                'method': 'TF-IDF',
                'max_features': 1000
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'TF-IDF RAG processing failed: {str(e)}'
        }


def _create_content_summary(query: str, content: str, max_length: int = 300) -> str:
    """Create a concise summary of the most relevant content."""
    try:
        sentences = content.split('. ')
        
        query_terms = set(query.lower().split())
        scored_sentences = []
        
        for sentence in sentences:
            sentence_terms = set(sentence.lower().split())
            overlap_score = len(query_terms.intersection(sentence_terms))
            if overlap_score > 0 and len(sentence.strip()) > 20:
                scored_sentences.append((sentence.strip(), overlap_score))
        
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        summary_parts = []
        current_length = 0
        
        for sentence, _ in scored_sentences:
            if current_length + len(sentence) <= max_length:
                summary_parts.append(sentence)
                current_length += len(sentence)
            else:
                break
        
        return '. '.join(summary_parts) + '.' if summary_parts else 'No relevant summary available.'
        
    except Exception:
        return 'Summary generation failed.'


def lambda_handler(event, context):
    """AWS Lambda handler function."""
    return mcp_server.handle_request(event, context)                                                                    