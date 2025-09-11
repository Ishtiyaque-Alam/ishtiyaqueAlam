#!/usr/bin/env python3
"""
Report Generator - Standalone script for generating LLM-powered reports
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import argparse
from dotenv import load_dotenv

load_dotenv()

print(os.getenv('GEMINI_API_KEY'))

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzers.local_analyzer import Issue
from analyzers.global_analyzer import DuplicateFunction


class ReportGenerator:
    def __init__(self, issues_file: str, output_file: str = "Report.md"):
        self.issues_file = issues_file
        self.output_file = output_file
        self.api_key = os.getenv('GEMINI_API_KEY')
    
    def load_issues(self) -> List[Dict[str, Any]]:
        """Load and filter issues from JSON file"""
        with open(self.issues_file, 'r', encoding='utf-8') as f:
            all_issues = json.load(f)
        
        # Filter only High and Medium severity issues
        filtered_issues = [
            issue for issue in all_issues 
            if issue.get('severity', '').lower() in ['high', 'medium']
        ]
        
        print(f"Loaded {len(all_issues)} total issues")
        print(f"Filtered to {len(filtered_issues)} High/Medium issues")
        
        return filtered_issues
    
    def extract_lines_from_file(self,relative_path: str, start_line: int, end_line: int) -> str:
        """
        Extracts lines from start_line to end_line (inclusive) from a file at the given relative path.
        Returns the extracted lines as a single string.
        """
        abs_path = os.path.abspath(relative_path)
        extracted = []
        with open(abs_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, start=1):
                if start_line <= i <= end_line:
                    extracted.append(line)
                if i > end_line:
                    break
        return ''.join(extracted)

    def generate_report(self):
        """Generate the complete report"""
        print("Loading issues...")
        issues = self.load_issues()
        
        if not issues:
            report_content = """# Code Quality Analysis Report

This report analyzes High and Medium severity issues found in the codebase.

**No High/Medium severity issues found.**

All issues are of Low severity and have been filtered out for this report.
"""
        else:
            print(f"Found {len(issues)} High/Medium issues for analysis")
            
            # Try to use Gemini API if available, otherwise fall back to basic analysis
            try:
                report_content = self._generate_gemini_report(issues)
            except Exception as e:
                print(f"Gemini API not available ({e}), using basic analysis...")
                report_content = self._generate_basic_report(issues)
        
        # Write report to file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"Report generated: {self.output_file}")
    
    def _generate_gemini_report(self, issues: List[Dict[str, Any]]) -> str:
        """Generate report using Gemini API"""
        try:
            import google.generativeai as genai
            
            # Configure Gemini
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not set")
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Process issues in batches of 4
            batch_size = 4
            report_content = """# Code Quality Analysis Report

This report analyzes High and Medium severity issues found in the codebase using AI-powered analysis.

---

"""
            
            for i in range(0, len(issues), batch_size):
                batch = issues[i:i + batch_size]
                print(f"Processing LLM batch {i//batch_size + 1}/{(len(issues) + batch_size - 1)//batch_size}")
                
                # Create prompt for this batch
                prompt = self._create_llm_prompt(batch)
                
                # Generate response from Gemini
                response = model.generate_content(prompt)
                report_content += response.text + "\n\n"
            
            print("✓ LLM-powered report generated successfully")
            return report_content
            
        except ImportError:
            raise Exception("google-generativeai not installed")
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")
    
    def _generate_basic_report(self, issues: List[Dict[str, Any]]) -> str:
        """Generate basic report without LLM"""
        # Sort issues by severity (High first, then Medium)
        issues.sort(key=lambda x: (x.get('severity', '').lower() != 'high', x.get('severity', '').lower()))
        
        report_content = f"""# Code Quality Analysis Report

This report analyzes High and Medium severity issues found in the codebase.

**Total Issues Analyzed:** {len(issues)}
**High Severity:** {len([i for i in issues if i.get('severity', '').lower() == 'high'])}
**Medium Severity:** {len([i for i in issues if i.get('severity', '').lower() == 'medium'])}

---

"""
        
        # Process each issue
        for i, issue in enumerate(issues, 1):
            report_content += self._analyze_issue_for_report(issue, i)
        
        print("✓ Basic report generated successfully")
        return report_content
    
    def _create_llm_prompt(self, issues_batch: List[Dict[str, Any]]) -> str:
        """Create prompt for LLM analysis of a batch of issues"""
        prompt = """You are a code quality assistant. 
