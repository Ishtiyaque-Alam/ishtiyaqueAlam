from setuptools import setup, find_packages

setup(
    name="code-analyzer",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "tree-sitter>=0.20.0",
        "tree-sitter-python>=0.20.0", 
        "tree-sitter-javascript>=0.20.0",
        "tree-sitter-java>=0.20.0",
        "chromadb>=0.4.0",
        "sentence-transformers>=2.2.0",
        "networkx>=3.0",
        "pyvis>=0.3.0",
        "plotly>=5.0.0",
        "click>=8.0.0",
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "tqdm>=4.60.0"
    ],
    entry_points={
        "console_scripts": [
            "qa-agent=src.cli:main",
        ],
    },
)
