import os
import requests
import json
import sys
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List

# Load environment variables from .env file
load_dotenv()

class JiraClient:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        if verbose:
            logging.basicConfig(
                level=logging.INFO,
                format='%(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout)
                ]
            )
        else:
            # In non-verbose mode, only show warnings and errors
            logging.basicConfig(
                level=logging.WARNING,
                format='%(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout)
                ]
            )
        
        logger = logging.getLogger(__name__)
        if verbose:
            logger.info("Initializing JIRA client")
        
        # Load JIRA credentials from environment
        self.email = os.getenv("JIRA_EMAIL")
        self.api_token = os.getenv("JIRA_API_TOKEN")
        base_url = os.getenv("JIRA_BASE_URL", "").strip()
        
        # Ensure base URL has https:// scheme
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
        
        # Add /rest/api/2 to the base URL if not present
        if not base_url.endswith("/rest/api/2"):
            base_url = f"{base_url}/rest/api/2"
        
        self.base_url = base_url
        
        if not all([self.email, self.api_token, self.base_url]):
            raise ValueError("Missing required environment variables. Please set JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_BASE_URL")
        
        if verbose:
            logger.info("JIRA credentials loaded successfully")
            logger.info(f"Using JIRA base URL: {self.base_url}")
        
        # Create session with authentication
        self.session = requests.Session()
        self.session.auth = (self.email, self.api_token)
        
        if verbose:
            logger.info("JIRA client initialized successfully")
    
    def get_all_issues(self, max_results=50, start_at=0, jql_query: str = None):
        """
        Fetch issues from JIRA
        
        Args:
            max_results (int): Maximum number of results to return (default: 50)
            start_at (int): Index of the first issue to return (default: 0)
            jql_query (str, optional): JQL query to filter issues
            
        Returns:
            dict: JSON response from JIRA API
        """
        url = f"{self.base_url}/search"
        if self.verbose:
            print(f"Making API request to: {url}")
        
        # Build JQL query
        if jql_query:
            query = {
                "jql": jql_query,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": ["summary", "status", "assignee", "priority", "created", "updated", "duedate", "issuetype"]
            }
        else:
            query = {
                "jql": "order by created DESC",
                "startAt": start_at,
                "maxResults": max_results,
                "fields": ["summary", "status", "assignee", "priority", "created", "updated", "duedate", "issuetype"]
            }
        
        if self.verbose:
            print(f"Using query: {json.dumps(query, indent=2)}")
        
        try:
            if self.verbose:
                print("Sending API request...")
            response = self.session.post(url, json=query)
            
            if self.verbose:
                print(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                print(f"Response headers: {response.headers}")
                print(f"Response body: {response.text}")
                return None
            
            json_response = response.json()
            if self.verbose:
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
    
    def get_all_issues_paginated(self, jql_query: str = None, max_results: int = 50):
        """Get all issues with pagination support"""
        all_issues = []
        start_at = 0
        
        while True:
            if self.verbose:
                logging.info(f"\nFetching page of issues (start_at={start_at}, max_results={max_results})")
                if jql_query:
                    logging.info(f"Using JQL query: {jql_query}")
            
            # Build the query
            query = {
                "startAt": start_at,
                "maxResults": max_results,
                "fields": [
                    "summary",
                    "status",
                    "assignee",
                    "priority",
                    "created",
                    "updated",
                    "duedate",
                    "issuetype",
                    "Story point estimate"  # Add story points field directly
                ]
            }
            
            if jql_query:
                query["jql"] = jql_query
            
            if self.verbose:
                logging.info(f"Making API request to: {self.base_url}/search")
                logging.info(f"Using query: {json.dumps(query, indent=2)}")
            
            try:
                response = self.session.post(f"{self.base_url}/search", json=query)
                
                if self.verbose:
                    logging.info(f"Response status code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    issues = data.get("issues", [])
                    total = data.get("total", 0)
                    
                    if self.verbose:
                        logging.info(f"Successfully retrieved data. Total issues: {total}")
                        logging.info(f"Retrieved {len(issues)} issues in this page")
                    
                    all_issues.extend(issues)
                    
                    if self.verbose:
                        logging.info(f"Total issues: {len(all_issues)}, Next start_at: {start_at + max_results}")
                    
                    if len(issues) < max_results:
                        if self.verbose:
                            logging.info("No more issues to retrieve")
                        break
                    
                    start_at += max_results
                else:
                    if self.verbose:
                        logging.error(f"Error: {response.status_code}")
                        logging.error(f"Response headers: {dict(response.headers)}")
                        logging.error(f"Response body: {response.text}")
                    logger.error("Error fetching issues")
                    return None
                    
            except requests.exceptions.RequestException as e:
                if self.verbose:
                    logging.error(f"Request error: {str(e)}")
                logger.error("Error fetching issues")
                return None
            except json.JSONDecodeError as e:
                if self.verbose:
                    logging.error(f"JSON decode error: {str(e)}")
                logger.error("Error parsing response")
                return None
        
        return all_issues

    def get_available_fields(self) -> List[Dict[str, Any]]:
        """Get all available fields from JIRA"""
        if self.verbose:
            logging.info("\nFetching available fields")
        
        try:
            response = self.session.get(f"{self.base_url}/field")
            if response.status_code == 200:
                fields = response.json()
                if self.verbose:
                    logging.info("Available fields:")
                    for field in fields:
                        logging.info(f"  • {field.get('name')} (ID: {field.get('id')})")
                return fields
            else:
                if self.verbose:
                    logging.error(f"Failed to get fields: {response.status_code}")
                    logging.error(f"Response: {response.text}")
                return []
        except Exception as e:
            if self.verbose:
                logging.error(f"Error getting fields: {str(e)}")
            return []

    def create_issue(self, summary: str, description: str, priority: str = "Medium", story_points: int = None, due_date: str = None) -> Dict[str, Any]:
        """Create a new issue in JIRA"""
        try:
            if self.verbose:
                logging.info(f"\nCreating new issue with summary: {summary}")
            
            # Get available fields
            fields = self.get_available_fields()
            field_names = {field.get("name"): field.get("id") for field in fields}
            
            # Step 1: Create the issue with basic required fields
            issue_data = {
                "fields": {
                    "project": {"key": "SCRUM"},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": "Task"}
                }
            }
            
            if self.verbose:
                logging.info(f"Creating issue with basic data: {json.dumps(issue_data, indent=2)}")
            
            # Create the issue
            response = self.session.post(
                f"{self.base_url}/issue",
                json=issue_data
            )
            
            if response.status_code != 201:
                error_msg = f"Failed to create issue. Status code: {response.status_code}"
                if self.verbose:
                    logging.error(error_msg)
                    logging.error(f"Response: {response.text}")
                raise Exception(error_msg)
            
            created_issue = response.json()
            issue_key = created_issue.get("key")
            
            if self.verbose:
                logging.info(f"Successfully created issue: {issue_key}")
            
            # Step 2: Update the issue with additional fields
            update_data = {"fields": {}}
            
            # Add priority if it exists
            if "Priority" in field_names:
                update_data["fields"][field_names["Priority"]] = {"name": priority}
            
            # Add story points if they exist
            if story_points is not None and "Story point estimate" in field_names:
                update_data["fields"][field_names["Story point estimate"]] = story_points
            
            # Add due date if it exists
            if due_date and "Due date" in field_names:
                update_data["fields"][field_names["Due date"]] = due_date
            
            # Only make the update request if we have fields to update
            if update_data["fields"]:
                if self.verbose:
                    logging.info(f"Updating issue with additional fields: {json.dumps(update_data, indent=2)}")
                
                update_response = self.session.put(
                    f"{self.base_url}/issue/{issue_key}",
                    json=update_data
                )
                
                if update_response.status_code != 204:
                    if self.verbose:
                        logging.warning(f"Some fields could not be updated: {update_response.status_code}")
                        logging.warning(f"Update response: {update_response.text}")
            
            return created_issue
            
        except Exception as e:
            if self.verbose:
                logging.error(f"Error creating issue: {str(e)}")
            raise

    def get_priorities(self) -> List[Dict[str, Any]]:
        """Get all available priorities from JIRA"""
        if self.verbose:
            logging.info("\nFetching available priorities")
        
        try:
            response = self.session.get(f"{self.base_url}/priority")
            if response.status_code == 200:
                priorities = response.json()
                if self.verbose:
                    logging.info("Available priorities:")
                    for priority in priorities:
                        logging.info(f"  • {priority.get('name')} (ID: {priority.get('id')})")
                return priorities
            else:
                if self.verbose:
                    logging.error(f"Failed to get priorities: {response.status_code}")
                    logging.error(f"Response: {response.text}")
                return []
        except Exception as e:
            if self.verbose:
                logging.error(f"Error getting priorities: {str(e)}")
            return []

    def bulk_assign_issues(self, jql_query: str = "assignee is EMPTY") -> Dict[str, Any]:
        """
        Bulk assign issues to the current user.
        
        Args:
            jql_query (str): JQL query to find issues to assign (default: unassigned issues)
            
        Returns:
            Dict[str, Any]: Summary of the operation
        """
        if self.verbose:
            logging.info(f"\nBulk assigning issues matching query: {jql_query}")
        
        try:
            # First get the authenticated user's account ID
            response = self.session.get(f"{self.base_url}/myself")
            if response.status_code != 200:
                raise Exception(f"Failed to get user info: {response.status_code}")
            
            user_info = response.json()
            account_id = user_info.get("accountId")
            
            if not account_id:
                raise Exception("Could not get user account ID")
            
            if self.verbose:
                logging.info(f"Authenticated user account ID: {account_id}")
            
            # Get all issues matching the query
            issues = self.get_all_issues_paginated(jql_query=jql_query)
            if not issues:
                if self.verbose:
                    logging.info("No issues found matching the query")
                return {"success": True, "message": "No issues found to assign", "count": 0}
            
            if self.verbose:
                logging.info(f"Found {len(issues)} issues to assign")
                # Log priority distribution
                priority_counts = {}
                for issue in issues:
                    priority = issue.get("fields", {}).get("priority", {}).get("name", "None")
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1
                logging.info("\nPriority distribution:")
                for priority, count in priority_counts.items():
                    logging.info(f"  • {priority}: {count} issues")
            
            # Assign each issue
            assigned_count = 0
            failed_count = 0
            failed_issues = []
            
            for issue in issues:
                issue_key = issue.get("key")
                try:
                    # Update the issue's assignee using the assignee endpoint
                    update_data = {
                        "accountId": account_id
                    }
                    
                    if self.verbose:
                        logging.info(f"Assigning {issue_key} to {account_id}")
                    
                    response = self.session.put(
                        f"{self.base_url}/issue/{issue_key}/assignee",
                        json=update_data
                    )
                    
                    if response.status_code in (204, 200):  # Success
                        assigned_count += 1
                        if self.verbose:
                            logging.info(f"Successfully assigned {issue_key}")
                    else:
                        failed_count += 1
                        failed_issues.append(issue_key)
                        if self.verbose:
                            logging.error(f"Failed to assign {issue_key}: {response.status_code}")
                            logging.error(f"Response: {response.text}")
                
                except Exception as e:
                    failed_count += 1
                    failed_issues.append(issue_key)
                    if self.verbose:
                        logging.error(f"Error assigning {issue_key}: {str(e)}")
            
            result = {
                "success": True,
                "message": f"Successfully assigned {assigned_count} issues",
                "count": assigned_count,
                "failed_count": failed_count
            }
            
            if failed_issues:
                result["failed_issues"] = failed_issues
            
            if self.verbose:
                logging.info(f"Bulk assign complete. Success: {assigned_count}, Failed: {failed_count}")
            
            return result
            
        except Exception as e:
            if self.verbose:
                logging.error(f"Error during bulk assign: {str(e)}")
            raise

if __name__ == "__main__":
    print("Starting JIRA client...")
    
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