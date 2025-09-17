#!/usr/bin/env python3
"""
Statistical Analysis of JIRA Cycle Times

Analyzes cycle time data with outlier removal using statistical methods.
"""

import pandas as pd
import numpy as np
import argparse
import sys
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


class CycleTimeAnalyzer:
    def __init__(self, csv_file: str):
        """Initialize the analyzer with CSV data."""
        try:
            self.df = pd.read_csv(csv_file)
            print(f"Loaded {len(self.df)} issues from {csv_file}")
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            sys.exit(1)
    
    def remove_outliers_iqr(self, column: str = 'cycle_time_days') -> pd.DataFrame:
        """Remove outliers using Interquartile Range (IQR) method."""
        Q1 = self.df[column].quantile(0.25)
        Q3 = self.df[column].quantile(0.75)
        IQR = Q3 - Q1
        
        # Define outlier bounds (1.5 * IQR is standard)
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Filter out outliers
        outliers = self.df[(self.df[column] < lower_bound) | (self.df[column] > upper_bound)]
        clean_data = self.df[(self.df[column] >= lower_bound) & (self.df[column] <= upper_bound)]
        
        print(f"\nIQR Method Results:")
        print(f"Q1 (25th percentile): {Q1:.2f} days")
        print(f"Q3 (75th percentile): {Q3:.2f} days")
        print(f"IQR: {IQR:.2f} days")
        print(f"Lower bound: {lower_bound:.2f} days")
        print(f"Upper bound: {upper_bound:.2f} days")
        print(f"Outliers removed: {len(outliers)} ({len(outliers)/len(self.df)*100:.1f}%)")
        
        return clean_data, outliers
    
    def remove_outliers_zscore(self, column: str = 'cycle_time_days', threshold: float = 3.0) -> pd.DataFrame:
        """Remove outliers using Z-score method."""
        mean = self.df[column].mean()
        std = self.df[column].std()
        
        # Calculate Z-scores
        z_scores = np.abs((self.df[column] - mean) / std)
        
        # Filter out outliers
        outliers = self.df[z_scores > threshold]
        clean_data = self.df[z_scores <= threshold]
        
        print(f"\nZ-Score Method Results (threshold={threshold}):")
        print(f"Mean: {mean:.2f} days")
        print(f"Standard deviation: {std:.2f} days")
        print(f"Outliers removed: {len(outliers)} ({len(outliers)/len(self.df)*100:.1f}%)")
        
        return clean_data, outliers
    
    def remove_outliers_percentile(self, column: str = 'cycle_time_days', lower: float = 5, upper: float = 95) -> pd.DataFrame:
        """Remove outliers using percentile method."""
        lower_bound = self.df[column].quantile(lower / 100)
        upper_bound = self.df[column].quantile(upper / 100)
        
        # Filter out outliers
        outliers = self.df[(self.df[column] < lower_bound) | (self.df[column] > upper_bound)]
        clean_data = self.df[(self.df[column] >= lower_bound) & (self.df[column] <= upper_bound)]
        
        print(f"\nPercentile Method Results ({lower}th-{upper}th percentile):")
        print(f"Lower bound ({lower}th percentile): {lower_bound:.2f} days")
        print(f"Upper bound ({upper}th percentile): {upper_bound:.2f} days")
        print(f"Outliers removed: {len(outliers)} ({len(outliers)/len(self.df)*100:.1f}%)")
        
        return clean_data, outliers
    
    def calculate_statistics(self, data: pd.DataFrame, label: str = "") -> Dict:
        """Calculate comprehensive statistics for the data."""
        cycle_times = data['cycle_time_days']
        
        stats = {
            'count': len(data),
            'mean': cycle_times.mean(),
            'median': cycle_times.median(),
            'mode': cycle_times.mode().iloc[0] if len(cycle_times.mode()) > 0 else 'N/A',
            'std': cycle_times.std(),
            'min': cycle_times.min(),
            'max': cycle_times.max(),
            'q25': cycle_times.quantile(0.25),
            'q75': cycle_times.quantile(0.75),
            'iqr': cycle_times.quantile(0.75) - cycle_times.quantile(0.25),
            'skewness': cycle_times.skew(),
            'kurtosis': cycle_times.kurtosis()
        }
        
        print(f"\n{label} Statistics:")
        print(f"Count: {stats['count']}")
        print(f"Mean: {stats['mean']:.2f} days")
        print(f"Median: {stats['median']:.2f} days")
        print(f"Standard Deviation: {stats['std']:.2f} days")
        print(f"Min: {stats['min']:.2f} days")
        print(f"Max: {stats['max']:.2f} days")
        print(f"25th Percentile: {stats['q25']:.2f} days")
        print(f"75th Percentile: {stats['q75']:.2f} days")
        print(f"IQR: {stats['iqr']:.2f} days")
        print(f"Skewness: {stats['skewness']:.2f} (0=normal, >1=right-skewed)")
        print(f"Kurtosis: {stats['kurtosis']:.2f} (0=normal distribution)")
        
        return stats
    
    def analyze_by_issue_type(self, data: pd.DataFrame) -> None:
        """Analyze cycle times by issue type."""
        print(f"\n--- Analysis by Issue Type ---")
        
        type_stats = data.groupby('issue_type')['cycle_time_days'].agg([
            'count', 'mean', 'median', 'std', 'min', 'max'
        ]).round(2)
        
        print(type_stats)
        
        # Show distribution
        print(f"\nIssue Type Distribution:")
        for issue_type, count in data['issue_type'].value_counts().items():
            percentage = count / len(data) * 100
            print(f"{issue_type}: {count} issues ({percentage:.1f}%)")
    
    def analyze_by_assignee(self, data: pd.DataFrame, top_n: int = 10) -> None:
        """Analyze cycle times by assignee."""
        print(f"\n--- Analysis by Assignee (Top {top_n}) ---")
        
        assignee_stats = data.groupby('assignee')['cycle_time_days'].agg([
            'count', 'mean', 'median', 'std'
        ]).round(2)
        
        # Sort by count and show top N
        top_assignees = assignee_stats.sort_values('count', ascending=False).head(top_n)
        print(top_assignees)
    
    def identify_extreme_outliers(self, outliers: pd.DataFrame) -> None:
        """Analyze the removed outliers to understand what they represent."""
        if len(outliers) == 0:
            print("\nNo outliers to analyze.")
            return
        
        print(f"\n--- Analysis of {len(outliers)} Outliers ---")
        
        # Sort by cycle time
        extreme_outliers = outliers.nlargest(10, 'cycle_time_days')[
            ['key', 'summary', 'issue_type', 'cycle_time_days', 'assignee']
        ]
        
        print("Top 10 longest cycle times (outliers):")
        for _, row in extreme_outliers.iterrows():
            print(f"{row['key']}: {row['cycle_time_days']:.1f} days - {row['issue_type']} - {row['summary'][:60]}...")
        
        # Analyze outlier patterns
        print(f"\nOutlier Issue Types:")
        for issue_type, count in outliers['issue_type'].value_counts().items():
            percentage = count / len(outliers) * 100
            mean_days = outliers[outliers['issue_type'] == issue_type]['cycle_time_days'].mean()
            print(f"{issue_type}: {count} issues ({percentage:.1f}%), avg: {mean_days:.1f} days")
    
    def generate_summary_report(self, original_stats: Dict, clean_stats: Dict, method: str) -> None:
        """Generate a summary report comparing original vs cleaned data."""
        print(f"\n{'='*60}")
        print(f"SUMMARY REPORT - {method}")
        print(f"{'='*60}")
        
        print(f"Original Data:")
        print(f"  Issues: {original_stats['count']}")
        print(f"  Mean cycle time: {original_stats['mean']:.1f} days")
        print(f"  Median cycle time: {original_stats['median']:.1f} days")
        print(f"  Standard deviation: {original_stats['std']:.1f} days")
        
        print(f"\nCleaned Data (outliers removed):")
        print(f"  Issues: {clean_stats['count']}")
        print(f"  Mean cycle time: {clean_stats['mean']:.1f} days")
        print(f"  Median cycle time: {clean_stats['median']:.1f} days")
        print(f"  Standard deviation: {clean_stats['std']:.1f} days")
        
        print(f"\nImprovement:")
        mean_improvement = ((original_stats['mean'] - clean_stats['mean']) / original_stats['mean']) * 100
        std_improvement = ((original_stats['std'] - clean_stats['std']) / original_stats['std']) * 100
        
        print(f"  Mean reduced by: {mean_improvement:.1f}%")
        print(f"  Standard deviation reduced by: {std_improvement:.1f}%")
        print(f"  Data points retained: {clean_stats['count']/original_stats['count']*100:.1f}%")
        
        print(f"\nRecommended Team Cycle Time: {clean_stats['median']:.1f} days (median)")
        print(f"Typical Range: {clean_stats['q25']:.1f} - {clean_stats['q75']:.1f} days (IQR)")


