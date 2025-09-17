# JIRA Cycle Time Metrics

Extract cycle time metrics from your JIRA installation to analyze development team performance.

## What is Cycle Time?

Cycle time measures how long tasks spend in active development statuses. By default, this includes time spent in:
- Doing
- Blocked  
- Review
- In Progress
- In Review

This metric helps teams understand their delivery efficiency and identify bottlenecks.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get your JIRA API token:**
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Create a new API token
   - Save it securely

3. **Run the script:**
   ```bash
   export JIRA_API_TOKEN="your-token-here"
   python jira_metrics.py --url https://your-company.atlassian.net --username your-email@company.com
   ```

## Example Output

The script generates a CSV file with these columns:
- `key`: Issue key (e.g., PROJ-123)
- `summary`: Issue title
- `cycle_time_hours`: Total hours in cycle time statuses
- `cycle_time_days`: Total days in cycle time statuses
- `status`: Current issue status
- `created`: When the issue was created
- `resolved`: When the issue was resolved (if completed)

## Advanced Usage

### Custom Status Names
If your JIRA uses different status names:
```bash
python jira_metrics.py --url https://company.atlassian.net --username user@company.com --statuses "Development" "Code Review" "QA Testing"
```

### Filter by Project or Sprint
```bash
# Specific project
python jira_metrics.py --jql "project = MYPROJ AND resolved >= -30d" --url https://company.atlassian.net --username user@company.com

# Current sprint
python jira_metrics.py --jql "sprint in openSprints()" --url https://company.atlassian.net --username user@company.com
```

### Export Detailed Data
```bash
python jira_metrics.py --json --url https://company.atlassian.net --username user@company.com
```

This creates both a CSV summary and a detailed JSON file with status transition history.

## Security Notes

- Never commit your API token to version control
- Use environment variables or a local config file for credentials
- API tokens are safer than passwords and can be easily revoked

## Troubleshooting

**Authentication Error**: Verify your JIRA URL, username, and API token
**No Issues Found**: Check your JQL query and permissions
**Missing Status Transitions**: The script requires changelog history (may not be available for very old issues)