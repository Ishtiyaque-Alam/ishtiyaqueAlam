# Code Analysis Pipeline with Vector Search

A comprehensive Python pipeline that parses code, detects issues, generates reports, stores results in vector databases, and enables dependency-aware semantic search.

## Features

- **Multi-language Support**: Python, JavaScript, Java parsing with Tree-sitter
- **Comprehensive Issue Detection**: Security, complexity, documentation, and duplication analysis
- **Vector Database Storage**: ChromaDB for semantic search of code and issues
- **Dependency Graph Analysis**: NetworkX-based dependency visualization
- **Interactive Visualizations**: HTML-based interactive graphs and reports
- **Semantic Search**: Natural language queries with context-aware responses

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install the package:
```bash
pip install -e .
```

## Usage

### Command Line Interface

#### Analyze Code
```bash
qa-agent analyze <path_to_code>
```

Options:
- `--output-dir, -o`: Output directory for results (default: ./analysis_output)

### Example Usage

1. **Analyze a Python project**:
```bash
qa-agent analyze ./my_project
```

2. **Analyze with custom output directory**:
```bash
qa-agent analyze ./my_project -o ./reports
```

3. **Analyze current directory**:
```bash
qa-agent analyze .
```

## Output Files

The analysis generates several output files:

- `chunks.json`: Parsed function-level code chunks with metadata
- `issues.json`: Detected issues with details
- `report.json`: Enriched report with full context
- `graph.html`: Interactive dependency graph visualization
- `summary_report.html`: Summary report with statistics
- `chroma_db/`: Vector database storage for semantic search

## Issue Categories

### Security Issues
- `eval`/`exec` usage
- SQL injection risks
- Weak cryptographic hashes (MD5, SHA1)
- Hardcoded secrets

### Complexity Issues
- Function length (>200 lines)
- Cyclomatic complexity (>10)
- Excessive nesting depth (>3)

### Documentation Issues
- Missing docstrings for public functions
- Incomplete documentation

### Duplication Issues
- Duplicate functions across files
- Code similarity detection

## Severity Levels

- **High**: Exploitable security risks, extreme complexity
- **Medium**: Performance/maintainability issues
- **Low**: Documentation/style issues

## File Exclusions

The analyzer automatically excludes common non-source files and directories to focus on actual code:

### Default Exclusions

**File Patterns:**
- Build artifacts: `*.pyc`, `*.pyo`, `*.so`, `*.dll`, `*.exe`, `*.jar`
- IDE files: `*.swp`, `*.swo`, `*~`, `.DS_Store`
- Documentation: `*.md`, `*.txt`, `*.rst`, `*.pdf`
- Config files: `*.ini`, `*.cfg`, `*.json`, `*.yaml`
- Log files: `*.log`, `*.out`, `*.err`
- Temporary files: `*.tmp`, `*.bak`, `*.orig`

**Directories:**
- Build dirs: `__pycache__`, `node_modules`, `build`, `dist`, `target`
- IDE dirs: `.vscode`, `.idea`, `.git`
- Environment: `venv`, `env`, `.env`

### Customizing Exclusions

You can customize exclusions in several ways:

1. **Command line options:**
```bash
# Exclude specific patterns
qa-agent analyze ./project -e "*.pyc" -e "*.log"

# Exclude specific directories  
qa-agent analyze ./project -d "build" -d "tests"

# Include test files
qa-agent analyze ./project --include-tests
```

2. **Programmatic configuration:**
```python
from src.pipeline.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer(
    exclude_patterns=['*.pyc', '*.log', 'test_*'],
    exclude_dirs=['build', 'dist', 'tests']
)
```

3. **Configuration file:**
See `exclusion_config_example.py` for detailed examples.

## Architecture

```
src/
├── parsers/           # Tree-sitter based code parsing
├── analyzers/         # Local and global issue analysis
├── vector_db/         # ChromaDB integration
├── visualization/     # Graph and report generation
├── qa_agent/         # Semantic search and Q&A
├── pipeline/         # Main analysis orchestrator
└── cli.py           # Command-line interface
```

## Dependencies

- **tree-sitter**: Multi-language code parsing
- **chromadb**: Vector database for semantic search
- **sentence-transformers**: Text embeddings (all-MiniLM-L6-v4)
- **networkx**: Dependency graph analysis
- **pyvis**: Interactive graph visualization
- **click**: CLI interface

## Examples

### Security Analysis
```bash
qa-agent query "What security vulnerabilities exist in the authentication code?"
```

### Performance Analysis
```bash
qa-agent query "Which functions have high complexity and need refactoring?"
```

### Code Search
```bash
qa-agent query "How does user authentication work?"
```

### Duplication Detection
```bash
qa-agent query "Are there any duplicate database query functions?"
```

## Interactive Mode

The interactive mode allows for continuous querying:

```bash
qa-agent analyze ./project --interactive
```

This will:
1. Run the full analysis
2. Start an interactive session where you can ask questions
3. Provide context-aware answers with code references

## Customization

You can extend the analysis by:

1. **Adding new issue detectors** in `src/analyzers/local_analyzer.py`
2. **Implementing new languages** in `src/parsers/tree_sitter_parser.py`
3. **Creating custom visualizations** in `src/visualization/`
4. **Adding new query types** in `src/qa_agent/semantic_search.py`

## License

MIT License
