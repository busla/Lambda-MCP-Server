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
from datetime import timedelta
SKLEARN_AVAILABLE = False
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
        
    except ImportError:
        return {
            'status': 'error',
            'message': 'LangChain dependencies not available. Install langchain, sentence-transformers, and faiss-cpu for RAG functionality.',
            'chunks': [],
            'fallback_used': False
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
        
    except ImportError:
        return {
            'status': 'error',
            'message': 'scikit-learn not available for TF-IDF processing. Install scikit-learn for fallback RAG functionality.',
            'chunks': []
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


@mcp_server.tool()
def generate_github_worklog(github_username: str, repo_name: str = "busla/Lambda-MCP-Server", days_back: int = 30) -> str:
    """Generate a detailed worklog from GitHub user activity for invoicing purposes.
    
    Analyzes GitHub activity including commits, PRs, and branches to estimate time spent
    on development work. Calculates work hours based on commit timestamp intervals.
    
    Args:
        github_username: GitHub username to analyze activity for
        repo_name: Repository to analyze (default: busla/Lambda-MCP-Server)
        days_back: Number of days back to analyze (default: 30)
        
    Returns:
        JSON string containing detailed worklog with estimated hours and activity breakdown
    """
    try:
        github_token = os.environ.get('GITHUB_TOKEN')
        if not github_token:
            return json.dumps({"error": "GitHub token not configured. Set GITHUB_TOKEN environment variable."})
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
        
        worklog_data = {
            'username': github_username,
            'repository': repo_name,
            'analysis_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days_analyzed': days_back
            },
            'activity_summary': {},
            'daily_breakdown': {},
            'estimated_hours': {
                'total_hours': 0,
                'billable_hours': 0,
                'methodology': 'commit_interval_analysis'
            },
            'detailed_activities': []
        }
        
        commits_data = _fetch_github_commits(repo_name, github_username, start_date, end_date, headers)
        
        prs_data = _fetch_github_pull_requests(repo_name, github_username, start_date, end_date, headers)
        
        issues_data = _fetch_github_issues_activity(repo_name, github_username, start_date, end_date, headers)
        
        work_sessions = _analyze_work_sessions(commits_data, prs_data, issues_data)
        
        daily_breakdown = _generate_daily_breakdown(work_sessions)
        
        total_hours = sum(day_data['estimated_hours'] for day_data in daily_breakdown.values())
        
        worklog_data.update({
            'activity_summary': {
                'total_commits': len(commits_data),
                'total_pull_requests': len(prs_data),
                'total_issues_activity': len(issues_data),
                'work_sessions_detected': len(work_sessions)
            },
            'daily_breakdown': daily_breakdown,
            'estimated_hours': {
                'total_hours': round(total_hours, 2),
                'billable_hours': round(total_hours * 0.9, 2),  # 90% billable rate
                'methodology': 'commit_interval_analysis_with_session_detection'
            },
            'detailed_activities': work_sessions
        })
        
        return json.dumps(worklog_data, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"GitHub worklog generation failed: {str(e)}"})


