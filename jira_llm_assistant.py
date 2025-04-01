#!/usr/bin/env python3
import os
import sys
import json
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich import print as rprint
from typing import Optional, List

from jira_client_fixed import JiraClient
from llm_client import LLMClient

# Initialize console for rich output
console = Console()

# Create Typer app
app = typer.Typer(help="JIRA LLM Assistant - Interact with JIRA using AI")

def check_api_keys():
    """Check if required API keys are set"""
    missing_keys = []
    
    if not os.getenv("JIRA_API_TOKEN"):
        missing_keys.append("JIRA_API_TOKEN")
    if not os.getenv("JIRA_EMAIL"):
        missing_keys.append("JIRA_EMAIL")
    if not os.getenv("JIRA_DOMAIN"):
        missing_keys.append("JIRA_DOMAIN")
    if not os.getenv("OPENAI_API_KEY"):
        missing_keys.append("OPENAI_API_KEY")
    
    if missing_keys:
        console.print(f"[bold red]Error: Missing required API keys: {', '.join(missing_keys)}[/bold red]")
        console.print("Please update your .env file with the required values.")
        sys.exit(1)

@app.command()
def summary(limit: int = typer.Option(20, help="Maximum number of issues to analyze")):
    """Generate a summary of your JIRA issues"""
    check_api_keys()
    
    with console.status("[bold green]Connecting to JIRA..."):
        jira_client = JiraClient()
    
    with console.status("[bold green]Fetching JIRA issues..."):
        issues = jira_client.get_all_issues_paginated()
        if not issues:
            console.print("[bold red]No issues found or error occurred.[/bold red]")
            return
        
        # Limit issues for analysis
        issues_to_analyze = issues[:limit]
        console.print(f"[bold green]Successfully retrieved {len(issues)} issues. Analyzing the {len(issues_to_analyze)} most recent...[/bold green]")
    
    with console.status("[bold green]Generating summary with AI..."):
        llm_client = LLMClient()
        summary = llm_client.summarize_issues(issues_to_analyze)
    
    # Display summary
    console.print(Panel(Markdown(summary), title="JIRA Issues Summary", border_style="blue"))

@app.command()
def analyze(issue_key: str = typer.Argument(..., help="JIRA issue key to analyze (e.g., PRJ-123)")):
    """Analyze a specific JIRA issue in detail"""
    check_api_keys()
    
    with console.status(f"[bold green]Fetching issue {issue_key}..."):
        jira_client = JiraClient()
        
        # Custom JQL to get a specific issue with all fields
        query = {
            "jql": f"key = {issue_key}",
            "fields": ["*all"]  # Request all fields
        }
        
        # Use the base URL without the search endpoint
        url = f"{jira_client.base_url}/search"
        
        response = jira_client.client.post(
            url,
            json=query,
            headers=jira_client.headers,
            auth=jira_client.auth
        )
        
        if response.status_code != 200:
            console.print(f"[bold red]Error fetching issue {issue_key}: {response.status_code}[/bold red]")
            console.print(response.text)
            return
        
        data = response.json()
        issues = data.get("issues", [])
        
        if not issues:
            console.print(f"[bold red]Issue {issue_key} not found.[/bold red]")
            return
        
        issue = issues[0]
    
    with console.status("[bold green]Analyzing issue with AI..."):
        llm_client = LLMClient()
        analysis = llm_client.analyze_issue(issue)
    
    # Display analysis
    console.print(Panel(Markdown(analysis), title=f"Analysis of {issue_key}", border_style="green"))

@app.command()
def create_jql(query: str = typer.Argument(..., help="Natural language query to convert to JQL")):
    """Convert a natural language query to JQL"""
    check_api_keys()
    
    with console.status("[bold green]Generating JQL query..."):
        llm_client = LLMClient()
        jql = llm_client.generate_jql_query(query)
    
    # Display JQL
    console.print(Panel(jql, title="Generated JQL Query", border_style="yellow"))
    
    # Ask if user wants to run the query
    run_query = typer.confirm("Would you like to run this query?")
    
    if run_query:
        with console.status("[bold green]Running JQL query..."):
            jira_client = JiraClient()
            
            # Use the generated JQL
            response = jira_client.client.post(
                f"{jira_client.base_url}/search",
                json={"jql": jql, "maxResults": 20},
                headers=jira_client.headers,
                auth=jira_client.auth
            )
            
            if response.status_code != 200:
                console.print(f"[bold red]Error running JQL query: {response.status_code}[/bold red]")
                console.print(response.text)
                return
            
            data = response.json()
            issues = data.get("issues", [])
            
            if not issues:
                console.print("[bold yellow]No issues found matching this query.[/bold yellow]")
                return
            
            console.print(f"[bold green]Found {len(issues)} issues:[/bold green]")
            for i, issue in enumerate(issues, 1):
                fields = issue.get("fields", {})
                key = issue.get("key", "N/A")
                summary = fields.get("summary", "N/A")
                status = fields.get("status", {}).get("name", "N/A") if fields.get("status") else "N/A"
                console.print(f"{i}. [bold blue]{key}[/bold blue]: {summary} (Status: {status})")

