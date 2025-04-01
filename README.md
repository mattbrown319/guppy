# JIRA LLM Integration

This project provides a simple interface to interact with JIRA using Python and potentially integrate with LLMs.

## Setup

1. Clone this repository
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Update the `.env` file with your JIRA credentials:
   ```
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-jira-api-token
   JIRA_DOMAIN=your-domain.atlassian.net
   ```

## Usage

### Fetching All Issues

To fetch all issues from your JIRA board, run:

```
python jira_client.py
```

This will display a list of the 10 most recent issues with their keys, summaries, and statuses.

## Extending the Project

This project provides a foundation for building LLM-powered JIRA interactions. You can extend it by:

1. Adding more JIRA API endpoints
2. Integrating with an LLM for generating summaries or insights
3. Creating automated workflows for JIRA tasks
4. Building a chat interface for interacting with your JIRA data

## Security Notes

- Never commit your `.env` file with real credentials to version control
- Consider adding `.env` to your `.gitignore` file
- Rotate your API tokens regularly for security 