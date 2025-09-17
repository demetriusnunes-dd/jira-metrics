# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JIRA metrics extraction tool that calculates cycle time for development tasks. Cycle time is defined as the total time a task spends in "Doing", "Blocked", or "Review" statuses (customizable).

## Development Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pandas numpy matplotlib seaborn  # For statistical analysis
   ```

2. Set up JIRA credentials in `.env` file:
   ```bash
   # Copy the example and edit
   cp .env.example .env
   # Edit .env with your credentials
   ```
   
   **⚠️ Security**: Never commit the `.env` file to version control!

## Common Commands

### Quick Usage (Recommended)
```bash
# Recent resolved issues (last 30 days) with analysis
./metrics --preset recent --analyze

# Current sprint issues
./metrics --preset sprint --output sprint_metrics.csv

# All 2025 resolved issues
./metrics --preset 2025 --analyze

# Stories only (excludes epics)
./metrics --preset stories

# Custom JQL with analysis
./metrics --jql "project = TAS AND assignee = 'your.name@company.com'" --analyze
```

### Advanced Usage
```bash
# Full control version
python3 jira_metrics_easy.py --preset recent --max-results 500 --json --analyze

# Original version (requires explicit credentials)
python3 jira_metrics.py --url https://company.atlassian.net --username user@company.com --jql "your query"

# Statistical analysis only (on existing CSV)
python3 analyze_cycle_times.py your_metrics.csv --method all
```

### Common JQL Patterns
- Recent changes: `status changed DURING (-30d, now())`
- Current sprint: `sprint in openSprints()`
- Specific project: `project = PROJKEY`
- Resolved recently: `resolved >= -7d`

## Architecture

### Core Components

- **JiraMetricsExtractor**: Main class that handles JIRA API communication and metric calculation
- **Cycle Time Calculation**: Analyzes issue changelog to determine time spent in specified statuses
- **Export Functions**: Outputs metrics to CSV and optionally JSON formats

### Key Features

- Configurable status mapping for cycle time calculation
- Handles timezone parsing for JIRA datetime fields
- Processes issue changelog history to track status transitions
- Supports bulk processing with pagination
- Exports detailed breakdown of time spent in each status