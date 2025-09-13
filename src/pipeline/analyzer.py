import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm
from dataclasses import asdict

from src.parsers.tree_sitter_parser import TreeSitterParser
from src.analyzers.local_analyzer import LocalAnalyzer, Issue
from src.analyzers.global_analyzer import GlobalAnalyzer, DuplicateFunction
from src.vector_db.chroma_manager import ChromaManager
from src.visualization.graph_visualizer import GraphVisualizer
from src.qa_agent.semantic_search import SemanticSearchAgent


class CodeAnalyzer:
    def __init__(self, output_dir: str = "./analysis_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.parser = TreeSitterParser()
        self.local_analyzer = LocalAnalyzer()
        self.global_analyzer = GlobalAnalyzer()
        self.chroma_manager = ChromaManager(persist_directory=str(self.output_dir / "chroma_db"))
        self.visualizer = GraphVisualizer()
        
        # Results storage
        self.functions = []
        self.issues = []
        self.duplicates = []
        self.dependency_graph = None
        self.qa_agent = None
    
    def analyze(self, target_path: str) -> Dict[str, Any]:
        """Main analysis pipeline"""
        print(f"Starting analysis of: {target_path}")
        
        # Step 1: Parse code and extract functions
        print("Step 1: Parsing code...")
        self.functions = self._parse_code(target_path)
        print(f"Found {len(self.functions)} functions")
        
        # Step 2: Local issue analysis
        print("Step 2: Analyzing local issues...")
        self.issues = self._analyze_local_issues()
        print(f"Found {len(self.issues)} local issues")
        
        # Step 3: Global analysis
        print("Step 3: Analyzing global issues...")
        self.duplicates = self._analyze_global_issues()
        print(f"Found {len(self.duplicates)} duplicate functions")
        
        # Step 4: Build dependency graph
        print("Step 4: Building dependency graph...")
        self.dependency_graph = self._build_dependency_graph()
        print(f"Built graph with {self.dependency_graph.number_of_nodes()} nodes and {self.dependency_graph.number_of_edges()} edges")
        
        # Step 5: Store in vector databases
        print("Step 5: Storing in vector databases...")
        self._store_in_vector_dbs()
        
        # Step 6: Create visualizations
        print("Step 6: Creating visualizations...")
        self._create_visualizations()
        
        # Step 7: Initialize QA agent
        print("Step 7: Initializing QA agent...")
        self.qa_agent = SemanticSearchAgent(self.chroma_manager, self.dependency_graph)
        
        #Step 8: Generate reports
        print("Step 8: Generating reports...")
        self._generate_reports()
        
        # Step 9: Generate LLM-powered Markdown report
        print("Step 9: Generating LLM-powered Markdown report...")
        self._generate_markdown_report()
        
        print("Analysis complete!")
        return self._get_summary()
    
    def _parse_code(self, target_path: str) -> List[Dict[str, Any]]:
        """Parse code and extract functions"""
        if os.path.isfile(target_path):
            functions = self.parser.parse_file(target_path)
        else:
            functions = self.parser.parse_directory(target_path)
        
        # Save chunks
        chunks_path = self.output_dir / "chunks.json"
        self.parser.save_chunks(functions, str(chunks_path))
        
        return functions
    
    def _analyze_local_issues(self) -> List[Issue]:
        """Analyze local issues for each function"""
        issues = []
        
        for func in tqdm(self.functions, desc="Analyzing functions"):
            func_issues = self.local_analyzer.analyze_function(func)
            issues.extend(func_issues)
        
        return issues
    
    def _analyze_global_issues(self) -> List[DuplicateFunction]:
        """Analyze global issues (duplication)"""
        duplicates = self.global_analyzer.analyze_duplication(self.functions)
        return duplicates
    
    def _build_dependency_graph(self) -> Any:
        """Build dependency graph and annotate with issues"""
        # Build graph]
        graph = self.global_analyzer.build_dependency_graph(self.functions)
        
        # Combine all issues
        all_issues = self.issues + self.duplicates
        
        # Annotate graph with issues
        graph = self.global_analyzer.annotate_graph_with_issues(all_issues)
        
        return graph
    
    def _store_in_vector_dbs(self):
        """Store functions and issues in vector databases"""
        # Store functions in CodeDB
        self.chroma_manager.add_code_functions(self.functions)
        
        # Store issues in IssuesDB
        all_issues = self.issues + self.duplicates
        self.chroma_manager.add_issues(all_issues)
    
    def _create_visualizations(self):
        """Create interactive visualizations"""
        # Create interactive dependency graph
        graph_path = self.output_dir / "graph.html"
        self.visualizer.create_interactive_graph(
            self.dependency_graph, 
            str(graph_path)
        )
        
        # Create summary report
        report_path = self.output_dir / "summary_report.html"
        self.visualizer.create_summary_report(
            self.dependency_graph,
            str(report_path)
        )
    
    def _generate_reports(self):
        """Generate JSON reports and Markdown report"""
        # Save issues
        issues_path = self.output_dir / "issues.json"
        self._save_issues(issues_path)
        
        # # Save enriched report
        # report_path = self.output_dir / "report.json"
        # self._save_enriched_report(report_path)
        
        # Markdown report will be generated in Step 9 with LLM
    
    def _save_issues(self, output_path: str):
        """Save issues to JSON file"""
        issues_data = []
        
        for issue in self.issues + self.duplicates:

            if isinstance(issue,Issue):
                issue_dict = asdict(issue)
            elif isinstance(issue, DuplicateFunction):

                issue_dict = {
                    "file": issue.file,
                    "class": issue.class_name or "",
                    "function": issue.function,
                    "lines": issue.lines,
                    "category": issue.category,
                    "issue": issue.issue,
                    "severity": issue.severity,
                    "explanation": issue.explanation,
                    "suggestion": issue.suggestion
                }
            else:
                raise TypeError(f"Unsupported issue type: {type(issue)}")
            issues_data.append(issue_dict)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(issues_data, f, indent=2, ensure_ascii=False)
    
    def _generate_markdown_report(self):
        """Generate Markdown report using the separate report generator"""
        import subprocess
        import sys
        
        issues_file = self.output_dir / "issues.json"
        report_file = self.output_dir / "Report.md"
        
        # Use the separate report generator script
        script_path = Path(__file__).parent / "report_generator.py"
        
        try:
            result = subprocess.run([
                sys.executable, str(script_path), 
                str(issues_file), 
                "-o", str(report_file)
            ], capture_output=True, text=True, check=True)
            
            print("  Markdown report generated successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"Error generating report: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
        except Exception as e:
            print(f"Unexpected error: {e}")
    
    def _get_summary(self) -> Dict[str, Any]:
        """Get analysis summary"""
        total_functions = len(self.functions)
        total_issues = len(self.issues) + len(self.duplicates)
        
        # Count issues by category
        issues_by_category = {}
        for issue in self.issues + self.duplicates:
            category = issue.category
            issues_by_category[category] = issues_by_category.get(category, 0) + 1
        
        # Count issues by severity
        issues_by_severity = {}
        for issue in self.issues + self.duplicates:
            severity = issue.severity
            issues_by_severity[severity] = issues_by_severity.get(severity, 0) + 1
        
        return {
            "total_functions": total_functions,
            "total_issues": total_issues,
            "issues_by_category": issues_by_category,
            "issues_by_severity": issues_by_severity,
            "files_analyzed": len(set(func['file'] for func in self.functions)),
            "dependencies": self.dependency_graph.number_of_edges() if self.dependency_graph else 0
        }
    
