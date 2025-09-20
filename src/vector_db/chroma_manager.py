import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
import json
from dotenv import load_dotenv
import os


load_dotenv()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR")
if not PERSIST_DIR:
    PERSIST_DIR = "analysis_output/chroma_db"
    print("[WARNING] CHROMA_PERSIST_DIR not set. Using default: analysis_output/chroma_db")

class ChromaManager:
    def __init__(self, persist_directory: str = PERSIST_DIR,intialize: bool=False):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        
        self.embedder=embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
        # Initialize collections
        if intialize:
            self.client.delete_collection("code_functions")
            self.client.delete_collection("code_issues")

            
        self.code_collection = self.client.get_or_create_collection(
            name="code_functions",
            metadata={"description": "Function-level code embeddings"},
            embedding_function=self.embedder
        )
        
        self.issues_collection = self.client.get_or_create_collection(
            name="code_issues",
            metadata={"description": "Code issue embeddings"},
            embedding_function=self.embedder
        )
    
    def add_code_functions(self, functions: List[Dict[str, Any]]):
        """Add function code to CodeDB"""
        if not functions:
            return
        
        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for i, func in enumerate(functions):
            # Create unique ID with index to avoid duplicates
            func_id = f"{func['file']}::{func.get('class', '')}::{func['function']}::{i}"
            func_id = func_id.replace('::', '::')  # Clean up double colons
            
            ids.append(func_id)
            documents.append(func['code'])
            
            # Prepare metadata (ChromaDB doesn't accept None values)
            metadata = {
                "file": func['file'],
                "class": func.get('class') or "",
                "function": func['function'],
                "start_line": func['start_line'],
                "end_line": func['end_line'],
                "parameters": json.dumps(func.get('parameters', [])),
                "function_length": func['function_length'],
                "nesting_depth": func['nesting_depth'],
                "has_docstring": func['has_docstring'],
                "calls": json.dumps(func.get('calls', [])),
                "imports": json.dumps(func.get('imports', [])),
                "parent_file": func['parent_file']
            }
            metadatas.append(metadata)
        
        # Add to collection
        self.code_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
    
    def add_issues(self, issues: List[Any]):
        """Add issues to IssuesDB"""
        if not issues:
            return
        
        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for i, issue in enumerate(issues):
            # Create unique ID with index to avoid duplicates
            issue_id = f"{issue.file}::{issue.class_name or ''}::{issue.function}::issue{i}"
            issue_id = issue_id.replace('::', '::')  # Clean up double colons
            
            ids.append(issue_id)
            
            # Create document from explanation and suggestion
            document = f"{issue.explanation} {issue.suggestion}"
            documents.append(document)
            
            # Prepare metadata (ChromaDB doesn't accept None values)
            metadata = {
                "file": issue.file,
                "class": issue.class_name or "",
                "function": issue.function,
                "category": issue.category,
                "issue": issue.issue,
                "severity": issue.severity,
                "lines": json.dumps(issue.lines)
            }
            metadatas.append(metadata)
        
        # Add to collection
        self.issues_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
    
    def search_code(self, query: str, n_results: int = 3, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search for code functions"""
        where_clause = {}
        if filters:
            for key, value in filters.items():
                if value is not None:
                    where_clause[key] = value
        
        results = self.code_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause if where_clause else None
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            result = {
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i]
            }
            formatted_results.append(result)
        
        return formatted_results
    
    def search_issues(self, query: str, n_results: int = 5, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search for code issues"""
        where_clause = {}
        if filters:
            for key, value in filters.items():
                if value is not None:
                    where_clause[key] = value
        
        results = self.issues_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause if where_clause else None
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            result = {
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i]
            }
            formatted_results.append(result)
        
        return formatted_results
    
    def get_function_by_id(self, func_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific function by ID"""
        results = self.code_collection.get(ids=[func_id])
        
        if results['ids']:
            return {
                'id': results['ids'][0],
                'document': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        
        return None
    
    def get_issues_by_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Get all issues for a specific file"""
        results = self.issues_collection.get(
            where={"file": file_path}
        )
        
        formatted_results = []
        for i in range(len(results['ids'])):
            result = {
                'id': results['ids'][i],
                'document': results['documents'][i],
                'metadata': results['metadatas'][i]
            }
            formatted_results.append(result)
        
        return formatted_results
    
    def get_issues_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """Get all issues with a specific severity"""
        results = self.issues_collection.get(
            where={"severity": severity}
        )
        
        formatted_results = []
        for i in range(len(results['ids'])):
            result = {
                'id': results['ids'][i],
                'document': results['documents'][i],
                'metadata': results['metadatas'][i]
            }
            formatted_results.append(result)
        
        return formatted_results
    
    def get_issues_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all issues in a specific category"""
        results = self.issues_collection.get(
            where={"category": category}
        )
        
        formatted_results = []
        for i in range(len(results['ids'])):
            result = {
                'id': results['ids'][i],
                'document': results['documents'][i],
                'metadata': results['metadatas'][i]
            }
            formatted_results.append(result)
        
        return formatted_results
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collections"""
        code_count = self.code_collection.count()
        issues_count = self.issues_collection.count()
        
        return {
            "code_functions": code_count,
            "issues": issues_count
        }