@app.command()
def improve(issue_key: str = typer.Argument(..., help="JIRA issue key to suggest improvements for")):
    """Suggest improvements for a JIRA issue"""
    check_api_keys()
    
    with console.status(f"[bold green]Fetching issue {issue_key}..."):
        jira_client = JiraClient()
        
        # Custom JQL to get a specific issue
        query = {
            "jql": f"key = {issue_key}",
            "fields": ["summary", "description", "status", "priority"]
        }
        
        response = jira_client.client.post(
            f"{jira_client.base_url}/search",
            json=query,
            headers=jira_client.headers,
            auth=jira_client.auth
        )
        
        if response.status_code != 200:
            console.print(f"[bold red]Error fetching issue {issue_key}: {response.status_code}[/bold red]")
            console.print(response.text)
            return
        
        data = response.json()
        issues = data.get("issues", [])
        
        if not issues:
            console.print(f"[bold red]Issue {issue_key} not found.[/bold red]")
            return
        
        issue = issues[0]
    
    with console.status("[bold green]Generating improvement suggestions..."):
        llm_client = LLMClient()
        suggestions = llm_client.suggest_issue_updates(issue)
    
    # Display suggestions
    console.print(Panel(Markdown(suggestions), title=f"Improvement Suggestions for {issue_key}", border_style="purple"))

@app.command()
def chat():
    """Interactive chat session with your JIRA assistant"""
    check_api_keys()
    
    console.print("[bold blue]Welcome to the JIRA Assistant Chat![/bold blue]")
    console.print("Type 'exit' or 'quit' to end the session.")
    console.print("You can ask questions about your JIRA issues or request specific actions.")
    console.print("Example queries:")
    console.print("  - Summarize my current issues")
    console.print("  - What are the highest priority bugs?")
    console.print("  - Help me create a JQL query for open issues assigned to me")
    console.print("  - Generate a weekly status report based on recent issues")
    
    jira_client = JiraClient()
    llm_client = LLMClient()
    
    # Get all issues at the start to have context for the conversation
    with console.status("[bold green]Fetching JIRA issues for context..."):
        issues = jira_client.get_all_issues_paginated()
        if not issues:
            console.print("[bold yellow]Warning: Could not retrieve JIRA issues. Chat functionality may be limited.[/bold yellow]")
    
    # Prepare initial context about issues
    issues_context = []
    for issue in issues[:20]:  # Limit to 20 issues to avoid token limits
        fields = issue.get("fields", {})
        issues_context.append({
            "key": issue.get("key", ""),
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", "") if fields.get("status") else "",
            "priority": fields.get("priority", {}).get("name", "") if fields.get("priority") else ""
        })
    
    system_prompt = f"""
    You are a helpful JIRA assistant with access to the user's JIRA issues.
    Be concise, helpful, and professional in your responses.
    Here is the current context of JIRA issues you can reference:
    {json.dumps(issues_context, indent=2)}
    """
    
    conversation_history = [{"role": "system", "content": system_prompt}]
    
    while True:
        user_input = typer.prompt("\n[bold green]You[/bold green]")
        
        if user_input.lower() in ("exit", "quit", "bye"):
            console.print("[bold blue]Goodbye![/bold blue]")
            break
        
        conversation_history.append({"role": "user", "content": user_input})
        
        with console.status("[bold green]Thinking..."):
            # Use full conversation history for context
            response = llm_client.client.chat.completions.create(
                model=llm_client.default_model,
                messages=conversation_history,
                temperature=0.7,
                max_tokens=2000
            )
            
            assistant_response = response.choices[0].message.content
            conversation_history.append({"role": "assistant", "content": assistant_response})
        
        console.print("\n[bold blue]JIRA Assistant:[/bold blue]")
        console.print(Markdown(assistant_response))

if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        sys.exit(1) 