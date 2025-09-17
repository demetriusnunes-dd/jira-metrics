#!/usr/bin/env python3
"""
JIRA Metrics Extractor

Extracts cycle time metrics from JIRA issues.
Cycle time = time spent in Doing, Blocked, or Review statuses.
"""

import os
import sys
import json
import csv
import argparse
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from requests.auth import HTTPBasicAuth


class JiraMetricsExtractor:
    def __init__(self, base_url: str, username: str, api_token: str):
        """Initialize the JIRA metrics extractor."""
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, api_token)
        self.session = requests.Session()
        self.session.auth = self.auth
        
        # Default cycle time statuses - can be customized
        self.cycle_time_statuses = {'Doing', 'Blocked', 'Review', 'In Progress', 'In Review'}
        
        # Rate limiting configuration
        self.requests_per_minute = 60  # Conservative default
        self.request_interval = 60.0 / self.requests_per_minute  # seconds between requests
        self.last_request_time = 0
        self.max_retries = 5
        self.base_backoff = 1.0  # seconds
    
    def set_cycle_time_statuses(self, statuses: List[str]):
        """Set custom statuses that count toward cycle time."""
        self.cycle_time_statuses = set(statuses)
    
    def set_rate_limit(self, requests_per_minute: int):
        """Set the rate limit for API requests."""
        self.requests_per_minute = requests_per_minute
        self.request_interval = 60.0 / self.requests_per_minute
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_interval:
            sleep_time = self.request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with exponential backoff retry logic."""
        for attempt in range(self.max_retries):
            self._rate_limit()
            
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Handle rate limiting responses
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    jitter = random.uniform(0.1, 0.5)  # Add jitter to avoid thundering herd
                    wait_time = retry_after + jitter
                    
                    print(f"Rate limited (429). Waiting {wait_time:.1f} seconds before retry {attempt + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                    continue
                
                # Handle server errors with exponential backoff
                if response.status_code >= 500:
                    if attempt == self.max_retries - 1:
                        response.raise_for_status()
                    
                    backoff_time = (self.base_backoff * (2 ** attempt)) + random.uniform(0, 1)
                    print(f"Server error {response.status_code}. Retrying in {backoff_time:.1f} seconds (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(backoff_time)
                    continue
                
                # Success or client error (don't retry client errors)
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                
                backoff_time = (self.base_backoff * (2 ** attempt)) + random.uniform(0, 1)
                print(f"Request failed: {e}. Retrying in {backoff_time:.1f} seconds (attempt {attempt + 1}/{self.max_retries})")
                time.sleep(backoff_time)
        
        raise Exception(f"Failed to complete request after {self.max_retries} attempts")
    
    def get_issues(self, jql: str, max_results: int = 100) -> List[Dict]:
        """Get issues from JIRA using JQL query."""
        # Try the new API v3 JQL endpoint first
        try:
            return self._get_issues_v3_jql(jql, max_results)
        except Exception as e:
            print(f"v3 JQL API failed: {e}, trying v3 search API")
            return self._get_issues_v3_search(jql, max_results)
    
    def _get_issues_v3_jql(self, jql: str, max_results: int) -> List[Dict]:
        """Get issues using v3 JQL API."""
        url = f"{self.base_url}/rest/api/3/search/jql"
        
        issues = []
        next_page_token = None
        
        while len(issues) < max_results:
            params = {
                'jql': jql,
                'maxResults': min(max_results - len(issues), 100),
                'expand': 'changelog',
                'fields': 'key,summary,status,created,resolutiondate,assignee,priority,issuetype'
            }
            
            if next_page_token:
                params['nextPageToken'] = next_page_token
            
            response = self._make_request_with_retry('GET', url, params=params)
            
            data = response.json()
            
            # Get detailed issue data for each issue ID
            for issue_summary in data.get('issues', []):
                issue_id = issue_summary['id']
                issue_detail = self._get_issue_detail(issue_id)
                if issue_detail:
                    issues.append(issue_detail)
            
            if data.get('isLast', True) or not data.get('nextPageToken'):
                break
                
            next_page_token = data.get('nextPageToken')
        
        return issues
    
    def _get_issues_v3_search(self, jql: str, max_results: int) -> List[Dict]:
        """Get issues using v3 search API (fallback)."""
        url = f"{self.base_url}/rest/api/3/search"
        
        issues = []
        start_at = 0
        
        while len(issues) < max_results:
            params = {
                'jql': jql,
                'maxResults': min(max_results - len(issues), 100),
                'startAt': start_at,
                'expand': 'changelog',
                'fields': 'key,summary,status,created,resolutiondate,assignee,priority,issuetype'
            }
            
            response = self._make_request_with_retry('GET', url, params=params)
            
            data = response.json()
            issues.extend(data.get('issues', []))
            
            if len(data.get('issues', [])) == 0 or data.get('total', 0) <= len(issues):
                break
                
            start_at += len(data.get('issues', []))
        
        return issues
    
    def _get_issue_detail(self, issue_id: str) -> Optional[Dict]:
        """Get detailed issue information including changelog."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_id}"
        params = {
            'expand': 'changelog',
            'fields': 'key,summary,status,created,resolutiondate,assignee,priority,issuetype'
        }
        
        try:
            response = self._make_request_with_retry('GET', url, params=params)
            return response.json()
        except Exception as e:
            print(f"Failed to get details for issue {issue_id}: {e}")
            return None
    
    def parse_datetime(self, date_str: str) -> datetime:
        """Parse JIRA datetime string."""
        # Handle different JIRA datetime formats
        for fmt in ['%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Fallback: remove timezone info and parse
        if '+' in date_str:
            date_str = date_str.split('+')[0]
        elif 'Z' in date_str:
            date_str = date_str.replace('Z', '')
        
        return datetime.fromisoformat(date_str)
    
    def calculate_cycle_time(self, issue: Dict) -> Tuple[float, List[Dict]]:
        """
        Calculate cycle time for an issue.
        
        Returns:
            Tuple of (total_cycle_time_hours, status_periods)
        """
        changelog = issue.get('changelog', {})
        histories = changelog.get('histories', [])
        
        if not histories:
            return 0.0, []
        
        # Track status changes
        status_changes = []
        
        # Add initial status (created)
        created_date = self.parse_datetime(issue['fields']['created'])
        current_status = None  # We don't know the initial status from creation
        
        # Process changelog to find status changes
        for history in sorted(histories, key=lambda x: x['created']):
            change_date = self.parse_datetime(history['created'])
            
            for item in history['items']:
                if item['field'] == 'status':
                    from_status = item.get('fromString')
                    to_status = item.get('toString')
                    
                    status_changes.append({
                        'date': change_date,
                        'from_status': from_status,
                        'to_status': to_status
                    })
        
        # Calculate time in cycle time statuses
        total_cycle_time = 0.0
        status_periods = []
        current_cycle_start = None
        
        # Start from creation if first status is a cycle time status
        if status_changes and status_changes[0]['to_status'] in self.cycle_time_statuses:
            current_cycle_start = created_date
        
        for i, change in enumerate(status_changes):
            from_status = change['from_status']
            to_status = change['to_status']
            change_date = change['date']
            
            # If leaving a cycle time status
            if from_status in self.cycle_time_statuses and current_cycle_start:
                duration = (change_date - current_cycle_start).total_seconds() / 3600
                total_cycle_time += duration
                
                status_periods.append({
                    'status': from_status,
                    'start': current_cycle_start,
                    'end': change_date,
                    'duration_hours': duration
                })
                
                current_cycle_start = None
            
            # If entering a cycle time status
            if to_status in self.cycle_time_statuses:
                current_cycle_start = change_date
        
        # Handle case where issue is still in a cycle time status
        current_status = issue['fields']['status']['name']
        if current_status in self.cycle_time_statuses and current_cycle_start:
            end_date = datetime.now(current_cycle_start.tzinfo)
            if issue['fields'].get('resolutiondate'):
                end_date = self.parse_datetime(issue['fields']['resolutiondate'])
            
            duration = (end_date - current_cycle_start).total_seconds() / 3600
            total_cycle_time += duration
            
            status_periods.append({
                'status': current_status,
                'start': current_cycle_start,
                'end': end_date,
                'duration_hours': duration
            })
        
        return total_cycle_time, status_periods
    
    def extract_metrics(self, jql: str, max_results: int = 100) -> List[Dict]:
        """Extract cycle time metrics for issues matching the JQL query."""
        print(f"Fetching issues with JQL: {jql}")
        issues = self.get_issues(jql, max_results)
        print(f"Found {len(issues)} issues")
        
        metrics = []
        
        for issue in issues:
            key = issue['key']
            fields = issue['fields']
            
            cycle_time, status_periods = self.calculate_cycle_time(issue)
            
            metrics.append({
                'key': key,
                'summary': fields['summary'],
                'status': fields['status']['name'],
                'created': fields['created'],
                'resolved': fields.get('resolutiondate'),
                'assignee': fields.get('assignee', {}).get('displayName') if fields.get('assignee') else None,
                'priority': fields.get('priority', {}).get('name') if fields.get('priority') else None,
                'issue_type': fields.get('issuetype', {}).get('name') if fields.get('issuetype') else None,
                'cycle_time_hours': cycle_time,
                'cycle_time_days': cycle_time / 24 if cycle_time > 0 else 0,
                'status_periods': status_periods
            })
        
        return metrics
    
    def export_to_csv(self, metrics: List[Dict], filename: str):
        """Export metrics to CSV file."""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'key', 'summary', 'status', 'created', 'resolved', 'assignee',
                'priority', 'issue_type', 'cycle_time_hours', 'cycle_time_days'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for metric in metrics:
                # Remove status_periods for CSV export (too complex)
                row = {k: v for k, v in metric.items() if k != 'status_periods'}
                writer.writerow(row)
        
        print(f"Metrics exported to {filename}")


def main():
    parser = argparse.ArgumentParser(description='Extract JIRA cycle time metrics')
    parser.add_argument('--url', required=True, help='JIRA base URL')
    parser.add_argument('--username', required=True, help='JIRA username')
    parser.add_argument('--token', help='JIRA API token (or set JIRA_API_TOKEN env var)')
    parser.add_argument('--jql', default='project = YOUR_PROJECT AND status changed DURING (-30d, now())',
                       help='JQL query to filter issues')
    parser.add_argument('--max-results', type=int, default=10000, help='Maximum number of issues to process')
    parser.add_argument('--statuses', nargs='+', 
                       default=['Doing', 'Blocked', 'Review', 'In Progress', 'In Review'],
                       help='Status names that count toward cycle time')
    parser.add_argument('--output', default='jira_metrics.csv', help='Output CSV filename')
    parser.add_argument('--json', action='store_true', help='Also output detailed JSON')
    parser.add_argument('--rate-limit', type=int, default=60, 
                       help='Maximum requests per minute (default: 60)')
    
    args = parser.parse_args()
    
    # Get API token from environment if not provided
    api_token = args.token or os.getenv('JIRA_API_TOKEN')
    if not api_token:
        print("Error: JIRA API token required. Use --token or set JIRA_API_TOKEN environment variable.")
        sys.exit(1)
    
    try:
        extractor = JiraMetricsExtractor(args.url, args.username, api_token)
        extractor.set_cycle_time_statuses(args.statuses)
        extractor.set_rate_limit(args.rate_limit)
        
        print(f"Rate limit set to {args.rate_limit} requests per minute")
        
        metrics = extractor.extract_metrics(args.jql, args.max_results)
        
        # Export to CSV
        extractor.export_to_csv(metrics, args.output)
        
        # Export to JSON if requested
        if args.json:
            json_filename = args.output.replace('.csv', '.json')
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, default=str)
            print(f"Detailed metrics exported to {json_filename}")
        
        # Print summary
        if metrics:
            avg_cycle_time = sum(m['cycle_time_hours'] for m in metrics) / len(metrics)
            print(f"\nSummary:")
            print(f"Total issues: {len(metrics)}")
            print(f"Average cycle time: {avg_cycle_time:.1f} hours ({avg_cycle_time/24:.1f} days)")
            print(f"Cycle time statuses: {', '.join(args.statuses)}")
    
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to JIRA: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()