# Repository Chat Application

A full-stack application that allows users to ingest GitHub repositories and chat with the codebase using AI. Built with FastAPI backend and Flutter mobile frontend.

## Features

- 🔗 **Repository Ingestion**: Clone and process GitHub repositories
- 🤖 **AI-Powered Chat**: Ask questions about code using natural language
- 📱 **Mobile App**: Cross-platform Flutter application
- 🔍 **Code Analysis**: Supports Python, C/C++, Java, JavaScript, HTML, CSS files
- 💬 **Markdown Responses**: Well-formatted answers with code snippets
- 🗂️ **Multiple File Types**: Intelligent parsing of different programming languages

## Tech Stack

### Backend

- **FastAPI**: Modern Python web framework
- **LangChain**: AI framework for document processing
- **FAISS**: Vector database for semantic search
- **Groq**: LLM API for chat functionality
- **HuggingFace**: Embeddings model
- **Git**: Repository cloning

### Frontend

- **Flutter**: Cross-platform mobile development
- **Provider**: State management
- **HTTP**: API communication
- **Flutter Markdown**: Markdown rendering


## Setup Instructions

### Prerequisites

- Python 3.8+
- Flutter SDK 3.0+
- Git
- Android Studio or VS Code
- uv (Python package manager)

### Backend Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/Mustafa-Ahmed-Rizwan/Source-Code-Analysis.git
   ```

2. **Create virtual environment with uv**

   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   uv pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file in the backend directory:

   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

5. **Run the backend**
   ```bash
   python app.py
   ```
   The API will be available at `http://localhost:8080`

### Frontend Setup

1. **Install Flutter SDK**

   - Download from: https://flutter.dev/docs/get-started/install
   - Add Flutter to your system PATH

2. **Navigate to frontend directory**

   ```bash
   cd repo_chat_app
   ```

3. **Install dependencies**

   ```bash
   flutter pub get
   ```

4. **Configure API connection**
   Edit `lib/services/api_service.dart` and update the `baseUrl`:

   ```dart
   static const String baseUrl = 'http://YOUR_BACKEND_URL:8080';
   ```

   **Connection URLs:**

   - Android Emulator: `http://10.0.2.2:8080`
   - iOS Simulator: `http://localhost:8080`
   - Physical Device: `http://YOUR_COMPUTER_IP:8080`

5. **Run the Flutter app**
   ```bash
   flutter run
   ```

## Usage Guide

1. **Start the Backend**

   - Activate virtual environment
   - Run `python app.py`

2. **Launch Mobile App**

   - Connect phone or start emulator
   - Run `flutter run`

3. **Ingest Repository**

   - Go to "Repository" tab
   - Enter GitHub URL (e.g., `https://github.com/user/repo`)
   - Click "Ingest Repository"

4. **Chat with Code**
   - Switch to "Chat" tab
   - Ask questions about the codebase
   - Get AI-powered responses with code examples

## Supported File Types

- **Python**: `.py` files
- **C/C++**: `.c`, `.cpp`, `.h`, `.hpp` files
- **Java**: `.java` files
- **JavaScript**: `.js` files
- **Web**: `.html`, `.css` files

## Development Notes

### Backend Architecture

- Uses FAISS for vector similarity search
- Implements function/class-level chunking for better context
- Supports conversational memory
- Custom prompt templates for code-specific responses

### Frontend Architecture

- Provider pattern for state management
- Responsive design for different screen sizes
- Markdown rendering for formatted responses
- Error handling with user-friendly messages

## Environment Variables

Create a `.env` file in the backend directory:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional (with defaults)
HOST=0.0.0.0
PORT=8080
```

## Requirements Files

### Backend Dependencies (requirements.txt)

All Python packages are managed via `uv` and listed in `requirements.txt`.

### Frontend Dependencies (pubspec.yaml)

Flutter packages are defined in `pubspec.yaml` with version constraints.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test thoroughly
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
