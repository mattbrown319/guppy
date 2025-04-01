#!/usr/bin/env python3
import os
import sys
import json
import logging
from typing import List, Dict, Any
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich import print as rprint
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Check for required environment variables
required_vars = ["JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_BASE_URL", "OPENAI_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    console = Console()
    console.print(f"[bold red]Error: Missing required environment variables: {', '.join(missing_vars)}[/bold red]")
    console.print("Please update your .env file with the required values.")
    sys.exit(1)

from jira_client_fixed import JiraClient
from llm_client import LLMClient

# Initialize console for rich output
console = Console()

class JiraAIAssistant:
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
            logger.info("Initializing JiraAIAssistant")
            logger.info("Creating JIRA client...")
            self.jira_client = JiraClient(verbose=verbose)
            logger.info("JIRA client created successfully")
            logger.info("Creating LLM client...")
            self.llm_client = LLMClient(verbose=verbose)
            logger.info("LLM client created successfully")
            logger.info("JiraAIAssistant initialized successfully")
        else:
            # In non-verbose mode, just initialize without logging
            self.jira_client = JiraClient(verbose=verbose)
            self.llm_client = LLMClient(verbose=verbose)
        
        # Cache for JIRA issues
        self.issues = None
        self.issues_context = None
        
        # Get available fields
        self.available_fields = self.jira_client.get_available_fields()
        if verbose:
            logger.info("Available fields loaded")
    
    def generate_jql_query(self, question: str) -> str:
        """Use the LLM to generate an appropriate JQL query based on the user's question"""
        if self.verbose:
            logging.info(f"\nConverting question to JQL: {question}")
        
        # Get available priorities
        priorities = self.jira_client.get_priorities()
        priority_names = [p.get("name") for p in priorities]
        
        # Get available field names for JQL
        field_names = [field.get("name") for field in self.available_fields]
        
        if self.verbose:
            logging.info(f"Available priorities: {', '.join(priority_names)}")
            logging.info(f"Available fields: {', '.join(field_names)}")
        
        system_prompt = f"""
        You are a JIRA query expert. Your task is to convert natural language questions into JIRA JQL queries.
        
        Available fields: {', '.join(field_names)}
        
        Focus on:
        1. Priority (Available priorities: {', '.join(priority_names)})
        2. Status (To Do, In Progress, Done)
        3. Due dates and overdue items
        4. Assignee (optional - only include if specifically asked about assigned issues)
        5. Issue types (Story, Bug, Task)
        6. Story point estimate - use this based on context:
           - For quick tasks: "Story point estimate" <= 3
           - For full day tasks: "Story point estimate" >= 5
           - For medium tasks: "Story point estimate" <= 5
           - For long tasks: "Story point estimate" >= 8
        
        Important rules:
        1. For priority queries, use the exact priority names from the list above
        2. For assignee queries, use 'assignee = currentUser()' but only if specifically asked about assigned issues
        3. For status queries, use 'status in ("To Do", "In Progress")' - always use quotes around status values
        4. For due dates, use 'duedate <= now()'
        5. Always include ORDER BY priority DESC, updated DESC
        6. For issue types, use 'issuetype in ("Task", "Story", "Bug")' - always use quotes around type values
        7. For story points, analyze the context:
           - Look for phrases like "full day", "long task", "quick task", "small task"
           - Default to medium tasks (<= 5 points) if no specific duration is mentioned
        8. Always include 'project = "SCRUM"' at the start of the query
        9. Only use fields that are in the available fields list above
        
        Return ONLY the JQL query, nothing else.
        """
        
        user_prompt = f"""
        Convert this question into a JIRA JQL query:
        {question}
        
        The query should be specific and focused on the user's intent.
        Only include assignee = currentUser() if the question specifically asks about assigned issues.
        Remember to use quotes around status and issue type values.
        For story points, consider the context of the question to determine appropriate point range.
        Always start with project = "SCRUM".
        Only use fields that are in the available fields list.
        """
        
        jql_query = self.llm_client.generate_response(user_prompt, system_prompt).strip()
        if self.verbose:
            logging.info(f"Generated JQL query: {jql_query}")
        return jql_query
    
    def fetch_issues(self, jql_query: str = None):
        """Fetch issues using a specific JQL query or get all issues"""
        if self.verbose:
            logging.info("\nFetching JIRA issues...")
            if jql_query:
                logging.info(f"Using JQL query: {jql_query}")
        
        # First verify who we're authenticated as
        try:
            response = self.jira_client.session.get(f"{self.jira_client.base_url}/myself")
            if response.status_code == 200:
                user_info = response.json()
                if self.verbose:
                    logging.info(f"Authenticated as: {user_info.get('emailAddress', 'Unknown')}")
        except Exception as e:
            if self.verbose:
                logging.error(f"Failed to verify authenticated user: {str(e)}")
        
        if jql_query:
            self.issues = self.jira_client.get_all_issues_paginated(jql_query=jql_query)
        else:
            self.issues = self.jira_client.get_all_issues_paginated()
        
        # Check if we got a valid response (even if empty)
        if self.issues is None:
            if self.verbose:
                logging.error("Failed to connect to JIRA")
            console.print("[bold red]Error: Failed to connect to JIRA. Please check your connection and try again.[/bold red]")
            return False
        
        if self.verbose:
            logging.info(f"Retrieved {len(self.issues)} issues")
        
        # Prepare context for the LLM
        self.issues_context = []
        for issue in self.issues[:20]:  # Limit to 20 issues to avoid token limits
            fields = issue.get("fields", {})
            self.issues_context.append({
                "key": issue.get("key", ""),
                "summary": fields.get("summary", ""),
                "status": fields.get("status", {}).get("name", "") if fields.get("status") else "",
                "priority": fields.get("priority", {}).get("name", "") if fields.get("priority") else "",
                "assignee": fields.get("assignee", {}).get("displayName", "") if fields.get("assignee") else "Unassigned",
                "created": fields.get("created", ""),
                "updated": fields.get("updated", ""),
                "dueDate": fields.get("duedate", ""),
                "issueType": fields.get("issuetype", {}).get("name", "") if fields.get("issuetype") else ""
            })
        
        return True
    
    def process_query(self, question: str) -> str:
        """Process a user query and return a response"""
        if self.verbose:
            logging.info(f"\nProcessing query: {question}")
        
        # First check if this is a task creation request
        creation_prompt = """
        You are a JIRA query analyzer. Your task is to determine if the user's question is asking to create a new task.
        
        Look for phrases like:
        - "create a new task"
        - "add a new task"
        - "create a ticket"
        - "add a ticket"
        - "create an issue"
        - "add an issue"
        
        If it is a creation request, extract the following information in JSON format:
        {
            "is_create_request": true,
            "summary": "brief summary of the task",
            "description": "detailed description",
            "priority": "Highest/High/Medium/Low/Lowest",
            "story_points": number,
            "due_date": "YYYY-MM-DD" or null
        }
        
        If it's not a creation request, return:
        {
            "is_create_request": false
        }
        
        Return ONLY the JSON, nothing else.
        """
        
        creation_response = self.llm_client.generate_response(question, creation_prompt).strip()
        try:
            creation_data = json.loads(creation_response)
            if creation_data.get("is_create_request"):
                if self.verbose:
                    logging.info("Detected task creation request")
                return self.create_new_issue(
                    summary=creation_data["summary"],
                    description=creation_data["description"],
                    priority=creation_data["priority"],
                    story_points=creation_data.get("story_points"),
                    due_date=creation_data.get("due_date")
                )
        except json.JSONDecodeError:
            if self.verbose:
                logging.error("Failed to parse creation response")
        
        # Then check if this is an assignment request
        assignment_prompt = """
        You are a JIRA query analyzer. Your task is to determine if the user's question is asking to assign issues to themselves.
        
        Look for phrases like:
        - "assign all issues to me"
        - "take ownership of issues"
        - "claim all issues"
        - "assign tickets to me"
        - "take all tickets"
        
        Return ONLY "yes" or "no", nothing else.
        """
        
        is_assignment_request = self.llm_client.generate_response(question, assignment_prompt).strip().lower()
        
        if is_assignment_request == "yes":
            if self.verbose:
                logging.info("Detected assignment request")
            return self.bulk_assign_issues()
        
        # Generate initial JQL query from the question
        jql_query = self.generate_jql_query(question)
        
        # Try different search strategies if no results found
        search_strategies = [
            {"query": jql_query, "description": "original criteria"},
            {"query": jql_query.replace("priority = Highest", "priority in (Highest, High)"), "description": "high priority"},
            {"query": jql_query.replace("priority = Highest", "priority in (Highest, High, Medium)"), "description": "medium priority"},
            {"query": jql_query.replace("priority = Highest", ""), "description": "any priority"}
        ]
        
        issues = None
        used_strategy = None
        
        for strategy in search_strategies:
            if self.verbose:
                logging.info(f"\nTrying search strategy: {strategy['description']}")
                logging.info(f"Using JQL: {strategy['query']}")
            
            if self.fetch_issues(strategy['query']):
                issues = self.issues
                used_strategy = strategy
                break
        
        if not issues:
            # If still no issues found, try a broader search
            system_prompt = """
            You are a helpful JIRA assistant. The user's query returned no matching issues.
            Your task is to explain why no issues were found and suggest what they might want to try instead.
            Be helpful and constructive in your response.
            """
            
            user_prompt = f"""
            The user asked: {question}
            
            The JQL query used was: {jql_query}
            
            No matching issues were found. Please explain why this might be and suggest what they could try instead.
            """
            
            return self.llm_client.generate_response(user_prompt, system_prompt)
        
        # Create a more concise system prompt
        system_prompt = """
        You are a helpful JIRA assistant. Your task is to analyze JIRA issues and provide concise, focused responses.
        
        Important guidelines:
        1. Be direct and concise - no unnecessary pleasantries or filler text
        2. Focus on the most relevant information first
        3. Include only essential details: issue key, summary, priority, status, and story points
        4. If you had to broaden the search criteria, mention this briefly
        5. For task suggestions, focus on the task's key attributes that make it suitable
        6. Keep responses under 2-3 sentences unless more detail is specifically requested
        
        Example format:
        "SCRUM-123: Implement login page (High priority, 5 points, To Do)"
        """
        
        # Create a more focused user prompt
        user_prompt = f"""
        Based on these JIRA issues, please answer this question concisely:
        {question}
        
        Here are the relevant issues:
        {json.dumps(self.issues_context, indent=2)}
        
        Search strategy used: {used_strategy['description'] if used_strategy else 'original criteria'}
        
        Provide a focused response that highlights the most relevant information.
        """
        
        # Get response from LLM
        response = self.llm_client.generate_response(user_prompt, system_prompt)
        
        if self.verbose:
            logging.info(f"Generated response: {response}")
        
        return response
    
    def get_issue_details(self, issue_key: str) -> Dict[str, Any]:
        """Get detailed information about a specific issue"""
        if not self.issues:
            if not self.fetch_issues():
                return None
        
        for issue in self.issues:
            if issue.get("key") == issue_key:
                return issue
        return None
    
    def create_new_issue(self, summary: str, description: str, priority: str = "Medium", story_points: int = None, due_date: str = None) -> str:
        """Create a new issue in JIRA"""
        try:
            if self.verbose:
                logging.info(f"\nCreating new issue with summary: {summary}")
                if story_points:
                    logging.info(f"Story points: {story_points}")
                if due_date:
                    logging.info(f"Due date: {due_date}")
            
            created_issue = self.jira_client.create_issue(
                summary=summary,
                description=description,
                priority=priority,
                story_points=story_points,
                due_date=due_date
            )
            
            issue_key = created_issue.get("key")
            if self.verbose:
                logging.info(f"Successfully created issue: {issue_key}")
            
            response = f"Successfully created issue {issue_key}:\n\n**Summary:** {summary}\n**Priority:** {priority}"
            if story_points:
                response += f"\n**Story Points:** {story_points}"
            if due_date:
                response += f"\n**Due Date:** {due_date}"
            
            return response
            
        except Exception as e:
            if self.verbose:
                logging.error(f"Error creating issue: {str(e)}")
            return f"Failed to create issue: {str(e)}"
    
    def bulk_assign_issues(self, jql_query: str = "assignee is EMPTY") -> str:
        """Bulk assign issues to the current user"""
        try:
            if self.verbose:
                logging.info(f"\nBulk assigning issues matching query: {jql_query}")
            
            result = self.jira_client.bulk_assign_issues(jql_query=jql_query)
            
            if result["success"]:
                message = f"**{result['message']}**\n"
                if result["count"] > 0:
                    message += f"\nSuccessfully assigned {result['count']} issues"
                if result.get("failed_count", 0) > 0:
                    message += f"\nFailed to assign {result['failed_count']} issues"
                    if result.get("failed_issues"):
                        message += f"\nFailed issues: {', '.join(result['failed_issues'])}"
                return message
            else:
                return f"Failed to assign issues: {result.get('message', 'Unknown error')}"
            
        except Exception as e:
            if self.verbose:
                logging.error(f"Error during bulk assign: {str(e)}")
            return f"Error assigning issues: {str(e)}"

def main():
    # Parse command line arguments
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    console.print(Panel.fit(
        "[bold blue]Welcome to the JIRA AI Assistant![/bold blue]\n\n"
        "I can help you analyze your JIRA issues and answer questions about them.\n"
        "Type 'exit' or 'quit' to end the session.\n"
        "Type 'verbose' to toggle verbose mode.\n"
        "Type 'create' to create a new issue.\n"
        "Type 'assign' to assign unassigned issues to yourself.\n\n"
        "[bold]Example queries:[/bold]\n"
        "  • What are my top priorities?\n"
        "  • Which issues are overdue?\n"
        "  • Give me a summary of my current tasks\n"
        "  • What's the status of SCRUM-61?",
        title="JIRA AI Assistant",
        border_style="blue"
    ))
    
    assistant = JiraAIAssistant(verbose=verbose)
    
    while True:
        try:
            # Get user input
            console.print("\n[bold blue]Enter your question:[/bold blue] ", end="")
            query = input().strip()
            
            if query.lower() in ("exit", "quit", "bye"):
                console.print("[bold blue]Goodbye![/bold blue]")
                break
            
            if query.lower() == "verbose":
                verbose = not verbose
                assistant.verbose = verbose
                if verbose:
                    logging.getLogger().setLevel(logging.DEBUG)
                    console.print("[bold green]Verbose mode enabled[/bold green]")
                else:
                    logging.getLogger().setLevel(logging.INFO)
                    console.print("[bold green]Verbose mode disabled[/bold green]")
                continue
            
            if query.lower() == "create":
                console.print("\n[bold blue]Creating new issue...[/bold blue]")
                console.print("Enter issue summary: ", end="")
                summary = input().strip()
                
                console.print("Enter issue description (press Enter twice to finish):")
                description_lines = []
                while True:
                    line = input()
                    if line.strip() == "":
                        break
                    description_lines.append(line)
                description = "\n".join(description_lines)
                
                console.print("Enter issue type (Task/Story/Bug) [default: Task]: ", end="")
                issue_type = input().strip() or "Task"
                
                console.print("Enter priority (Highest/High/Medium/Low/Lowest) [default: Medium]: ", end="")
                priority = input().strip() or "Medium"
                
                response = assistant.create_new_issue(
                    summary=summary,
                    description=description,
                    priority=priority
                )
                
                console.print("\n[bold blue]Assistant:[/bold blue]")
                console.print(Markdown(response))
                continue
            
            if query.lower() == "assign":
                console.print("\n[bold blue]Assigning unassigned issues to you...[/bold blue]")
                response = assistant.bulk_assign_issues()
                console.print("\n[bold blue]Assistant:[/bold blue]")
                console.print(Markdown(response))
                continue
            
            if not query:
                continue
            
            # Process the query
            console.print("[bold blue]Thinking...[/bold blue]")
            response = assistant.process_query(query)
            
            # Display response
            console.print("\n[bold blue]Assistant:[/bold blue]")
            console.print(Markdown(response))
            
        except KeyboardInterrupt:
            console.print("\n[bold blue]Goodbye![/bold blue]")
            break
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")
            console.print("Please try again or type 'exit' to quit.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        sys.exit(1) 