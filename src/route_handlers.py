# src/route_handlers.py
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse, HTMLResponse
import os
import shutil
import re
from src.helper import repo_ingestion, load_repo, function_class_chunker, get_repo_hash, remove_readonly
from pydantic import BaseModel
from typing import Optional

# Global variables
qa = None
current_repo_hash = None
current_repo_path = None
_embeddings = None

class ChatRequest(BaseModel):
    msg: str

class RepoRequest(BaseModel):
    question: str

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embeddings

def setup_routes(app, persist_directory):
    global qa, current_repo_hash, current_repo_path

    def load_llm():
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama3-70b-8192",
            temperature=0.5,
            max_tokens=512,
            timeout=10,
            max_retries=2
        )

    # Custom prompt template for code Q&A
    CUSTOM_PROMPT_TEMPLATE = """
    You are an expert code assistant with a professional and clear communication style. Your task is to analyze the provided context from the codebase and answer the user's question in well-structured Markdown format. Follow these guidelines:

- Use proper Markdown headings (e.g., `## Overview`, `## Details`, `## Summary`) to organize the response.
- Start with a `## Overview` summarizing the main point.
- In `## Details`, provide step-by-step explanations, referencing filenames and line numbers if available.
- When listing items, use Markdown bullet points with a consistent format (e.g., `- Item: Description`).
- Include relevant code snippets from the context, formatted with triple backticks and the language (e.g., ```python).
- For warnings, errors, or important notes, use blockquotes (`>`) or bold text.
- If you make any assumptions, list them under an `## Assumptions` section if there are none then output this heading.
- If the answer is not found in the context, respond with:  
  `## Answer`  
  I don't know based on the provided context.
- Avoid speculation or small talk; focus solely on technical accuracy and relevance.
- End with a `## Summary` or `## Next Steps` section, providing a concise recap or actionable advice.

Context:
{context}

Question:
{question}

Provide the answer in clear, simple language with a professional tone, formatted entirely in Markdown.
    """

    def initialize_vector_db(repo_url=None, repo_path=None):
        global qa, current_repo_hash, current_repo_path
        from langchain.memory import ConversationSummaryMemory
        from langchain.chains import ConversationalRetrievalChain
        from langchain_community.vectorstores import FAISS
        from langchain_core.prompts import PromptTemplate

        if qa is not None:
            qa = None
        llm = load_llm()
        memory = ConversationSummaryMemory(llm=llm, memory_key="chat_history", return_messages=True)
        try:
            embeddings = get_embeddings()
            if repo_url:
                repo_hash = get_repo_hash(repo_url)
                db_path = os.path.join(persist_directory, repo_hash, "faiss_index")
                current_repo_hash = repo_hash
                current_repo_path = repo_path
                if os.path.exists(db_path):
                    shutil.rmtree(os.path.join(persist_directory, repo_hash), onerror=remove_readonly)
                if repo_path:
                    documents = load_repo(repo_path)
                    text_chunks = function_class_chunker(documents)
                    vectordb = FAISS.from_documents(documents=text_chunks, embedding=embeddings)
                    os.makedirs(os.path.dirname(db_path), exist_ok=True)
                    vectordb.save_local(db_path)
                else:
                    return {"status": "error", "message": "No repository path provided for new ingestion."}
            elif current_repo_hash:
                db_path = os.path.join(persist_directory, current_repo_hash, "faiss_index")
                if os.path.exists(db_path):
                    vectordb = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
                else:
                    return {"status": "error", "message": "No existing vector DB found for current repository."}
            else:
                return {"status": "error", "message": "No repository URL or existing vector DB found."}
            qa = ConversationalRetrievalChain.from_llm(
                llm,
                retriever=vectordb.as_retriever(search_type="mmr", search_kwargs={"k": 8}),
                memory=memory,
                combine_docs_chain_kwargs={"prompt": PromptTemplate(
                    template=CUSTOM_PROMPT_TEMPLATE,
                    input_variables=["context", "question"]
                )}
            )
            return {"status": "success", "message": "Vector DB initialized successfully"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to initialize Vector DB: {str(e)}"}

    # Create API router
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index():
        # Simple HTML response for testing
        return """
        <html>
            <head>
                <title>Repository Chat API</title>
            </head>
            <body>
                <h1>Repository Chat API</h1>
                <p>FastAPI backend is running!</p>
                <p>Use the mobile app to interact with this API.</p>
            </body>
        </html>
        """

    @router.post("/api/repository")
    async def ingest_repository(request: RepoRequest):
        global qa, current_repo_hash
        user_input = request.question
        repo_result = repo_ingestion(user_input)
        
        if repo_result["status"] == "error":
            if "Repository already exists" in repo_result["message"]:
                match = re.search(r"at (.+)", repo_result["message"])
                repo_path = match.group(1) if match else None
                if repo_path:
                    repo_hash = get_repo_hash(user_input)
                    old_db_path = os.path.join(persist_directory, repo_hash, "faiss_index")
                    if os.path.exists(old_db_path):
                        shutil.rmtree(os.path.join(persist_directory, repo_hash), onerror=remove_readonly)
                    init_result = initialize_vector_db(repo_url=user_input, repo_path=repo_path)
                    return {"response": init_result["message"] if init_result["status"] == "success" else repo_result["message"]}
                return {"response": "Could not determine repository path. Please ingest a new repository."}
            return {"response": repo_result["message"]}
        
        init_result = initialize_vector_db(repo_url=user_input, repo_path=repo_result["repo_path"])
        return {"response": init_result["message"]}

    @router.post("/api/chat")
    async def chat(request: ChatRequest):
        global qa, current_repo_hash, current_repo_path
        msg = request.msg
        
        if msg == "clear_chat":
            if qa:
                qa.memory.clear()
                return {"response": "", "type": "chat"}
            return {"response": "No chat history to clear.", "type": "chat"}
        
        if msg in ("new_chat", "clear_repo"):
            if current_repo_hash:
                repo_dir = os.path.join(persist_directory, current_repo_hash)
                if os.path.exists(repo_dir):
                    shutil.rmtree(repo_dir, onerror=remove_readonly)
            if current_repo_path and os.path.exists(current_repo_path):
                shutil.rmtree(current_repo_path, onerror=remove_readonly)
            qa = None
            current_repo_hash = None
            current_repo_path = None
            return {"response": "", "type": "repo"}
        
        if not qa:
            return {"response": "Vector DB not initialized. Please ingest a repository first.", "type": "error"}
        
        try:
            result = qa(msg)
            return {"response": result["answer"], "type": "answer"}
        except Exception as e:
            return {"response": f"Error processing chat: {str(e)}", "type": "error"}

    @router.get("/api/health")
    async def health_check():
        return {"status": "healthy", "message": "API is running"}

    # Include router in the app
    app.include_router(router)