# Source Code Analysis

## Overview
This project is a web-based chatbot application designed to ingest GitHub repositories containing Python code and enable users to interact with the codebase through natural language queries. Built using Flask, it leverages LangChain for conversational retrieval, HuggingFace embeddings for semantic understanding, and FAISS for efficient vector storage. The application provides a user-friendly interface to ingest repositories, ask questions about the code, and manage chat history.

## Features
- **Repository Ingestion**: Clone and process GitHub repositories into analyzable document chunks.
- **Code Analysis**: Break down Python code into function and class-level chunks with metadata for detailed querying.
- **Conversational Interface**: Chat with the codebase using a custom LLM-powered Q&A system.
- **Memory Management**: Clear repository data or chat history as needed.
- **Responsive Design**: A clean UI with Tailwind CSS styling for an enhanced user experience.

## Prerequisites
- Python 3.8+
- Git (for repository cloning)
- Required Python packages (listed in `requirements.txt`)
- GROQ API Key (set as `GROQ_API_KEY` environment variable)

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

2. **Set Up Environment**
   - Create a virtual environment and activate it:
     ```bash
     python -m venv venv
     source venv/bin/activate  # On Windows: venv\Scripts\activate
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

3. **Configure Environment Variables**
   - Create a `.env` file in the root directory and add your GROQ API Key:
     ```
     GROQ_API_KEY=your_api_key_here
     ```

4. **Initialize the Project**
   - Run the setup script to create necessary files:
     ```bash
     python template.py
     ```

## Usage

1. **Run the Application**
   ```bash
   python app.py
   ```
   The app will be available at `http://0.0.0.0:8080`.

2. **Ingest a Repository**
   - Enter a GitHub repository URL (e.g., `https://github.com/username/repo`) in the "Ingest GitHub Repository" section and click "Ingest".
   - Wait for the processing to complete (this may take a moment for large repositories).

3. **Chat with the Codebase**
   - Once ingested, use the "Chat with Codebase" section to ask questions about the code.
   - Click "Send" or press Enter to submit your query.
   - Use "Clear Chat" to reset the conversation history or "Clear Repo" to remove the current repository data.

## Project Structure
- `app.py`: Main Flask application entry point.
- `src/helper.py`: Utility functions for repository ingestion, document loading, and chunking.
- `src/route_handlers.py`: Defines Flask routes for ingestion and chatting.
- `index.html`: Frontend template with chat interface.
- `styles.css`: Custom CSS to complement Tailwind styling.
- `script.js`: JavaScript for dynamic frontend interactions.
- `template.py`: Script to initialize project files.
- `.env`: Environment variable configuration.
- `.gitignore`: Git ignore file.
- `README.md`: This file.
- `requirements.txt`: Project dependencies.

## Contributing
Contributions are welcome! Please fork the repository and submit pull requests with your changes. Ensure to:
- Follow the existing code style.
- Add tests or documentation as needed.
- Open an issue for discussion before making significant changes.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- [LangChain](https://python.langchain.com/) for conversational AI capabilities.
- [HuggingFace](https://huggingface.co/) for embeddings.
- [FAISS](https://github.com/facebookresearch/faiss) for vector storage.
- [Tailwind CSS](https://tailwindcss.com/) for styling.