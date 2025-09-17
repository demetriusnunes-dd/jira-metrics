"""
Configuration example for JIRA metrics extraction.
Copy this file to config.py and update with your JIRA details.
"""

# JIRA Configuration
JIRA_URL = "https://your-company.atlassian.net"
JIRA_USERNAME = "your-email@company.com"
# Use an API token, not your password: https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_API_TOKEN = "your-api-token-here"

# JQL Queries for different teams/projects
JQL_QUERIES = {
    "my_team": "project = MYPROJ AND status changed DURING (-30d, now())",
    "sprint_issues": "project = MYPROJ AND sprint in openSprints()",
    "resolved_last_month": "project = MYPROJ AND resolved >= -30d"
}

# Status names that count toward cycle time
# Customize these based on your JIRA workflow
CYCLE_TIME_STATUSES = [
    "Doing",
    "Blocked", 
    "Review",
    "In Progress",
    "In Review",
    "Code Review",
    "Testing"
]

# Output settings
DEFAULT_OUTPUT_FILE = "team_metrics.csv"
MAX_RESULTS = 200