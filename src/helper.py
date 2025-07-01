import os
import re
import shutil
import hashlib
import logging
import ast
import glob
from git import Repo
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers.language.language_parser import LanguageParser
from langchain.text_splitter import Language
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
import stat
from pycparser import CParser, parse_file
import clang.cindex  # Added import for libclang
from bs4 import BeautifulSoup
import tinycss2

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
        # Load Python, C, and C++ files with LanguageParser
        loaders = [
            GenericLoader.from_filesystem(
                repo_path,
                glob="**/*.py",
                suffixes=[".py"],
                parser=LanguageParser(language=Language.PYTHON, parser_threshold=500)
            ),
            GenericLoader.from_filesystem(
                repo_path,
                glob="**/*.c",
                suffixes=[".c"],
                parser=LanguageParser(language=Language.C, parser_threshold=500)
            ),
            GenericLoader.from_filesystem(
                repo_path,
                glob="**/*.h",
                suffixes=[".h"],
                parser=LanguageParser(language=Language.C, parser_threshold=500)
            ),
            GenericLoader.from_filesystem(
                repo_path,
                glob="**/*.cpp",
                suffixes=[".cpp"],
                parser=LanguageParser(language=Language.CPP, parser_threshold=500)
            ),
            GenericLoader.from_filesystem(
                repo_path,
                glob="**/*.hpp",
                suffixes=[".hpp"],
                parser=LanguageParser(language=Language.CPP, parser_threshold=500)
            )
        ]
        documents = []
        for loader in loaders:
            docs = loader.load()
            documents.extend(docs)

        # Manually load and parse HTML files
        for html_file in glob.glob(os.path.join(repo_path, "**/*.html"), recursive=True):
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
                soup = BeautifulSoup(content, 'html.parser')
                doc = Document(
                    page_content=str(soup.prettify()),
                    metadata={"source": html_file, "type": "HTML_Document"}
                )
                documents.append(doc)

        # Manually load and parse CSS files
        for css_file in glob.glob(os.path.join(repo_path, "**/*.css"), recursive=True):
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
                rules = list(tinycss2.parse_stylesheet(content, skip_comments=True))
                doc = Document(
                    page_content="\n".join(str(rule) for rule in rules),
                    metadata={"source": css_file, "type": "CSS_Rule"}
                )
                documents.append(doc)

        logger.info(f"Loaded {len(documents)} documents (Python, C, C++, HTML, CSS) from {repo_path}")
        if not documents:
            raise ValueError(f"No supported files found in {repo_path}.")
        return documents
    except Exception as e:
        logger.error(f"Error loading repository {repo_path}: {str(e)}")
        raise

# Creating text chunks
def text_splitter(documents):
    documents_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,  # Default to PYTHON, adjust for C if needed
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
    Splits Python, C, C++, HTML, and CSS code into function/class or logical chunks with metadata.
    If a chunk is too large, further splits it using character-based splitting.
    """
    chunks = []
    for doc in documents:
        code = doc.page_content if hasattr(doc, "page_content") else doc
        file_path = doc.metadata.get("source", "unknown") if hasattr(doc, "metadata") else "unknown"
        file_extension = os.path.splitext(file_path)[1].lower()
        try:
            if file_extension == ".py":
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
            elif file_extension == ".c":
                parser = CParser()
                tree = parser.parse(code)
                for node in ast.walk(tree):
                    if hasattr(node, 'coord'):
                        start_line = node.coord.line - 1
                        end_line = node.coord.line
                        lines = code.splitlines()
                        chunk_code = "\n".join(lines[start_line:end_line])
                        metadata = {
                            "type": node.__class__.__name__,
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
            elif file_extension == ".h":
                parser = CParser()
                tree = parser.parse(code)
                for node in ast.walk(tree):
                    if hasattr(node, 'coord'):
                        start_line = node.coord.line - 1
                        end_line = node.coord.line
                        lines = code.splitlines()
                        chunk_code = "\n".join(lines[start_line:end_line])
                        metadata = {
                            "type": node.__class__.__name__,
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
            elif file_extension in [".cpp", ".hpp"]:
                index = clang.cindex.Index.create()
                tu = index.parse(file_path)
                for node in tu.cursor.walk_preorder():
                    if node.location.file and os.path.abspath(node.location.file.name) == os.path.abspath(file_path):
                        if node.kind in (
                            clang.cindex.CursorKind.FUNCTION_DECL,
                            clang.cindex.CursorKind.CXX_METHOD,
                            clang.cindex.CursorKind.CLASS_DECL
                        ):
                            start_line = node.extent.start.line - 1
                            end_line = node.extent.end.line
                            with open(file_path, 'r') as f:
                                lines = f.readlines()
                                chunk_code = "".join(lines[start_line:end_line]).strip()
                            metadata = {
                                "type": node.kind.name,
                                "name": node.spelling,
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
            elif "type" in doc.metadata and doc.metadata["type"] == "HTML_Document":
                chunk_code = doc.page_content
                metadata = {
                    "type": "HTML_Document",
                    "name": os.path.basename(doc.metadata["source"]),
                    "file": doc.metadata["source"],
                    "start_line": 1,
                    "end_line": len(chunk_code.splitlines())
                }
                if len(chunk_code) > max_chunk_size:
                    for i in range(0, len(chunk_code), max_chunk_size - overlap):
                        sub_chunk = chunk_code[i:i + max_chunk_size]
                        sub_metadata = metadata.copy()
                        sub_metadata["split"] = f"{i//(max_chunk_size - overlap) + 1}"
                        chunks.append({"content": sub_chunk, "metadata": sub_metadata})
                else:
                    chunks.append({"content": chunk_code, "metadata": metadata})
            elif "type" in doc.metadata and doc.metadata["type"] == "CSS_Rule":
                chunk_code = doc.page_content
                metadata = {
                    "type": "CSS_Rule",
                    "name": os.path.basename(doc.metadata["source"]),
                    "file": doc.metadata["source"],
                    "start_line": 1,
                    "end_line": len(chunk_code.splitlines())
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
            logger.warning(f"Parsing failed for {file_path}: {e}. Falling back to character split.")
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