🔹 Install pyenv-win

Install via PowerShell:
```bash
Invoke-WebRequest -UseBasicParsing -Uri https://pyenv-win.github.io/pyenv-win/install.ps1 | Invoke-Expression
```

(or follow pyenv-win docs
)

Restart PowerShell, then check:

pyenv --version

🔹 Install and set Python 3.11.9(or lower) for your project
```bash
pyenv install 3.11.9
cd <your destination folder>
pyenv local 3.11.9
```


This creates a .python-version file (you can commit it to your repo).

Create & activate venv

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
# Code Analysis Pipeline with Vector Search


A comprehensive Python pipeline that parses code, detects issues, generates reports, stores results in vector databases, and enables dependency-aware semantic search.

## Features

- **Multi-language Support**: Python, JavaScript, Java parsing with Tree-sitter
- **Comprehensive Issue Detection**: Security, complexity, documentation, and duplication analysis
- **Vector Database Storage**: ChromaDB for semantic search of code and issues
- **Dependency Graph Analysis**: NetworkX-based dependency visualization With Issues
- **Interactive Visualizations**: HTML-based interactive graphs and reports(DashBoard)
- **Semantic Search**: Natural language queries with context-aware responses
- **GitHub Analyser**: Analyze a Repository Directly from Web, by pasting the {Owner_name}/repository
- **QA Bot**:Ask Questions about the codeBase with smart context switch to prevent unnecessary Retrievals
- **Debugger Agent**- an AI agent based on Planner Design for comprehensive bebugging and modification in the codeBase-Use the  keyword 'think' in the Chat
- **Interactive LightWeight UI**- Built using Jinja2 and XHTML and fastAPI to interact with the Bot in Web
- **Comprehensive Report of Issues**- Prepares a markdown Report with the Issues, explanation and Fix
- **CLI design**- Interactive CLI design build using typher and Click

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
To Analyze a folder
```bash
python -m src.cli analyze <Repo_location>
```
To Chat with the Bot
```bash
python -m src.cli chat
```
To analyze a Repository on Github
```bash
python -m src.cli github <Repo Owner/Repo Name>
```
## Output Files

The analysis generates several output files(Go to Analysis_output):

- `chunks.json`: Parsed function-level code chunks with metadata
- `issues.json`: Detected issues with details
- `report.json`: Enriched report with full context
- `graph.html`: Interactive dependency graph visualization
- `summary_report.html`: Summary report with statistics(DashBoard)
- `chroma_db/`: Vector database storage for semantic search
- `Report.md/`: Final Generated Report With Issues and Fix and Location
e
## Issue Categories

### Security Issues
Python
- `eval`/`exec` usage
- SQL injection risks
- Weak cryptographic hashes (MD5, SHA1)
- Hardcoded secrets(api_key, password, token, etc.)

JavaScript

- Use of eval()
- Use of new Function()
- Dangerous DOM writes (.innerHTML =, document.write())

Java
- Use of Runtime.getRuntime().exec()
- Weak cryptography (MessageDigest.getInstance("MD5"/"SHA1"))
- SQL injection via JDBC string concatenation (Statement.execute("..."+var))
### Complexity Issues
- Function length (>200 lines)
- Cyclomatic complexity (>10)
- Excessive nesting depth (>3)

### Documentation Issues
- Missing docstrings for public functions
- Incomplete documentation
Java
- Function with no Javadoc (/** ... */).
JavaScript
- Function with no JSDoc (/** ... */).

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
frontend               #Interactive UI to interact from a WebUI
Main.py                #Contains the FastAPI to run the surver
src/
├── parsers/           # Tree-sitter based code parsing
├── analyzers/         # Local and global issue analysis
├── vector_db/         # ChromaDB integration
├── visualization/     # Graph and report generation With issues annotated 
├── qa_agent/         # Semantic search and Q&A with Smart Debugger Agent Support
├── pipeline/         # Main analysis orchestrator
└── github_analyser   # To analyise a repository directly from the github 

```

## Dependencies

- **tree-sitter**: Multi-language code parsing
- **chromadb**: Vector database for semantic search
- **sentence-transformers**: Text embeddings (all-MiniLM-L6-v4)
- **networkx**: Dependency graph analysis
- **pyvis**: Interactive graph visualization
- **click  and Typher**: CLI interface
- **FastAPI**: For interaction on WebUI
- **JINJA2, XHTML, TailWind CSS**: For frontend Design
- **LangChain**: For Agentic AI design
- **Google genai**: For LLM support - Gemini-2.5-flash

## Customization

You can extend the analysis by:

1. **Adding new issue detectors** in `src/analyzers/local_analyzer.py`
2. **Implementing new languages** in `src/parsers/tree_sitter_parser.py`
3. **Creating custom visualizations** in `src/visualization/`
4. **Adding new query types** in `src/qa_agent/semantic_search.py`

## License

MIT License
