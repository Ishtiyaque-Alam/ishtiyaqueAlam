from typing import List, Dict, Any, Optional, Tuple
import json
import networkx as nx
from src.vector_db.chroma_manager import ChromaManager


class SemanticSearchAgent:
    def __init__(self, chroma_manager: ChromaManager, dependency_graph: nx.DiGraph):
        self.chroma_manager = chroma_manager
        self.dependency_graph = dependency_graph
    
    def search_code(self, query: str, n_results: int = 5, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search for code functions using semantic search"""
        return self.chroma_manager.search_code(query, n_results, filters)
    
    def search_issues(self, query: str, n_results: int = 5, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search for code issues using semantic search"""
        return self.chroma_manager.search_issues(query, n_results, filters)
    
    def get_code_with_context(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Get code functions with expanded context from dependencies"""
        # First, search for relevant functions
        code_results = self.search_code(query, n_results)
        
        # Expand context for each result
        expanded_results = []
        for result in code_results:
            expanded_result = self._expand_code_context(result)
            expanded_results.append(expanded_result)
        
        return expanded_results
    
    def get_issues_with_context(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Get issues with expanded context from related files"""
        # Search for relevant issues
        issue_results = self.search_issues(query, n_results)
        
        # Expand context for each result
        expanded_results = []
        for result in issue_results:
            expanded_result = self._expand_issue_context(result)
            expanded_results.append(expanded_result)
        
        return expanded_results
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """Answer a natural language question about the codebase"""
        question_lower = question.lower()
        
        # Determine question type and search strategy
        if any(keyword in question_lower for keyword in ['security', 'vulnerability', 'injection', 'crypto', 'secret']):
            return self._answer_security_question(question)
        elif any(keyword in question_lower for keyword in ['performance', 'bottleneck', 'slow', 'optimize']):
            return self._answer_performance_question(question)
        elif any(keyword in question_lower for keyword in ['duplicate', 'copy', 'similar']):
            return self._answer_duplication_question(question)
        elif any(keyword in question_lower for keyword in ['documentation', 'docstring', 'comment']):
            return self._answer_documentation_question(question)
        elif any(keyword in question_lower for keyword in ['complex', 'complexity', 'nested']):
            return self._answer_complexity_question(question)
        else:
            return self._answer_general_question(question)
    
    def _expand_code_context(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Expand code context with dependency information"""
        metadata = result['metadata']
        file_path = metadata['file']
        
        # Get dependency information
        dependencies = self._get_file_dependencies(file_path)
        dependents = self._get_file_dependents(file_path)
        
        # Get related functions in the same file
        related_functions = self._get_related_functions_in_file(file_path)
        
        expanded_result = result.copy()
        expanded_result['context'] = {
            'dependencies': dependencies,
            'dependents': dependents,
            'related_functions': related_functions
        }
        
        return expanded_result
    
    def _expand_issue_context(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Expand issue context with related information"""
        metadata = result['metadata']
        file_path = metadata['file']
        
        # Get all issues in the same file
        file_issues = self.chroma_manager.get_issues_by_file(file_path)
        
        # Get issues of the same category
        category_issues = self.chroma_manager.get_issues_by_category(metadata['category'])
        
        # Get issues of the same severity
        severity_issues = self.chroma_manager.get_issues_by_severity(metadata['severity'])
        
        expanded_result = result.copy()
        expanded_result['context'] = {
            'file_issues': file_issues,
            'category_issues': category_issues,
            'severity_issues': severity_issues
        }
        
        return expanded_result
    
    def _answer_security_question(self, question: str) -> Dict[str, Any]:
        """Answer security-related questions"""
        # Search for security issues
        security_issues = self.search_issues(question, n_results=10, filters={'category': 'security'})
        
        # Search for security-related code
        security_code = self.search_code(question, n_results=5)
        
        return {
            'type': 'security',
            'question': question,
            'security_issues': security_issues,
            'security_code': security_code,
            'summary': f"Found {len(security_issues)} security issues and {len(security_code)} related code functions."
        }
    
    def _answer_performance_question(self, question: str) -> Dict[str, Any]:
        """Answer performance-related questions"""
        # Search for complexity issues
        complexity_issues = self.search_issues(question, n_results=10, filters={'category': 'complexity'})
        
        # Search for performance-related code
        performance_code = self.search_code(question, n_results=5)
        
        return {
            'type': 'performance',
            'question': question,
            'complexity_issues': complexity_issues,
            'performance_code': performance_code,
            'summary': f"Found {len(complexity_issues)} complexity issues and {len(performance_code)} related code functions."
        }
    
    def _answer_duplication_question(self, question: str) -> Dict[str, Any]:
        """Answer duplication-related questions"""
        # Search for duplication issues
        duplication_issues = self.search_issues(question, n_results=10, filters={'category': 'duplication'})
        
        return {
            'type': 'duplication',
            'question': question,
            'duplication_issues': duplication_issues,
            'summary': f"Found {len(duplication_issues)} duplicate functions."
        }
    
    def _answer_documentation_question(self, question: str) -> Dict[str, Any]:
        """Answer documentation-related questions"""
        # Search for documentation issues
        doc_issues = self.search_issues(question, n_results=10, filters={'category': 'documentation'})
        
        return {
            'type': 'documentation',
            'question': question,
            'documentation_issues': doc_issues,
            'summary': f"Found {len(doc_issues)} documentation issues."
        }
    
    def _answer_complexity_question(self, question: str) -> Dict[str, Any]:
        """Answer complexity-related questions"""
        # Search for complexity issues
        complexity_issues = self.search_issues(question, n_results=10, filters={'category': 'complexity'})
        
        return {
            'type': 'complexity',
            'question': question,
            'complexity_issues': complexity_issues,
            'summary': f"Found {len(complexity_issues)} complexity issues."
        }
    
    def _answer_general_question(self, question: str) -> Dict[str, Any]:
        """Answer general questions"""
        # Search both code and issues
        code_results = self.search_code(question, n_results=5)
        issue_results = self.search_issues(question, n_results=5)
        
        return {
            'type': 'general',
            'question': question,
            'code_results': code_results,
            'issue_results': issue_results,
            'summary': f"Found {len(code_results)} relevant code functions and {len(issue_results)} related issues."
        }
    
    def _get_file_dependencies(self, file_path: str) -> List[str]:
        """Get files that the given file depends on"""
        if file_path in self.dependency_graph:
            return list(self.dependency_graph.predecessors(file_path))
        return []
    
    def _get_file_dependents(self, file_path: str) -> List[str]:
        """Get files that depend on the given file"""
        if file_path in self.dependency_graph:
            return list(self.dependency_graph.successors(file_path))
        return []
    
    def _get_related_functions_in_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Get other functions in the same file"""
        # This would require querying the code collection with file filter
        # For now, return empty list
        return []
    
    def get_impact_analysis(self, file_path: str) -> Dict[str, Any]:
        """Analyze the impact of changes to a file"""
        if file_path not in self.dependency_graph:
            return {"error": "File not found in dependency graph"}
        
        # Get dependency information
        dependencies = self._get_file_dependencies(file_path)
        dependents = self._get_file_dependents(file_path)
        
        # Get issues in the file
        file_issues = self.chroma_manager.get_issues_by_file(file_path)
        
        # Calculate impact metrics
        total_issues = len(file_issues)
        high_severity_issues = len([issue for issue in file_issues if issue['metadata'].get('severity') == 'High'])
        
        return {
            'file': file_path,
            'dependencies': dependencies,
            'dependents': dependents,
            'total_issues': total_issues,
            'high_severity_issues': high_severity_issues,
            'impact_score': len(dependents) + total_issues * 0.1
        }
