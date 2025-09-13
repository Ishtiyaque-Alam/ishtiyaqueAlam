import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Issue:
    file: str
    class_name: Optional[str]
    function: str
    lines: List[int]
    category: str
    issue: str
    severity: str
    explanation: str
    suggestion: str


class LocalAnalyzer:
    def __init__(self):
        # Base (Python-focused)
        self.security_patterns = {
            'eval_exec': re.compile(r'\b(eval|exec)\s*\('),
            'sql_injection': re.compile(r'["\'].*\+.*["\']', re.IGNORECASE),
            'weak_crypto': re.compile(r'\b(md5|sha1)\s*\('),
            'hardcoded_secrets': re.compile(r'(api[_-]?key|password|secret|token)\s*=\s*["\'][^"\']+["\']', re.IGNORECASE)
        }

        # JavaScript-specific
        self.security_patterns_js = {
            'eval': re.compile(r'\beval\s*\('),
            'function_constructor': re.compile(r'new\s+Function\s*\('),
            'inner_html': re.compile(r'\.innerHTML\s*='),
            'document_write': re.compile(r'document\.write\s*\('),
        }

        # Java-specific
        self.security_patterns_java = {
            'runtime_exec': re.compile(r'Runtime\.getRuntime\(\)\.exec\s*\('),
            'weak_crypto': re.compile(r'MessageDigest\.getInstance\(\s*"(MD5|SHA1)"\s*\)'),
            'jdbc_concat': re.compile(r'Statement\.execute(Query|Update)\s*\(.*\+".*"\)'),
        }


    
    def analyze_function(self, func_data: Dict[str, Any]) -> List[Issue]:
        """Analyze a single function for issues"""
        issues = []
        
        # Security analysis
        issues.extend(self._analyze_security(func_data))
        
        # Complexity analysis
        issues.extend(self._analyze_complexity(func_data))
        
        # Documentation analysis
        issues.extend(self._analyze_documentation(func_data))
        
        return issues
    
    def _analyze_security(self, func_data: Dict[str, Any]) -> List[Issue]:
        """Analyze security issues"""
        issues = []
        code = func_data.get('code', '')
        file_path = func_data['file']
        func_name = func_data['function']
        class_name = func_data.get('class')
        start_line = func_data['start_line']
        
        # Check for eval/exec
        if self.security_patterns['eval_exec'].search(code):
            issues.append(Issue(
                file=file_path,
                class_name=class_name,
                function=func_name,
                lines=[start_line, func_data['end_line']],
                category='security',
                issue='Use of eval/exec',
                severity='High',
                explanation='eval() and exec() can execute arbitrary code and pose security risks.',
                suggestion='Use safer alternatives like ast.literal_eval() or specific parsing functions.'
            ))
        
        # Check for SQL injection patterns
        if self.security_patterns['sql_injection'].search(code):
            issues.append(Issue(
                file=file_path,
                class_name=class_name,
                function=func_name,
                lines=[start_line, func_data['end_line']],
                category='security',
                issue='Potential SQL injection',
                severity='High',
                explanation='String concatenation in SQL queries can lead to SQL injection attacks.',
                suggestion='Use parameterized queries or prepared statements.'
            ))
        
        # Check for weak cryptography
        if self.security_patterns['weak_crypto'].search(code):
            issues.append(Issue(
                file=file_path,
                class_name=class_name,
                function=func_name,
                lines=[start_line, func_data['end_line']],
                category='security',
                issue='Weak cryptographic hash',
                severity='Medium',
                explanation='MD5 and SHA1 are cryptographically weak and vulnerable to collision attacks.',
                suggestion='Use SHA-256 or stronger hashing algorithms.'
            ))
        
        # Check for hardcoded secrets
        if self.security_patterns['hardcoded_secrets'].search(code):
            issues.append(Issue(
                file=file_path,
                class_name=class_name,
                function=func_name,
                lines=[start_line, func_data['end_line']],
                category='security',
                issue='Hardcoded secret detected',
                severity='High',
                explanation='Hardcoded secrets in source code are security risks.',
                suggestion='Use environment variables or secure secret management systems.'
            ))
                # --- JavaScript checks ---
        for name, pattern in self.security_patterns_js.items():
            if pattern.search(code):
                issues.append(Issue(
                    file=file_path,
                    class_name=class_name,
                    function=func_name,
                    lines=[start_line, func_data['end_line']],
                    category='security',
                    issue=f'JS Security: {name}',
                    severity='High',
                    explanation=f'Potential {name} security issue detected.',
                    suggestion='Avoid unsafe JS functions; use safer APIs.'
                ))

        # --- Java checks ---
        for name, pattern in self.security_patterns_java.items():
            if pattern.search(code):
                issues.append(Issue(
                    file=file_path,
                    class_name=class_name,
                    function=func_name,
                    lines=[start_line, func_data['end_line']],
                    category='security',
                    issue=f'Java Security: {name}',
                    severity='High',
                    explanation=f'Potential {name} security issue detected.',
                    suggestion='Refactor to safer Java APIs or libraries.'
                ))

        return issues
    
    def _analyze_complexity(self, func_data: Dict[str, Any]) -> List[Issue]:
        """Analyze complexity issues"""
        issues = []
        file_path = func_data['file']
        func_name = func_data['function']
        class_name = func_data.get('class')
        start_line = func_data['start_line']
        end_line = func_data['end_line']
        
        # Function length check
        function_length = func_data['function_length']
        if function_length > 200:
            severity = 'High' if function_length > 500 else 'Medium'
            issues.append(Issue(
                file=file_path,
                class_name=class_name,
                function=func_name,
                lines=[start_line, end_line],
                category='complexity',
                issue=f'Function too long ({function_length} lines)',
                severity=severity,
                explanation=f'Function has {function_length} lines, which makes it hard to understand and maintain.',
                suggestion='Break down the function into smaller, more focused functions.'
            ))
        
        # Cyclomatic complexity
        complexity = self._calculate_cyclomatic_complexity(func_data['code'])
        if complexity > 15:
            severity = 'High'
        elif complexity > 10:
            severity = 'Medium'
        else:
            severity = None
        
        if severity:
            issues.append(Issue(
                file=file_path,
                class_name=class_name,
                function=func_name,
                lines=[start_line, end_line],
                category='complexity',
                issue=f'High cyclomatic complexity ({complexity})',
                severity=severity,
                explanation=f'Function has high cyclomatic complexity ({complexity}), indicating many decision points.',
                suggestion='Simplify control flow by extracting methods or reducing conditional logic.'
            ))
        
        # Nesting depth check
        nesting_depth = func_data['nesting_depth']
        if nesting_depth > 3:
            issues.append(Issue(
                file=file_path,
                class_name=class_name,
                function=func_name,
                lines=[start_line, end_line],
                category='complexity',
                issue=f'Excessive nesting depth ({nesting_depth})',
                severity='Medium',
                explanation=f'Function has nesting depth of {nesting_depth}, making it hard to follow.',
                suggestion='Reduce nesting by using early returns, guard clauses, or extracting methods.'
            ))
        
        return issues
    
    def _analyze_documentation(self, func_data: Dict[str, Any]) -> List[Issue]:
        issues = []
        file_path = func_data['file']
        func_name = func_data['function']
        class_name = func_data.get('class')
        start_line = func_data['start_line']
        end_line = func_data['end_line']
        has_docstring = func_data['has_docstring']

        code = func_data.get('code', '')
        file_ext = file_path.split('.')[-1].lower()

        is_public = not func_name.startswith('_') or (
            func_name.startswith('__') and func_name.endswith('__')
        )

        missing_docs = False

        if file_ext == 'py':
            # Python → rely on has_docstring
            if is_public and not has_docstring:
                missing_docs = True

        elif file_ext == 'java':
            # Java → check for /** ... */ above method
            if not re.search(r'/\*\*.*\*/', code, re.DOTALL):
                missing_docs = True

        elif file_ext in ('js', 'jsx', 'ts', 'tsx'):
            # JavaScript/TypeScript → check for /** ... */ above function
            if not re.search(r'/\*\*.*\*/', code, re.DOTALL):
                missing_docs = True

        if missing_docs:
            issues.append(Issue(
                file=file_path,
                class_name=class_name,
                function=func_name,
                lines=[start_line, end_line],
                category='documentation',
                issue='Missing documentation',
                severity='Low',
                explanation=f'Function "{func_name}" is missing proper documentation.',
                suggestion='Add a docstring (Python) or Javadoc/JSDoc (Java/JS).'
            ))

        return issues
    
    def _calculate_cyclomatic_complexity(self, code: str) -> int:
        """Calculate cyclomatic complexity of a function (language-agnostic)"""
        import re
        
        # Language-agnostic approach: count control flow keywords
        # Base complexity
        complexity = 1
        
        # Convert to lowercase for case-insensitive matching
        code_lower = code.lower()
        
        # Define patterns for different types of control flow
        patterns = [
            # Conditional statements
            (r'\bif\b', 1),
            (r'\belif\b', 1),
            (r'\belse\s+if\b', 1),
            (r'\bswitch\b', 1),
            (r'\bcase\b', 1),
            (r'\bdefault\b', 1),
            
            # Loops
            (r'\bfor\b', 1),
            (r'\bwhile\b', 1),
            (r'\bdo\b', 1),
            (r'\bforeach\b', 1),
            
            # Exception handling
            (r'\btry\b', 1),
            (r'\bcatch\b', 1),
            (r'\bexcept\b', 1),
            (r'\bfinally\b', 1),
            
            # Logical operators (count each occurrence)
            (r'\band\b', 1),
            (r'\bor\b', 1),
            (r'&&', 1),
            (r'\|\|', 1),
            
            # Ternary operators
            (r'\?', 1),
            
            # Lambda/arrow functions (can add complexity)
            (r'=>', 0.5),
        ]
        
        # Count each pattern
        for pattern, weight in patterns:
            matches = re.findall(pattern, code_lower)
            complexity += len(matches) * weight
        
        # Additional complexity for nested structures
        # Count opening braces/brackets as indicators of nesting
        opening_braces = code.count('{') + code.count('[') + code.count('(')
        closing_braces = code.count('}') + code.count(']') + code.count(')')
        
        # Add complexity for unbalanced nesting (indicates complex structure)
        if opening_braces > closing_braces:
            complexity += (opening_braces - closing_braces) * 0.5
        
        # Return integer complexity
        return int(complexity)
