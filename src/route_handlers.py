from flask import render_template, jsonify, request
from langchain.memory import ConversationSummaryMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from src.helper import load_embedding, repo_ingestion, load_repo, function_class_chunker, get_repo_hash, remove_readonly
import os
import shutil
import re

# Global variables need to be defined at module level
qa = None
current_repo_hash = None
current_repo_path = None  # Add this line
embeddings = load_embedding()  # Preload embeddings

def setup_routes(app, persist_directory):
    global qa, current_repo_hash, current_repo_path

    # Setup LLM
    llm = ChatGroq(
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
- Include relevant code snippets from the context, formatted with triple backticks and the language (e.g., ````python`).
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
    custom_prompt = PromptTemplate(
        template=CUSTOM_PROMPT_TEMPLATE,
        input_variables=["context", "question"]
    )

    def initialize_vector_db(repo_url=None, repo_path=None):
        global qa, current_repo_hash, current_repo_path
        if qa is not None:
            qa = None
        memory = ConversationSummaryMemory(llm=llm, memory_key="chat_history", return_messages=True)
        try:
            if repo_url:
                repo_hash = get_repo_hash(repo_url)
                db_path = os.path.join(persist_directory, repo_hash, "faiss_index")
                current_repo_hash = repo_hash
                current_repo_path = repo_path  # Save the repo path globally
                if os.path.exists(db_path):
                    shutil.rmtree(os.path.join(persist_directory, repo_hash))
                if repo_path:
                    documents = load_repo(repo_path)
                    text_chunks = function_class_chunker(documents)
                    vectordb = FAISS.from_documents(documents=text_chunks, embedding=embeddings)  # Use preloaded embeddings
                    os.makedirs(os.path.dirname(db_path), exist_ok=True)
                    vectordb.save_local(db_path)
                else:
                    return {"status": "error", "message": "No repository path provided for new ingestion."}
            elif current_repo_hash:
                db_path = os.path.join(persist_directory, current_repo_hash, "faiss_index")
                if os.path.exists(db_path):
                    vectordb = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)  # Use preloaded embeddings
                else:
                    return {"status": "error", "message": "No existing vector DB found for current repository."}
            else:
                return {"status": "error", "message": "No repository URL or existing vector DB found."}
            qa = ConversationalRetrievalChain.from_llm(
                llm,
                retriever=vectordb.as_retriever(search_type="mmr", search_kwargs={"k": 8}),
                memory=memory,
                combine_docs_chain_kwargs={"prompt": custom_prompt}
            )
            return {"status": "success", "message": "Vector DB initialized successfully"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to initialize Vector DB: {str(e)}"}

    @app.route('/', methods=["GET", "POST"])
    def index():
        return render_template('index.html')

    @app.route('/chatbot', methods=["POST"])
    def gitRepo():
        global qa, current_repo_hash
        user_input = request.form['question']
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
                    return jsonify({"response": init_result["message"] if init_result["status"] == "success" else repo_result["message"]})
                return jsonify({"response": "Could not determine repository path. Please ingest a new repository."})
            return jsonify({"response": repo_result["message"]})
        init_result = initialize_vector_db(repo_url=user_input, repo_path=repo_result["repo_path"])
        return jsonify({"response": init_result["message"]})

    @app.route("/get", methods=["POST"])
    def chat():
        global qa, current_repo_hash, current_repo_path
        msg = request.form["msg"]
        if msg == "clear_chat":
            if qa:
                qa.memory.clear()
                return jsonify({"response": "", "type": "chat"})
            return jsonify({"response": "No chat history to clear.", "type": "chat"})
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
            return jsonify({"response": "", "type": "repo"})
        if not qa:
            return jsonify({"response": "Vector DB not initialized. Please ingest a repository first.", "type": "error"})
        result = qa(msg)
        return jsonify({"response": result["answer"], "type": "answer"})