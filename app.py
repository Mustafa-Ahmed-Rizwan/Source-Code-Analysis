from dotenv import load_dotenv
import os
import logging
import shutil
import hashlib
from flask import Flask, render_template, jsonify, request
from langchain.memory import ConversationSummaryMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from src.helper import load_embedding, repo_ingestion, load_repo, text_splitter

app = Flask(__name__)

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
GROQ_MODEL = "llama3-8b-8192"  # Updated model due to token limit

embeddings = load_embedding()
persist_directory = "db"

# Global QA chain and current repo index
qa = None
current_repo_hash = None

# Setup LLM
llm = ChatGroq(
    model=GROQ_MODEL,
    temperature=0.5,
    max_tokens=512,
    timeout=10,
    max_retries=2
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom prompt template for code Q&A
CUSTOM_PROMPT_TEMPLATE = """
You are an expert code assistant. Use ONLY the information provided in the context below to answer the user's question about the codebase.
If the answer is not present in the context, reply with "I don't know based on the provided context."
Do NOT make up answers or provide information not found in the context.
If helpful, reference code snippets or filenames from the context.

Context:
{context}

Question:
{question}

Answer in clear, simple language. Focus on technical accuracy and avoid small talk.
"""
custom_prompt = PromptTemplate(
    template=CUSTOM_PROMPT_TEMPLATE,
    input_variables=["context", "question"]
)

def get_repo_hash(repo_url):
    # Use repo name instead of full URL hash for simpler indexing
    import re
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", repo_url)
    if match:
        _, repo_name = match.groups()
        return repo_name
    return hashlib.md5(repo_url.encode()).hexdigest()

def initialize_vector_db(repo_url=None, repo_path=None):
    global qa, current_repo_hash
    # Clear existing memory and qa to ensure no old context persists
    if qa is not None:
        logger.info("Clearing existing QA chain")
    qa = None
    memory = ConversationSummaryMemory(llm=llm, memory_key="chat_history", return_messages=True)
    try:
        if repo_url:
            repo_hash = get_repo_hash(repo_url)
            db_path = os.path.join(persist_directory, repo_hash, "faiss_index")
            current_repo_hash = repo_hash
            logger.info(f"Initializing vector DB for repository {repo_url} with hash {repo_hash}")
            # Remove existing index for this repo if it exists
            if os.path.exists(db_path):
                shutil.rmtree(os.path.join(persist_directory, repo_hash))
                logger.info(f"Removed existing index at {db_path}")
            if repo_path:
                documents = load_repo(repo_path)
                text_chunks = text_splitter(documents)
                vectordb = FAISS.from_documents(documents=text_chunks, embedding=embeddings)
                # Persist the FAISS DB to disk
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                vectordb.save_local(db_path)
                logger.info(f"Saved new faiss_index with {len(text_chunks)} chunks for {repo_url}")
            else:
                return {"status": "error", "message": "No repository path provided for new ingestion."}
        elif current_repo_hash:
            db_path = os.path.join(persist_directory, current_repo_hash, "faiss_index")
            if os.path.exists(db_path):
                logger.info(f"Loading existing vector DB from {db_path}")
                vectordb = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
            else:
                return {"status": "error", "message": "No existing vector DB found for current repository."}
        else:
            return {"status": "error", "message": "No repository URL or existing vector DB found."}
        # Initialize QA chain with new memory
        qa = ConversationalRetrievalChain.from_llm(
            llm,
            retriever=vectordb.as_retriever(search_type="mmr", search_kwargs={"k": 8}),
            memory=memory,
            combine_docs_chain_kwargs={"prompt": custom_prompt}
        )
        logger.info("QA chain initialized successfully with vectordb containing %d documents", len(vectordb.docstore._dict))
        return {"status": "success", "message": "Vector DB initialized successfully"}
    except Exception as e:
        logger.error(f"Failed to initialize Vector DB: {str(e)}")
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
            import re
            match = re.search(r"at (.+)", repo_result["message"])
            repo_path = match.group(1) if match else None
            if repo_path:
                # Remove old index and reinitialize
                repo_hash = get_repo_hash(user_input)
                old_db_path = os.path.join(persist_directory, repo_hash, "faiss_index")
                if os.path.exists(old_db_path):
                    shutil.rmtree(os.path.join(persist_directory, repo_hash))
                init_result = initialize_vector_db(repo_url=user_input, repo_path=repo_path)
                return jsonify({"response": init_result["message"] if init_result["status"] == "success" else repo_result["message"]})
            else:
                return jsonify({"response": "Could not determine repository path. Please ingest a new repository."})
        return jsonify({"response": repo_result["message"]})
    init_result = initialize_vector_db(repo_url=user_input, repo_path=repo_result["repo_path"])
    if init_result["status"] == "success" and qa is None:
        logger.error("QA chain not initialized after successful vector DB initialization")
    return jsonify({"response": init_result["message"]})

@app.route("/get", methods=["POST"])
def chat():
    global qa, current_repo_hash
    msg = request.form["msg"]
    if msg == "clear":
        os.system("rm -rf repo")
        if os.path.exists(persist_directory):
            shutil.rmtree(persist_directory)
        qa = None
        current_repo_hash = None
        return jsonify({"response": "Repository and vector DB cleared."})
    if not qa:
        logger.error("QA chain is None when processing chat request")
        return jsonify({"response": "Vector DB not initialized. Please ingest a repository first."})
    logger.info("Processing chat request with message: %s for repo hash %s", msg, current_repo_hash)
    result = qa(msg)
    return jsonify({"response": result["answer"]})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)