import tree_sitter
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path


class TreeSitterParser:
    def __init__(self, exclude_patterns=None, exclude_dirs=None):
        self.languages = {}
        self.parsers = {}
        
        # Default exclusion patterns
        self.exclude_patterns = exclude_patterns or [
            # Common build/cache directories
            '__pycache__',
            'node_modules',
            '.git',
            '.svn',
            '.hg',
            'build',
            'dist',
            'target',
            'out',
            'bin',
            'obj',
            'lib',
            '__pycache__',
            'code_analyzer.egg-info',
            # Common cache files
            '*.pyc',
            '*.pyo',
            '*.pyd',
            '*.so',
            '*.dll',
            '*.exe',
            '*.o',
            '*.a',
            '*.lib',
            '*.jar',
            '*.war',
            '*.ear',
            # IDE/Editor files
            '.vscode',
            '.idea',
            '*.swp',
            '*.swo',
            '*~',
            '.DS_Store',
            'Thumbs.db',
            # Test files (optional - can be configured)
            # 'test_*',
            # '*_test.py',
            # 'tests/',
            # Documentation files
            '*.md',
            '*.txt',
            '*.rst',
            '*.pdf',
            '*.doc',
            '*.docx',
            # Config files
            '*.ini',
            '*.cfg',
            '*.conf',
            '*.config',
            '*.xml',
            '*.yaml',
            '*.yml',
            '*.json',
            '*.toml',
            # Log files
            '*.log',
            '*.out',
            '*.err',
            # Temporary files
            '*.tmp',
            '*.temp',
            '*.bak',
            '*.backup',
            '*.orig',
            '*.rej',
            # Library and third-party files
            '*.min.js',
            '*.min.css',
            '*.bundle.js',
            '*.chunk.js',
            '*.vendor.js',
            # Analysis output files
            'analysis_output',
            'chroma_db',
            '*.html',
            '*.sqlite3',
            '*.db',
            # Package files
            '*.egg-info',
            '*.dist-info',
            '*.whl',
            '*.tar.gz',
            '*.zip',
            # Virtual environments
            'venv',
            'env',
            '.env',
            'env.bak',
            'venv.bak'
        ]
        
        # Default exclusion directories
        self.exclude_dirs = exclude_dirs or [
            '__pycache__',
            'node_modules',
            '.git',
            '.svn',
            '.hg',
            'build',
            'dist',
            'target',
            'out',
            'bin',
            'obj',
            'lib',
            '.vscode',
            '.idea',
            'venv',
            'env',
            '.env',
            'env.bak',
            'venv.bak',
            'analysis_output',
            'chroma_db',
            '*.egg-info',
            '*.dist-info'
        ]
        
        self._setup_languages()
    
    def _setup_languages(self):
        """Initialize tree-sitter languages and parsers"""
        try:
            # Python
            from tree_sitter import Language, Parser
            import tree_sitter_python as tspython
            
            python_lang = Language(tspython.language())
            python_parser = Parser()
            python_parser.language = python_lang
            
            self.languages['python'] = python_lang
            self.parsers['python'] = python_parser
            
            # JavaScript
            import tree_sitter_javascript as tsjavascript
            js_lang = Language(tsjavascript.language())
            js_parser = Parser()
            js_parser.language = js_lang
            
            self.languages['javascript'] = js_lang
            self.parsers['javascript'] = js_parser
            
            # Java
            import tree_sitter_java as tsjava
            java_lang = Language(tsjava.language())
            java_parser = Parser()
            java_parser.language = java_lang
            
            self.languages['java'] = java_lang
            self.parsers['java'] = java_parser
            
        except ImportError as e:
            print(f"Warning: Could not import tree-sitter language: {e}")
    
    def get_language(self, file_path: str) -> Optional[str]:
        """Determine language from file extension"""
        ext = Path(file_path).suffix.lower()
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'javascript',
            '.tsx': 'javascript',
            '.java': 'java'
        }
        return ext_to_lang.get(ext)
    
    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a single file and extract function-level chunks"""
        language = self.get_language(file_path)
        if not language or language not in self.parsers:
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []
        
        parser = self.parsers[language]
        tree = parser.parse(bytes(content, 'utf8'))
        
        if language == 'python':
            return self._parse_python_functions(tree, content, file_path)
        elif language == 'javascript':
            return self._parse_javascript_functions(tree, content, file_path)
        elif language == 'java':
            return self._parse_java_functions(tree, content, file_path)
        
        return []
    
    def _parse_python_functions(self, tree, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract Python functions and methods"""
        functions = []
        lines = content.split('\n')
        
        def traverse(node, class_name=None):
            if node.type == 'function_definition':
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                        break
                
                if func_name:
                    func_data = self._extract_function_data(node, lines, file_path, func_name, class_name)
                    if func_data:
                        functions.append(func_data)
            
            elif node.type == 'class_definition':
                class_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                        break
                
                # Traverse class body for methods
                for child in node.children:
                    if child.type == 'block':
                        traverse(child, class_name)
            
            else:
                for child in node.children:
                    traverse(child, class_name)
        
        traverse(tree.root_node)
        return functions
    
    def _parse_javascript_functions(self, tree, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract JavaScript functions and methods"""
        functions = []
        lines = content.split('\n')
        
        def traverse(node, class_name=None):
            if node.type in ['function_declaration', 'method_definition', 'arrow_function']:
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                        break
                
                if func_name:
                    func_data = self._extract_function_data(node, lines, file_path, func_name, class_name)
                    if func_data:
                        functions.append(func_data)
            
            elif node.type == 'class_declaration':
                class_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                        break
                
                # Traverse class body for methods
                for child in node.children:
                    if child.type == 'class_body':
                        traverse(child, class_name)
            
            else:
                for child in node.children:
                    traverse(child, class_name)
        
        traverse(tree.root_node)
        return functions
    
    def _parse_java_functions(self, tree, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract Java methods"""
        functions = []
        lines = content.split('\n')
        
        def traverse(node, class_name=None):
            if node.type == 'method_declaration':
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                        break
                
                if func_name:
                    func_data = self._extract_function_data(node, lines, file_path, func_name, class_name)
                    if func_data:
                        functions.append(func_data)
            
            elif node.type == 'class_declaration':
                class_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                        break
                
                # Traverse class body for methods
                for child in node.children:
                    if child.type == 'class_body':
                        traverse(child, class_name)
            
            else:
                for child in node.children:
                    traverse(child, class_name)
        
        traverse(tree.root_node)
        return functions
    
    def _extract_function_data(self, node, lines: List[str], file_path: str, func_name: str, class_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """Extract metadata for a function"""
        start_line = node.start_point[0] + 1  # 1-indexed
        end_line = node.end_point[0] + 1
        
        # Extract function body
        func_lines = lines[start_line-1:end_line]
        func_code = '\n'.join(func_lines)
        
        # Extract parameters
        parameters = self._extract_parameters(node)
        
        # Calculate metrics
        function_length = end_line - start_line + 1
        nesting_depth = self._calculate_nesting_depth(node)
        has_docstring = self._has_docstring(func_code)
        
        # Extract function calls and imports
        calls = self._extract_function_calls(node, lines)
        imports = self._extract_imports(lines[:start_line])  # Only imports before function
        
        return {
            "file": file_path,
            "class": class_name,
            "function": func_name,
            "start_line": start_line,
            "end_line": end_line,
            "parameters": parameters,
            "function_length": function_length,
            "nesting_depth": nesting_depth,
            "has_docstring": has_docstring,
            "calls": calls,
            "imports": imports,
            "parent_file": file_path,
            "code": func_code
        }
    
    def _extract_parameters(self, node) -> List[str]:
        """Extract function parameters"""
        parameters = []
        
        def find_parameters(n):
            if n.type in ['parameter', 'formal_parameter']:
                for child in n.children:
                    if child.type == 'identifier':
                        parameters.append(child.text.decode('utf-8'))
            else:
                for child in n.children:
                    find_parameters(child)
        
        find_parameters(node)
        return parameters
    
    def _calculate_nesting_depth(self, node) -> int:
        """Calculate maximum nesting depth of the function"""
        max_depth = 0
        
        def traverse(n, depth):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            
            for child in n.children:
                if child.type in ['block', 'if_statement', 'for_statement', 'while_statement', 'try_statement']:
                    traverse(child, depth + 1)
                else:
                    traverse(child, depth)
        
        traverse(node, 0)
        return max_depth
    
    def _has_docstring(self, code: str) -> bool:
        """Check if function has a docstring"""
        lines = code.strip().split('\n')
        if len(lines) < 2:
            return False
        
        # Check for triple quotes in first few lines
        for line in lines[:5]:
            if '"""' in line or "'''" in line:
                return True
        return False
    
    def _extract_function_calls(self, node, lines: List[str]) -> List[str]:
        """Extract function calls within the function body"""
        calls = []
        
        def find_calls(n):
            if n.type == 'call':
                # Extract function name
                for child in n.children:
                    if child.type == 'identifier':
                        calls.append(child.text.decode('utf-8'))
                    elif child.type == 'attribute':
                        # Handle method calls like obj.method()
                        call_parts = []
                        for grandchild in child.children:
                            if grandchild.type == 'identifier':
                                call_parts.append(grandchild.text.decode('utf-8'))
                        if call_parts:
                            calls.append('.'.join(call_parts))
            else:
                for child in n.children:
                    find_calls(child)
        
        find_calls(node)
        return list(set(calls))  # Remove duplicates
    
    def _extract_imports(self, lines: List[str]) -> List[str]:
        """Extract import statements from lines"""
        imports = []
        
        for line in lines:
            line = line.strip()
            if line.startswith(('import ', 'from ')):
                imports.append(line)
        
        return imports
    
    def parse_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Parse all supported files in a directory recursively"""
        all_functions = []
        
        for root, dirs, files in os.walk(directory_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self._should_exclude_dir(d)]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if file should be excluded
                if self._should_exclude_file(file_path):
                    continue
                
                # Check if file has supported language
                if self.get_language(file_path):
                    functions = self.parse_file(file_path)
                    all_functions.extend(functions)
        
        return all_functions
    
    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if a file should be excluded based on patterns"""
        import fnmatch
        
        file_name = os.path.basename(file_path)
        relative_path = os.path.relpath(file_path)
        
        # Check against exclusion patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(relative_path, pattern):
                return True
        
        return False
    
    def _should_exclude_dir(self, dir_name: str) -> bool:
        """Check if a directory should be excluded"""
        return dir_name in self.exclude_dirs
    
    def add_exclusion_pattern(self, pattern: str):
        """Add a new exclusion pattern"""
        if pattern not in self.exclude_patterns:
            self.exclude_patterns.append(pattern)
    
    def add_exclusion_dir(self, dir_name: str):
        """Add a new exclusion directory"""
        if dir_name not in self.exclude_dirs:
            self.exclude_dirs.append(dir_name)
    
    def remove_exclusion_pattern(self, pattern: str):
        """Remove an exclusion pattern"""
        if pattern in self.exclude_patterns:
            self.exclude_patterns.remove(pattern)
    
    def remove_exclusion_dir(self, dir_name: str):
        """Remove an exclusion directory"""
        if dir_name in self.exclude_dirs:
            self.exclude_dirs.remove(dir_name)
    
    def get_exclusion_patterns(self) -> List[str]:
        """Get current exclusion patterns"""
        return self.exclude_patterns.copy()
    
    def get_exclusion_dirs(self) -> List[str]:
        """Get current exclusion directories"""
        return self.exclude_dirs.copy()
    
    def save_chunks(self, functions: List[Dict[str, Any]], output_path: str):
        """Save function chunks to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(functions, f, indent=2, ensure_ascii=False)
