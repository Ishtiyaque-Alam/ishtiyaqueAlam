import hashlib
import networkx as nx
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass


@dataclass
class DuplicateFunction:
    file: str
    class_name: Optional[str]
    function: str
    lines: List[int]
    category: str
    issue: str
    severity: str
    explanation: str
    suggestion: str


class GlobalAnalyzer:
    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        self.function_hashes = {}
        self.file_issues = defaultdict(list)
    
    def analyze_duplication(self, functions: List[Dict[str, Any]]) -> List[DuplicateFunction]:
        """Analyze for duplicate functions"""
        duplicates = []
        hash_to_functions = defaultdict(list)
        
        for func in functions:
            # Normalize function code for comparison
            normalized_code = self._normalize_function_code(func['code'])
            code_hash = hashlib.md5(normalized_code.encode()).hexdigest()
            
            hash_to_functions[code_hash].append(func)
        
        # Find functions with same hash (duplicates)
        for code_hash, func_list in hash_to_functions.items():
            if len(func_list) > 1:
                # Create duplicate issue for each function
                for func in func_list:
                    other_files = [f['file'] for f in func_list if f['file'] != func['file']]
                    
                    duplicates.append(DuplicateFunction(
                        file=func['file'],
                        class_name=func.get('class'),
                        function=func['function'],
                        lines=[func['start_line'], func['end_line']],
                        category='duplication',
                        issue='Duplicate function detected',
                        severity='Medium',
                        explanation=f'This function is duplicated in: {", ".join(other_files)}',
                        suggestion='Extract common functionality into a shared utility function or class.'
                    ))
        
        return duplicates
    
    def build_dependency_graph(self, functions: List[Dict[str, Any]]) -> nx.DiGraph:
        """
        Build a comprehensive dependency graph:
        - File nodes
        - Imported module nodes
        - Class nodes
        - Method/function nodes
        - Edges for imports, class membership, and function calls
        """
        self.dependency_graph.clear()

        files = set(func['file'] for func in functions)
        # Add all files as nodes
        for file_path in files:
            self.dependency_graph.add_node(file_path, type='file')

        # Add imported modules as nodes and edges
        for func in functions:
            file_path = func['file']
            imports = func.get('imports', [])
            for import_stmt in imports:
                imported_file = self._extract_imported_file(import_stmt, file_path)
                if imported_file:
                    self.dependency_graph.add_node(imported_file, type='imported_module')
                    self.dependency_graph.add_edge(file_path, imported_file, type='imports')

        # Add class and method/function nodes
        for func in functions:
            file_path = func['file']
            class_name = func.get('class_name', '')
            func_name = func['function']
            # Class node
            if class_name:
                class_id = f"{file_path}::{class_name}"
                self.dependency_graph.add_node(class_id, type='class')
                self.dependency_graph.add_edge(file_path, class_id, type='contains')
            # Method/function node
            func_id = f"{file_path}::{class_name}::{func_name}" if class_name else f"{file_path}::{func_name}"
            self.dependency_graph.add_node(func_id, type='function')
            # Edge from class to method
            if class_name:
                self.dependency_graph.add_edge(class_id, func_id, type='has_method')
            else:
                self.dependency_graph.add_edge(file_path, func_id, type='contains_function')

        # Add edges for function calls
        func_id_map = {}
        for func in functions:
            class_name = func.get('class_name', '')
            func_name = func['function']
            file_path = func['file']
            func_id = f"{file_path}::{class_name}::{func_name}" if class_name else f"{file_path}::{func_name}"
            func_id_map[(file_path, class_name, func_name)] = func_id

        for func in functions:
            caller_file = func['file']
            caller_class = func.get('class_name', '')
            caller_name = func['function']
            caller_id = func_id_map[(caller_file, caller_class, caller_name)]
            for callee in func.get('calls', []):
                # Try to find the callee function in the same file or any file
                callee_candidates = [
                    func_id_map.get((caller_file, callee.get('class_name', ''), callee['function'])) if isinstance(callee, dict) else func_id_map.get((caller_file, '', callee)),
                ]
                # If not found in same file, try all files
                if not any(callee_candidates):
                    for f in functions:
                        if f['function'] == (callee['function'] if isinstance(callee, dict) else callee):
                            callee_file = f['file']
                            callee_class = f.get('class_name', '')
                            callee_name = f['function']
                            callee_id = func_id_map.get((callee_file, callee_class, callee_name))
                            if callee_id:
                                callee_candidates.append(callee_id)
                for callee_id in callee_candidates:
                    if callee_id:
                        self.dependency_graph.add_edge(caller_id, callee_id, type='calls')

        return self.dependency_graph
    
    def annotate_graph_with_issues(self, issues: List[Any]) -> nx.DiGraph:
        """Annotate dependency graph with issue information"""
        # Group issues by file
        file_issues = defaultdict(list)
        for issue in issues:
            file_issues[issue.file].append(issue)
        
        # Add issue annotations to graph nodes
        for file_path in self.dependency_graph.nodes():
            file_issues_list = file_issues.get(file_path, [])
            
            # Count issues by category and severity
            issues_by_category = Counter(issue.category for issue in file_issues_list)
            issues_by_severity = Counter(issue.severity for issue in file_issues_list)
            
            self.dependency_graph.nodes[file_path].update({
                'total_issues': len(file_issues_list),
                'issues_by_category': dict(issues_by_category),
                'severity_distribution': dict(issues_by_severity),
                'issues': file_issues_list
            })
        
        return self.dependency_graph
    
    def get_file_dependencies(self, file_path: str) -> List[str]:
        """Get files that the given file depends on"""
        return list(self.dependency_graph.predecessors(file_path))
    
    def get_file_dependents(self, file_path: str) -> List[str]:
        """Get files that depend on the given file"""
        return list(self.dependency_graph.successors(file_path))
    
    def get_impact_analysis(self, file_path: str) -> Dict[str, Any]:
        """Analyze the impact of changes to a file"""
        if file_path not in self.dependency_graph:
            return {}
        
        # Get all files that depend on this file (transitive)
        dependents = set()
        for dependent in nx.descendants(self.dependency_graph, file_path):
            dependents.add(dependent)
        
        # Count total issues in dependent files
        total_issues = 0
        for dep_file in dependents:
            if 'total_issues' in self.dependency_graph.nodes[dep_file]:
                total_issues += self.dependency_graph.nodes[dep_file]['total_issues']
        
        return {
            'direct_dependents': len(self.dependency_graph.successors(file_path)),
            'transitive_dependents': len(dependents),
            'total_issues_in_dependents': total_issues,
            'dependent_files': list(dependents)
        }
    
    def _normalize_function_code(self, code: str) -> str:
        """Normalize function code for duplicate detection"""
        # Remove comments and docstrings
        lines = code.split('\n')
        normalized_lines = []
        
        in_docstring = False
        docstring_quote = None
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Handle docstrings
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    # Start of docstring
                    if '"""' in line:
                        docstring_quote = '"""'
                    else:
                        docstring_quote = "'''"
                    in_docstring = True
                    continue
                else:
                    # End of docstring
                    if docstring_quote in line:
                        in_docstring = False
                        docstring_quote = None
                    continue
            
            if in_docstring:
                continue
            
            # Skip comments
            if stripped.startswith('#'):
                continue
            
            # Normalize whitespace
            normalized_line = ' '.join(stripped.split())
            normalized_lines.append(normalized_line)
        
        return '\n'.join(normalized_lines)
    
    def _extract_imported_file(self, import_stmt: str, current_file: str) -> Optional[str]:
        """Extract the file path from an import statement (Python, Java, JS)"""
        import_stmt = import_stmt.strip()

        # ---------- Python ----------
        if import_stmt.startswith('from '):
            parts = import_stmt.split()
            if len(parts) >= 2:
                module_name = parts[1]
                return module_name.replace('.', '/') + '.py'
        elif import_stmt.startswith('import '):
            parts = import_stmt.split()
            if len(parts) >= 2:
                module_name = parts[1].split('.')[0]
                return module_name + '.py'

        # ---------- Java ----------
        if import_stmt.startswith('import '):
            # e.g. import java.util.List;
            parts = import_stmt.replace(';', '').split()
            if len(parts) >= 2:
                module_name = parts[1]
                return module_name.replace('.', '/') + '.java'

        # ---------- JavaScript ----------
        if import_stmt.startswith('import '):
            # e.g. import fs from 'fs';
            if ' from ' in import_stmt:
                module_name = import_stmt.split(' from ')[-1].strip("';\"")
                return module_name + '.js'
        if 'require(' in import_stmt:
            # e.g. const fs = require('fs');
            start = import_stmt.find("require(") + len("require(")
            end = import_stmt.find(")", start)
            module_name = import_stmt[start:end].strip("';\"")
            return module_name + '.js'

        return None