def _fetch_github_commits(repo_name: str, username: str, start_date: datetime, end_date: datetime, headers: Dict) -> List[Dict]:
    """Fetch commits from GitHub API for the specified user and date range."""
    commits = []
    page = 1
    per_page = 100
    
    while True:
        url = f"https://api.github.com/repos/{repo_name}/commits"
        params = {
            'author': username,
            'since': start_date.isoformat(),
            'until': end_date.isoformat(),
            'page': page,
            'per_page': per_page
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        page_commits = response.json()
        if not page_commits:
            break
            
        commits.extend(page_commits)
        page += 1
        
        if len(commits) >= 1000:
            break
    
    return commits


def _fetch_github_pull_requests(repo_name: str, username: str, start_date: datetime, end_date: datetime, headers: Dict) -> List[Dict]:
    """Fetch pull requests from GitHub API for the specified user and date range."""
    prs = []
    page = 1
    per_page = 100
    
    while True:
        url = f"https://api.github.com/repos/{repo_name}/pulls"
        params = {
            'state': 'all',
            'sort': 'updated',
            'direction': 'desc',
            'page': page,
            'per_page': per_page
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        page_prs = response.json()
        if not page_prs:
            break
        
        for pr in page_prs:
            if pr['user']['login'] == username:
                pr_date = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
                if start_date <= pr_date <= end_date:
                    prs.append(pr)
        
        page += 1
        
        if page_prs and datetime.fromisoformat(page_prs[-1]['updated_at'].replace('Z', '+00:00')) < start_date:
            break
            
        if len(prs) >= 200:
            break
    
    return prs


def _fetch_github_issues_activity(repo_name: str, username: str, start_date: datetime, end_date: datetime, headers: Dict) -> List[Dict]:
    """Fetch issues activity from GitHub API for the specified user and date range."""
    issues = []
    page = 1
    per_page = 100
    
    while True:
        url = f"https://api.github.com/repos/{repo_name}/issues"
        params = {
            'state': 'all',
            'sort': 'updated',
            'direction': 'desc',
            'page': page,
            'per_page': per_page
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        page_issues = response.json()
        if not page_issues:
            break
        
        for issue in page_issues:
            if issue['user']['login'] == username or any(
                assignee['login'] == username for assignee in issue.get('assignees', [])
            ):
                issue_date = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
                if start_date <= issue_date <= end_date:
                    issues.append(issue)
        
        page += 1
        
        if page_issues and datetime.fromisoformat(page_issues[-1]['updated_at'].replace('Z', '+00:00')) < start_date:
            break
            
        if len(issues) >= 200:
            break
    
    return issues


def _analyze_work_sessions(commits: List[Dict], prs: List[Dict], issues: List[Dict]) -> List[Dict]:
    """Analyze GitHub activity to detect work sessions and estimate time spent."""
    all_activities = []
    
    for commit in commits:
        commit_date = datetime.fromisoformat(commit['commit']['author']['date'].replace('Z', '+00:00'))
        all_activities.append({
            'type': 'commit',
            'timestamp': commit_date,
            'description': commit['commit']['message'][:100],
            'sha': commit['sha'][:8],
            'url': commit['html_url']
        })
    
    for pr in prs:
        pr_date = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
        all_activities.append({
            'type': 'pull_request',
            'timestamp': pr_date,
            'description': f"PR #{pr['number']}: {pr['title'][:80]}",
            'state': pr['state'],
            'url': pr['html_url']
        })
    
    for issue in issues:
        if 'pull_request' not in issue:  # Skip PRs that appear as issues
            issue_date = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
            all_activities.append({
                'type': 'issue',
                'timestamp': issue_date,
                'description': f"Issue #{issue['number']}: {issue['title'][:80]}",
                'state': issue['state'],
                'url': issue['html_url']
            })
    
    all_activities.sort(key=lambda x: x['timestamp'])
    
    work_sessions = []
    current_session = None
    session_gap_threshold = timedelta(hours=2)  # 2 hours gap indicates new session
    min_session_duration = timedelta(minutes=15)  # Minimum 15 minutes per session
    max_session_duration = timedelta(hours=8)  # Maximum 8 hours per session
    
    for activity in all_activities:
        if current_session is None:
            current_session = {
                'start_time': activity['timestamp'],
                'end_time': activity['timestamp'],
                'activities': [activity],
                'estimated_duration_hours': 0
            }
        else:
            time_gap = activity['timestamp'] - current_session['end_time']
            
            if time_gap <= session_gap_threshold:
                current_session['end_time'] = activity['timestamp']
                current_session['activities'].append(activity)
            else:
                session_duration = current_session['end_time'] - current_session['start_time']
                
                if session_duration < min_session_duration:
                    session_duration = min_session_duration
                elif session_duration > max_session_duration:
                    session_duration = max_session_duration
                
                current_session['estimated_duration_hours'] = session_duration.total_seconds() / 3600
                work_sessions.append(current_session)
                
                current_session = {
                    'start_time': activity['timestamp'],
                    'end_time': activity['timestamp'],
                    'activities': [activity],
                    'estimated_duration_hours': 0
                }
    
    if current_session:
        session_duration = current_session['end_time'] - current_session['start_time']
        
        if session_duration < min_session_duration:
            session_duration = min_session_duration
        elif session_duration > max_session_duration:
            session_duration = max_session_duration
            
        current_session['estimated_duration_hours'] = session_duration.total_seconds() / 3600
        work_sessions.append(current_session)
    
    return work_sessions


def _generate_daily_breakdown(work_sessions: List[Dict]) -> Dict:
    """Generate daily breakdown of work hours and activities."""
    daily_breakdown = {}
    
    for session in work_sessions:
        session_date = session['start_time'].date().isoformat()
        
        if session_date not in daily_breakdown:
            daily_breakdown[session_date] = {
                'date': session_date,
                'estimated_hours': 0,
                'sessions_count': 0,
                'activities_count': 0,
                'activity_types': {'commit': 0, 'pull_request': 0, 'issue': 0},
                'sessions': []
            }
        
        daily_breakdown[session_date]['estimated_hours'] += session['estimated_duration_hours']
        daily_breakdown[session_date]['sessions_count'] += 1
        daily_breakdown[session_date]['activities_count'] += len(session['activities'])
        
        for activity in session['activities']:
            activity_type = activity['type']
            if activity_type in daily_breakdown[session_date]['activity_types']:
                daily_breakdown[session_date]['activity_types'][activity_type] += 1
        
        daily_breakdown[session_date]['sessions'].append({
            'start_time': session['start_time'].strftime('%H:%M'),
            'end_time': session['end_time'].strftime('%H:%M'),
            'duration_hours': round(session['estimated_duration_hours'], 2),
            'activities_count': len(session['activities']),
            'primary_activity': session['activities'][0]['description'] if session['activities'] else 'Unknown'
        })
    
    for day_data in daily_breakdown.values():
        day_data['estimated_hours'] = round(day_data['estimated_hours'], 2)
    
    return daily_breakdown


def lambda_handler(event, context):
    """AWS Lambda handler function."""
    return mcp_server.handle_request(event, context)                                                                                                                                                                                                                                    