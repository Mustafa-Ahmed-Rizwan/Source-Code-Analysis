import os
import re
import shutil
import hashlib
import logging
import ast
from git import Repo
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers.language.language_parser import LanguageParser
from langchain.text_splitter import Language
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
import stat

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clone any GitHub repository with error handling
def repo_ingestion(repo_url):
    try:
        match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", repo_url)
        if not match:
            return {"status": "error", "message": "Invalid GitHub URL format."}
        username, repo_name = match.group(1), match.group(2)
        repo_path = os.path.join(username, repo_name)
        if os.path.exists(repo_path):
            return {"status": "error", "message": f"Repository already exists at {repo_path}."}
        os.makedirs(repo_path, exist_ok=True)
        Repo.clone_from(repo_url, to_path=repo_path)
        return {"status": "success", "message": f"Repository cloned successfully to {repo_path}", "repo_path": repo_path}
    except Exception as e:
        return {"status": "error", "message": f"Failed to clone repository: {str(e)}"}

# Loading repositories as documents
def load_repo(repo_path):
    try:
        loader = GenericLoader.from_filesystem(
            repo_path,
            glob="**/*.py",
            suffixes=[".py"],
            parser=LanguageParser(language=Language.PYTHON, parser_threshold=500)
        )
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} documents from {repo_path}")
        if not documents:
            raise ValueError(f"No Python files found in {repo_path}.")
        return documents
    except Exception as e:
        logger.error(f"Error loading repository {repo_path}: {str(e)}")
        raise

# Creating text chunks
def text_splitter(documents):
    documents_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=2000,
        chunk_overlap=200
    )
    text_chunks = documents_splitter.split_documents(documents)
    logger.info(f"Created {len(text_chunks)} text chunks")
    return text_chunks

# Loading HuggingFace embedding model
def load_embedding():
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return embeddings

def function_class_chunker(documents, max_chunk_size=1800, overlap=200):
    """
    Splits Python code into function/class-level chunks with metadata.
    If a chunk is too large, further splits it using character-based splitting.
    """
    chunks = []
    for doc in documents:
        code = doc.page_content if hasattr(doc, "page_content") else doc
        file_path = doc.metadata.get("source", "unknown") if hasattr(doc, "metadata") else "unknown"
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start_line = node.lineno - 1
                    end_line = getattr(node, 'end_lineno', None)
                    if end_line is None:
                        end_line = node.body[-1].lineno if node.body else node.lineno
                    lines = code.splitlines()
                    chunk_code = "\n".join(lines[start_line:end_line])
                    metadata = {
                        "type": type(node).__name__,
                        "name": getattr(node, "name", ""),
                        "file": file_path,
                        "start_line": start_line + 1,
                        "end_line": end_line
                    }
                    if len(chunk_code) > max_chunk_size:
                        for i in range(0, len(chunk_code), max_chunk_size - overlap):
                            sub_chunk = chunk_code[i:i + max_chunk_size]
                            sub_metadata = metadata.copy()
                            sub_metadata["split"] = f"{i//(max_chunk_size - overlap) + 1}"
                            chunks.append({"content": sub_chunk, "metadata": sub_metadata})
                    else:
                        chunks.append({"content": chunk_code, "metadata": metadata})
        except Exception as e:
            logger.warning(f"AST parsing failed for {file_path}: {e}. Falling back to character split.")
            for i in range(0, len(code), max_chunk_size - overlap):
                chunk_code = code[i:i + max_chunk_size]
                metadata = {"type": "char_split", "file": file_path, "split": f"{i//(max_chunk_size - overlap) + 1}"}
                chunks.append({"content": chunk_code, "metadata": metadata})
    logger.info(f"Created {len(chunks)} function/class-level (hybrid) chunks")
    return [Document(page_content=chunk["content"], metadata=chunk["metadata"]) for chunk in chunks]

def get_repo_hash(repo_url):
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", repo_url)
    if match:
        _, repo_name = match.groups()
        return repo_name
    return hashlib.md5(repo_url.encode()).hexdigest()

def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)