You will be given information about code issues from a repository including their file paths and line numbers. 
These issues have been flagged by a static analysis step.

### Instructions:
1. Only analyze issues with severity = High or Medium. Ignore Low.
2. For each issue:
   - Verify if it is indeed an issue. 
     - if it is not an issue do nothing and move to the next issue.
   - If it is an issue:
     - Explain clearly **why it is an issue** (security, complexity, documentation, etc.).
     - Suggest **how to fix or improve it** (concrete recommendations and implementable).
     - Prioritize the issue by severity and impact (High first, then Medium).
3. Output must be in **Markdown format**, using the following template:

### Format for Each Issue:
File: <file path> (lines <start>-<end>)
Severity: <High/Medium>
Issue: <short summary>

Why it is an issue:
<detailed explanation>

How to fix:
<detailed suggestion>

Priority: <High/Medium - based on severity and impact>

---

## Issues to Analyze:

"""
        
        for i, issue in enumerate(issues_batch, 1):
            file_path = issue['file']
            start_line = issue['lines'][0]
            end_line = issue['lines'][1]
            severity = issue['severity']
            issue_type = issue['issue']
            category = issue['category']
            
            prompt += f"""
### Issue {i}:
**File:** {file_path} (lines {start_line}-{end_line})
**Severity:** {severity}
**Category:** {category}
**Issue Type:** {issue_type}
** Code Snippet:** {self.extract_lines_from_file(file_path, start_line, end_line)}

---

"""
        
        return prompt
    
    def _analyze_issue_for_report(self, issue: Dict[str, Any], issue_num: int) -> str:
        """Analyze a single issue and generate report section (for basic report)"""
        file_path = issue['file']
        start_line = issue['lines'][0]
        end_line = issue['lines'][1]
        severity = issue['severity']
        issue_type = issue['issue']
        category = issue['category']
        explanation = issue.get('explanation', 'No explanation provided')
        suggestion = issue.get('suggestion', 'No suggestion provided')
        
        # Generate analysis based on category and severity
        analysis = self._generate_issue_analysis(issue)
        
        report_section = f"""### Issue {issue_num}: {issue_type}
**File:** {file_path} (lines {start_line}-{end_line})
**Severity:** {severity}
**Category:** {category}

**Why it is an issue:**
{analysis['why_issue']}

**How to fix:**
{analysis['how_to_fix']}

**Priority:** {analysis['priority']}

---

"""
        return report_section
    
    def _generate_issue_analysis(self, issue: Dict[str, Any]) -> Dict[str, str]:
        """Generate analysis for an issue based on its category"""
        category = issue['category'].lower()
        severity = issue['severity'].lower()
        explanation = issue.get('explanation', 'No explanation provided')
        suggestion = issue.get('suggestion', 'No suggestion provided')
        
        analysis = {
            'why_issue': explanation,
            'how_to_fix': suggestion,
            'priority': severity.title()
        }
        
        # Enhance analysis based on category
        if category == 'security':
            analysis['why_issue'] = f"**Security Risk:** {analysis['why_issue']}\n\nThis poses a security vulnerability that could be exploited by attackers."
            analysis['priority'] = "High" if severity == 'high' else "Medium"
            
        elif category == 'complexity':
            analysis['why_issue'] = f"**Complexity Issue:** {analysis['why_issue']}\n\nHigh complexity makes code hard to understand, test, and maintain."
            analysis['priority'] = "High" if severity == 'high' else "Medium"
            
        elif category == 'documentation':
            analysis['why_issue'] = f"**Documentation Issue:** {analysis['why_issue']}\n\nMissing documentation makes the codebase harder to understand and maintain."
            analysis['priority'] = "Medium"
            
        elif category == 'duplication':
            analysis['why_issue'] = f"**Code Duplication:** {analysis['why_issue']}\n\nDuplicated code increases maintenance burden and can lead to inconsistencies."
            analysis['priority'] = "Medium"
        
        return analysis


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Generate LLM-powered code quality report')
    parser.add_argument('issues_file', help='Path to issues.json file')
    parser.add_argument('-o', '--output', default='Report.md', help='Output file path (default: Report.md)')
    parser.add_argument('--api-key', help='Gemini API key (or set GEMINI_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Set API key if provided
    if args.api_key:
        os.environ['GEMINI_API_KEY'] = args.api_key
    
    if not os.path.exists(args.issues_file):
        print(f"Error: {args.issues_file} not found.")
        return 1
    
    try:
        generator = ReportGenerator(args.issues_file, args.output)
        generator.generate_report()
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