def main():
    parser = argparse.ArgumentParser(description='Analyze JIRA cycle times with outlier removal')
    parser.add_argument('csv_file', help='Path to the CSV file with cycle time data')
    parser.add_argument('--method', choices=['iqr', 'zscore', 'percentile', 'all'], 
                       default='iqr', help='Outlier removal method')
    parser.add_argument('--zscore-threshold', type=float, default=3.0, 
                       help='Z-score threshold for outlier removal')
    parser.add_argument('--percentile-lower', type=float, default=5,
                       help='Lower percentile for outlier removal')
    parser.add_argument('--percentile-upper', type=float, default=95,
                       help='Upper percentile for outlier removal')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = CycleTimeAnalyzer(args.csv_file)
    
    # Calculate original statistics
    original_stats = analyzer.calculate_statistics(analyzer.df, "Original Data")
    
    if args.method == 'all':
        methods = ['iqr', 'zscore', 'percentile']
    else:
        methods = [args.method]
    
    for method in methods:
        print(f"\n{'='*80}")
        print(f"ANALYZING WITH {method.upper()} METHOD")
        print(f"{'='*80}")
        
        if method == 'iqr':
            clean_data, outliers = analyzer.remove_outliers_iqr()
        elif method == 'zscore':
            clean_data, outliers = analyzer.remove_outliers_zscore(threshold=args.zscore_threshold)
        elif method == 'percentile':
            clean_data, outliers = analyzer.remove_outliers_percentile(
                lower=args.percentile_lower, upper=args.percentile_upper
            )
        
        # Calculate cleaned statistics
        clean_stats = analyzer.calculate_statistics(clean_data, f"Cleaned Data ({method.upper()})")
        
        # Additional analysis
        analyzer.analyze_by_issue_type(clean_data)
        analyzer.analyze_by_assignee(clean_data)
        analyzer.identify_extreme_outliers(outliers)
        
        # Generate summary
        analyzer.generate_summary_report(original_stats, clean_stats, method.upper())


if __name__ == '__main__':
    main()