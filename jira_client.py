import os
import requests
import json
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class JiraClient:
    def __init__(self):
        self.email = os.getenv("JIRA_EMAIL")
        self.api_token = os.getenv("JIRA_API_TOKEN")
        self.domain = os.getenv("JIRA_DOMAIN")
        # Print initialization information for debugging
        print(f"Initializing JIRA client with:")
        print(f"  Email: {self.email}")
        print(f"  Domain: {self.domain}")
        print(f"  API Token: {self.api_token[:5]}...{self.api_token[-5:] if self.api_token else ''}")
        
        # Ensure domain doesn't have trailing slash
        if self.domain and self.domain.endswith('/'):
            self.domain = self.domain.rstrip('/')
        
        self.base_url = f"https://{self.domain}/rest/api/3"
        print(f"Base URL: {self.base_url}")
        self.auth = (self.email, self.api_token)
    
    def get_all_issues(self, max_results=50, start_at=0):
        """
        Fetch all issues from JIRA
        
        Args:
            max_results (int): Maximum number of results to return (default: 50)
            start_at (int): Index of the first issue to return (default: 0)
            
        Returns:
            dict: JSON response from JIRA API
        """
        url = f"{self.base_url}/search"
        print(f"Making API request to: {url}")
        
        # JQL query to get all issues
        query = {
            "jql": "order by created DESC",
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ["summary", "status", "assignee", "priority", "created", "updated"]
        }
        
        print(f"Using query: {json.dumps(query, indent=2)}")
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        try:
            print("Sending API request...")
            response = requests.post(
                url,
                json=query,
                headers=headers,
                auth=self.auth
            )
            
            print(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                print(f"Response headers: {response.headers}")
                print(f"Response body: {response.text}")
                return None
            
            json_response = response.json()
            print(f"Successfully retrieved data. Total issues: {json_response.get('total', 0)}")
            return json_response
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response text: {response.text}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def get_all_issues_paginated(self, max_results_per_page=50):
        """
        Fetch all issues from JIRA with pagination
        
        Args:
            max_results_per_page (int): Maximum number of results per page (default: 50)
            
        Returns:
            list: List of all issues
        """
        all_issues = []
        start_at = 0
        total = None
        
        while total is None or start_at < total:
            print(f"\nFetching page of issues (start_at={start_at}, max_results={max_results_per_page})")
            response = self.get_all_issues(max_results=max_results_per_page, start_at=start_at)
            
            if response is None:
                print("Received None response, stopping pagination")
                break
                
            issues = response.get("issues", [])
            print(f"Retrieved {len(issues)} issues in this page")
            all_issues.extend(issues)
            
            # Update total and start_at for next iteration
            total = response.get("total", 0)
            start_at += len(issues)
            
            print(f"Total issues: {total}, Next start_at: {start_at}")
            
            if len(issues) == 0:
                print("No more issues to retrieve")
                break
        
        return all_issues

if __name__ == "__main__":
    print("Starting JIRA client...")
    
    # Check if required environment variables are set
    required_vars = ["JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_DOMAIN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please update your .env file with the required values.")
        sys.exit(1)
    
    # Initialize JIRA client
    print("Initializing JIRA client...")
    jira = JiraClient()
    
    # Get all issues
    print("Retrieving all issues...")
    issues = jira.get_all_issues_paginated()
    
    if issues:
        print(f"\nFound {len(issues)} issues:")
        for i, issue in enumerate(issues[:10], 1):  # Print first 10 issues
            fields = issue.get("fields", {})
            key = issue.get("key", "N/A")
            summary = fields.get("summary", "N/A")
            status = fields.get("status", {}).get("name", "N/A")
            print(f"{i}. {key}: {summary} (Status: {status})")
        
        if len(issues) > 10:
            print(f"... and {len(issues) - 10} more issues")
    else:
        print("\nNo issues found or error occurred. Please check the error messages above.") 