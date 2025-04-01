import os
import json
import logging
import sys
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMClient:
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
            logger.info("Initializing LLM client")
        
        # Load API key from environment
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        if verbose:
            logger.info("OpenAI API key loaded successfully")
            logger.info("LLM client initialized successfully")
        
        try:
            # Create OpenAI client
            if self.verbose:
                logging.info("Creating OpenAI client...")
            
            self.client = OpenAI(api_key=self.api_key)
            
            # Set default model
            self.default_model = "gpt-4"
            if self.verbose:
                logging.info(f"Default model set to: {self.default_model}")
            
        except Exception as e:
            logger.error(f"Error initializing LLM client: {str(e)}")
            raise
    
    def generate_response(self, user_prompt: str, system_prompt: str = None, model: str = None) -> str:
        """Generate a response using the OpenAI API"""
        try:
            if self.verbose:
                logging.info("\nGenerating response from OpenAI")
                logging.info(f"Using model: {model or self.default_model}")
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            
            if self.verbose:
                logging.info("Successfully received response from OpenAI")
            
            return response.choices[0].message.content
            
        except Exception as e:
            if self.verbose:
                logging.error(f"Error generating response: {str(e)}")
            raise
    
    def summarize_issues(self, issues: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of JIRA issues.
        
        Args:
            issues (List[Dict]): List of JIRA issues
            
        Returns:
            str: Summary of the issues
        """
        if not issues:
            return "No issues to summarize."
        
        # Prepare issues data for the prompt
        issues_data = []
        for issue in issues[:20]:  # Limit to 20 issues to avoid token limits
            fields = issue.get("fields", {})
            issues_data.append({
                "key": issue.get("key", ""),
                "summary": fields.get("summary", ""),
                "status": fields.get("status", {}).get("name", ""),
                "priority": fields.get("priority", {}).get("name", "") if fields.get("priority") else "",
                "assignee": fields.get("assignee", {}).get("displayName", "") if fields.get("assignee") else "Unassigned"
            })
        
        # Create prompt
        system_prompt = """
        You are an expert JIRA analyst. Analyze the provided JIRA issues and create a concise summary.
        Focus on identifying patterns, highlighting important issues, noting priorities,
        and providing actionable insights. Be professional and factual in your analysis.
        """
        
        user_prompt = f"""
        Please analyze the following JIRA issues and provide a summary:
        
        {json.dumps(issues_data, indent=2)}
        
        In your analysis, please include:
        1. A high-level overview of the issues
        2. Key patterns or trends
        3. Notable priorities or blockers
        4. Distribution of issue status
        5. Any recommendations based on this data
        """
        
        return self.generate_response(user_prompt, system_prompt)
    
    def analyze_issue(self, issue: Dict[str, Any]) -> str:
        """
        Perform an in-depth analysis of a single JIRA issue.
        
        Args:
            issue (Dict): JIRA issue data
            
        Returns:
            str: Analysis of the issue
        """
        if not issue:
            return "No issue data provided for analysis."
        
        fields = issue.get("fields", {})
        
        # Extract relevant information
        issue_data = {
            "key": issue.get("key", ""),
            "summary": fields.get("summary", ""),
            "description": fields.get("description", ""),
            "status": fields.get("status", {}).get("name", ""),
            "priority": fields.get("priority", {}).get("name", "") if fields.get("priority") else "",
            "assignee": fields.get("assignee", {}).get("displayName", "") if fields.get("assignee") else "Unassigned",
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "comments": []
        }
        
        # Extract comments if available
        comments = fields.get("comment", {}).get("comments", [])
        for comment in comments:
            issue_data["comments"].append({
                "author": comment.get("author", {}).get("displayName", ""),
                "created": comment.get("created", ""),
                "body": comment.get("body", "")
            })
        
        # Create prompt
        system_prompt = """
        You are an expert JIRA analyst and project manager. Analyze the provided JIRA issue in detail.
        Identify key information, dependencies, risks, and suggest next steps or improvements.
        Be professional, thorough, and actionable in your analysis.
        """
        
        user_prompt = f"""
        Please analyze the following JIRA issue in detail:
        
        {json.dumps(issue_data, indent=2)}
        
        In your analysis, please include:
        1. Summary of the issue and its importance
        2. Assessment of completeness (is enough information provided?)
        3. Potential risks or blockers
        4. Suggested next steps
        5. If there are comments, summarize the key points of discussion
        """
        
        return self.generate_response(user_prompt, system_prompt)
    
    def generate_jql_query(self, natural_language_query: str) -> str:
        """
        Generate a JQL query from natural language.
        
        Args:
            natural_language_query (str): Natural language query about JIRA issues
            
        Returns:
            str: JQL query
        """
        system_prompt = """
        You are an expert in JIRA Query Language (JQL). Your task is to translate natural language queries 
        into valid JQL syntax. Only return the JQL query without additional explanation or markdown formatting.
        Focus on accuracy and ensure the query follows JQL syntax rules. The JQL should be a single line.
        """
        
        user_prompt = f"""
        Please convert the following natural language query into a valid JQL query:
        
        "{natural_language_query}"
        
        Return only the JQL query, no explanations or other text.
        """
        
        return self.generate_response(user_prompt, system_prompt)
    
    def suggest_issue_updates(self, issue: Dict[str, Any]) -> str:
        """
        Suggest updates or improvements for a JIRA issue.
        
        Args:
            issue (Dict): JIRA issue data
            
        Returns:
            str: Suggested updates
        """
        if not issue:
            return "No issue data provided for suggesting updates."
        
        fields = issue.get("fields", {})
        
        # Extract relevant information
        issue_data = {
            "key": issue.get("key", ""),
            "summary": fields.get("summary", ""),
            "description": fields.get("description", ""),
            "status": fields.get("status", {}).get("name", ""),
            "priority": fields.get("priority", {}).get("name", "") if fields.get("priority") else ""
        }
        
        # Create prompt
        system_prompt = """
        You are an expert JIRA consultant. Your task is to review JIRA issues and suggest improvements
        to make them more complete, clear, and actionable. Focus on practical, specific suggestions
        that will help the team better understand and address the issue.
        """
        
        user_prompt = f"""
        Please review the following JIRA issue and suggest improvements:
        
        {json.dumps(issue_data, indent=2)}
        
        Consider:
        1. Is the summary clear and descriptive?
        2. Is the description complete and detailed?
        3. Is the priority appropriate?
        4. What additional information might be helpful?
        5. Any other improvements to make the issue more actionable?
        
        Please provide specific suggestions formatted as bullet points.
        """
        
        return self.generate_response(user_prompt, system_prompt) 