import os
import re
import shutil
import uuid
import logging
from git import Repo
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers.language.language_parser import LanguageParser
from langchain.text_splitter import Language
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clone any GitHub repository with error handling
def repo_ingestion(repo_url):
    try:
        # Extract username and repo name from the URL
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
            glob="**/*.py",  # Ensure we only look for Python files recursively
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