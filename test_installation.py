#!/usr/bin/env python3
"""
Test script to verify the code analyzer installation and basic functionality
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported"""
    try:
        from src.parsers.tree_sitter_parser import TreeSitterParser
        from src.analyzers.local_analyzer import LocalAnalyzer
        from src.analyzers.global_analyzer import GlobalAnalyzer
        from src.vector_db.chroma_manager import ChromaManager
        from src.visualization.graph_visualizer import GraphVisualizer
        from src.qa_agent.semantic_search import SemanticSearchAgent
        from src.pipeline.analyzer import CodeAnalyzer
        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_parser():
    """Test the tree-sitter parser"""
    try:
        from src.parsers.tree_sitter_parser import TreeSitterParser
        parser = TreeSitterParser()
        
        # Test with a simple Python function
        test_code = '''
def hello_world():
    """A simple hello world function"""
    print("Hello, World!")
    return "success"
'''
        
        # Create a temporary test file
        test_file = "test_function.py"
        with open(test_file, 'w') as f:
            f.write(test_code)
        
        try:
            functions = parser.parse_file(test_file)
            if functions and len(functions) > 0:
                func = functions[0]
                assert func['function'] == 'hello_world'
                assert func['has_docstring'] == True
                assert 'print' in func['calls']
                print("✓ Parser test passed")
                return True
            else:
                print("✗ Parser test failed: No functions found")
                return False
        finally:
            # Clean up test file
            if os.path.exists(test_file):
                os.remove(test_file)
                
    except Exception as e:
        print(f"✗ Parser test failed: {e}")
        return False

def test_analyzer():
    """Test the local analyzer"""
    try:
        from src.analyzers.local_analyzer import LocalAnalyzer
        analyzer = LocalAnalyzer()
        
        # Test function data
        func_data = {
            'file': 'test.py',
            'class': None,
            'function': 'test_func',
            'start_line': 1,
            'end_line': 10,
            'code': 'def test_func():\n    eval("print(1)")\n    return True',
            'function_length': 10,
            'nesting_depth': 1,
            'has_docstring': False,
            'calls': ['eval'],
            'imports': [],
            'parent_file': 'test.py'
        }
        
        issues = analyzer.analyze_function(func_data)
        
        # Should find eval usage issue
        eval_issues = [issue for issue in issues if 'eval' in issue.issue.lower()]
        if eval_issues:
            print("✓ Analyzer test passed")
            return True
        else:
            print("✗ Analyzer test failed: No eval issue detected")
            return False
            
    except Exception as e:
        print(f"✗ Analyzer test failed: {e}")
        return False

def test_cli():
    """Test CLI help command"""
    try:
        import subprocess
        result = subprocess.run([sys.executable, '-m', 'src.cli', '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'analyze' in result.stdout:
            print("✓ CLI test passed")
            return True
        else:
            print("✗ CLI test failed: CLI not working properly")
            return False
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Code Analyzer Installation")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("Parser Test", test_parser),
        ("Analyzer Test", test_analyzer),
        ("CLI Test", test_cli)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"  {test_name} failed")
    
    print("\n" + "=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Installation is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the installation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
