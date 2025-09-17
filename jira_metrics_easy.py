#!/usr/bin/env python3
"""
JIRA Metrics Extractor - Easy Version

Automatically loads credentials from .env file for simplified usage.
"""

import os
import sys
import argparse
from pathlib import Path

# Import the original extractor
from jira_metrics import JiraMetricsExtractor


def load_env_file(env_path: str = '.env') -> dict:
    """Load environment variables from .env file."""
    env_vars = {}
    
    if not os.path.exists(env_path):
        return env_vars
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def main():
    # Load environment variables
    env_vars = load_env_file()
    
    parser = argparse.ArgumentParser(description='Extract JIRA cycle time metrics (easy mode)')
    
    # Credentials (with defaults from .env)
    parser.add_argument('--url', default=env_vars.get('JIRA_URL'), 
                       help=f'JIRA base URL (default: {env_vars.get("JIRA_URL", "from .env file")})')
    parser.add_argument('--username', default=env_vars.get('JIRA_USERNAME'),
                       help=f'JIRA username (default: {env_vars.get("JIRA_USERNAME", "from .env file")})')
    parser.add_argument('--token', default=env_vars.get('JIRA_API_TOKEN'),
                       help='JIRA API token (default: from .env file)')
    
    # Common JQL presets
    parser.add_argument('--preset', choices=['recent', 'sprint', '2025', 'stories'], 
                       help='Use predefined JQL query')
    parser.add_argument('--jql', help='Custom JQL query (overrides preset)')
    
    # Settings with defaults from .env
    parser.add_argument('--max-results', type=int, 
                       default=int(env_vars.get('DEFAULT_MAX_RESULTS', 1000)),
                       help='Maximum number of issues to process')
    parser.add_argument('--rate-limit', type=int,
                       default=int(env_vars.get('DEFAULT_RATE_LIMIT', 60)),
                       help='Maximum requests per minute')
    
    # Output options
    parser.add_argument('--output', default='metrics.csv', help='Output CSV filename')
    parser.add_argument('--json', action='store_true', help='Also output detailed JSON')
    parser.add_argument('--analyze', action='store_true', 
                       help='Run statistical analysis after extraction')
    
    # Status customization
    parser.add_argument('--statuses', nargs='+', 
                       default=['Doing', 'Blocked', 'Review', 'In Progress', 'In Review'],
                       help='Status names that count toward cycle time')
    
    args = parser.parse_args()
    
    # Check required credentials
    if not all([args.url, args.username, args.token]):
        missing = []
        if not args.url: missing.append('JIRA_URL')
        if not args.username: missing.append('JIRA_USERNAME') 
        if not args.token: missing.append('JIRA_API_TOKEN')
        
        print(f"Error: Missing credentials. Please set in .env file: {', '.join(missing)}")
        print("\nCreate a .env file with:")
        print("JIRA_URL=https://your-company.atlassian.net")
        print("JIRA_USERNAME=your-email@company.com") 
        print("JIRA_API_TOKEN=your-token-here")
        sys.exit(1)
    
    # Set JQL based on preset or custom
    if args.jql:
        jql = args.jql
    elif args.preset:
        presets = {
            'recent': env_vars.get('JQL_RECENT_RESOLVED', 'project = TAS AND resolved >= -30d'),
            'sprint': env_vars.get('JQL_CURRENT_SPRINT', 'project = TAS AND sprint in openSprints()'),
            '2025': env_vars.get('JQL_2025_RESOLVED', 'project = TAS AND resolved >= "2025-01-01"'),
            'stories': env_vars.get('JQL_STORIES_ONLY', 'project = TAS AND issuetype = Story AND resolved >= -30d')
        }
        jql = presets[args.preset]
    else:
        # Default to recent resolved issues
        jql = env_vars.get('JQL_RECENT_RESOLVED', 'project = TAS AND resolved >= -30d')
    
    try:
        print(f"🔐 Connecting to: {args.url}")
        print(f"👤 User: {args.username}")
        print(f"🔍 Query: {jql}")
        print(f"⚡ Rate limit: {args.rate_limit} requests/minute")
        print(f"📊 Max results: {args.max_results}")
        print()
        
        # Initialize extractor
        extractor = JiraMetricsExtractor(args.url, args.username, args.token)
        extractor.set_cycle_time_statuses(args.statuses)
        extractor.set_rate_limit(args.rate_limit)
        
        # Extract metrics
        metrics = extractor.extract_metrics(jql, args.max_results)
        
        if not metrics:
            print("❌ No issues found matching the query.")
            return
        
        # Export results
        extractor.export_to_csv(metrics, args.output)
        
        if args.json:
            json_filename = args.output.replace('.csv', '.json')
            import json
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, default=str)
            print(f"📄 Detailed metrics: {json_filename}")
        
        print(f"✅ Metrics exported: {args.output}")
        
        # Run analysis if requested
        if args.analyze:
            print(f"\n🔬 Running statistical analysis...")
            try:
                os.system(f"python3 analyze_cycle_times.py {args.output} --method iqr")
            except Exception as e:
                print(f"Analysis failed: {e}")
        
        # Print summary
        cycle_times = [m['cycle_time_days'] for m in metrics]
        avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else 0
        
        print(f"\n📈 Quick Summary:")
        print(f"   Issues analyzed: {len(metrics)}")
        print(f"   Average cycle time: {avg_cycle_time:.1f} days")
        print(f"   Cycle time statuses: {', '.join(args.statuses)}")
        
        if avg_cycle_time > 15:
            print(f"   💡 Tip: High average suggests outliers. Use --analyze flag!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()