from dotenv import load_dotenv
import os
import logging
import shutil
import threading  # Add this import
from flask import Flask
from src.route_handlers import setup_routes
from src.helper import load_embedding  # Add this import

app = Flask(__name__)

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global QA chain and current repo index
qa = None
current_repo_hash = None
persist_directory = "db"

embeddings = load_embedding()  # Preload embeddings during startup
initial_load_thread = None

# Setup routes
setup_routes(app, persist_directory)

if __name__ == '__main__':
    # Start embedding loading in a separate thread
    initial_load_thread = threading.Thread(target=load_embedding, daemon=True)
    initial_load_thread.start()
    app.run(host="0.0.0.0", port=8080, debug=True)