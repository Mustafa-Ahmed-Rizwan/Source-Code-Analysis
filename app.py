from dotenv import load_dotenv
import os
import logging
import shutil
from flask import Flask
from src.route_handlers import setup_routes

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

# Setup routes
setup_routes(app, persist_directory)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)