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

def setup_routes(app, persist_directory):
    global qa, current_repo_hash

    # Setup LLM
    llm = ChatGroq(
        model="llama3-8b-8192",
        temperature=0.5,
        max_tokens=512,
        timeout=10,
        max_retries=2
    )

    # Custom prompt template for code Q&A
    CUSTOM_PROMPT_TEMPLATE = """
    You are an expert code assistant with a professional and clear communication style. Your task is to analyze the provided context from the codebase and answer the user's question in well-structured Markdown format. Follow these guidelines:

- Use proper Markdown headings (e.g., `## Heading`, `### Subheading`) to organize the response into sections.
- Use paragraphs for detailed explanations, ensuring each paragraph focuses on a single key point.
- When listing items, use Markdown bullet points with a consistent format (e.g., `- Item: Description`).
- Include relevant code snippets from the context when they help clarify the answer, formatting them with triple backticks (``````) and specify the language (e.g., ````python` or ````sql`) for syntax highlighting.
- Maintain a logical order: start with an overview under a `## Overview` heading, provide details or steps under a `## Details` or `## Steps` heading, and conclude with a summary or next steps under a `## Summary` heading if applicable.
- If the answer is not found in the context, respond with: `## Answer\nI don't know based on the provided context.`
- Avoid making up information, speculation, or small talk; focus solely on technical accuracy and relevance.

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
        global qa, current_repo_hash
        if qa is not None:
            qa = None
        memory = ConversationSummaryMemory(llm=llm, memory_key="chat_history", return_messages=True)
        try:
            if repo_url:
                repo_hash = get_repo_hash(repo_url)
                db_path = os.path.join(persist_directory, repo_hash, "faiss_index")
                current_repo_hash = repo_hash
                if os.path.exists(db_path):
                    shutil.rmtree(os.path.join(persist_directory, repo_hash))
                if repo_path:
                    documents = load_repo(repo_path)
                    text_chunks = function_class_chunker(documents)
                    vectordb = FAISS.from_documents(documents=text_chunks, embedding=load_embedding())
                    os.makedirs(os.path.dirname(db_path), exist_ok=True)
                    vectordb.save_local(db_path)
                else:
                    return {"status": "error", "message": "No repository path provided for new ingestion."}
            elif current_repo_hash:
                db_path = os.path.join(persist_directory, current_repo_hash, "faiss_index")
                if os.path.exists(db_path):
                    vectordb = FAISS.load_local(db_path, load_embedding(), allow_dangerous_deserialization=True)
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
                        shutil.rmtree(os.path.join(persist_directory, repo_hash))
                    init_result = initialize_vector_db(repo_url=user_input, repo_path=repo_path)
                    return jsonify({"response": init_result["message"] if init_result["status"] == "success" else repo_result["message"]})
                return jsonify({"response": "Could not determine repository path. Please ingest a new repository."})
            return jsonify({"response": repo_result["message"]})
        init_result = initialize_vector_db(repo_url=user_input, repo_path=repo_result["repo_path"])
        return jsonify({"response": init_result["message"]})

    @app.route("/get", methods=["POST"])
    def chat():
        global qa, current_repo_hash
        msg = request.form["msg"]
        if msg == "clear_repo":
            if current_repo_hash and os.path.exists(os.path.join(persist_directory, current_repo_hash)):
                shutil.rmtree(os.path.join(persist_directory, current_repo_hash), onerror=remove_readonly)
            import glob
            repo_dirs = glob.glob(f"*/{current_repo_hash}")
            for repo_dir in repo_dirs:
                if os.path.exists(repo_dir):
                    shutil.rmtree(repo_dir, onerror=remove_readonly)
            qa = None
            cleared_repo = current_repo_hash
            current_repo_hash = None
            return jsonify({"response": f"Repository '{cleared_repo}' and its vector DB cleared successfully.", "type": "repo"})
        if msg == "clear_chat":
            if qa:
                qa.memory.clear()
                return jsonify({"response": "Chat history cleared for this repository.", "type": "chat"})
            return jsonify({"response": "No chat history to clear.", "type": "chat"})
        if not qa:
            return jsonify({"response": "Vector DB not initialized. Please ingest a repository first.", "type": "error"})
        result = qa(msg)
        return jsonify({"response": result["answer"], "type": "answer"})