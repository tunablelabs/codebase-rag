# Codex: AI-Powered Code Understanding Platform

<!-- Replace with your actual logo when available -->
<!-- <p align="center">
  <img src="https://via.placeholder.com/200x200" alt="Codex Logo" width="200" height="200">
</p> -->

<p align="center">
  <a href="#features">Features</a> •
  <a href="#demo">Demo</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#usage">Usage</a> •
  <a href="#api-reference">API Reference</a> •
  <a href="#roadmap">Roadmap</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.0.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/Frontend-Next.js-000000" alt="Frontend">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688" alt="Backend">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

Codex is a full-stack application that transforms how developers understand and interact with codebases. By combining advanced code parsing, vector embeddings, and AI-driven insights, Codex allows you to navigate, search, and comprehend code through natural language conversations.

<!-- Replace with your actual screenshot when available -->
<!-- ![Codex Demo Screenshot](https://via.placeholder.com/800x450) -->

## ✨ Features

- **Natural Language Code Queries**: Ask questions about your codebase in plain English
- **Intelligent Code Navigation**: Find and understand code patterns across repositories
- **Project-Wide Context**: Get answers that incorporate understanding from your entire codebase
- **Multi-Language Support**: Works with Python, JavaScript, TypeScript, and Java codebases
- **Interactive UI**: Modern, responsive interface built with Next.js
- **Real-time Responses**: Stream AI answers as they're generated
- **Repository Integration**: Direct analysis of Git repositories
- **Quality Metrics**: Automatic evaluation of answer quality and relevance
- **Session Management**: Save and revisit conversations about your code
- **Documentation Analysis**: Process Markdown and text documentation alongside code

<!-- Add your demo link when available -->
<!-- ## 🎮 Demo

Visit our [live demo](https://example.com) to try Codex with sample repositories! -->

## 🏗️ Architecture

Codex combines powerful frontend and backend components:

### Frontend (Next.js)
- Modern, responsive UI built with Next.js and React
- Real-time streaming response display
- Code syntax highlighting
- Session management interface
- Repository and file visualization

### Backend (FastAPI)
- RESTful and WebSocket API endpoints
- Tree-sitter code parsing for AST generation
- Language-specific chunking strategies
- Vector embedding and semantic search
- LLM integration (OpenAI, Azure, Claude)
- Document storage with DynamoDB
- Response evaluation metrics

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Node.js and npm
- Git
- Docker and Docker Compose (for local DynamoDB)
- OpenAI API key or Azure OpenAI credentials
- Qdrant account or self-hosted instance
- AWS account (for DynamoDB) or local DynamoDB setup

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/codex.git
   cd codex
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   cd ..
   ```

4. Configure environment variables:
   - Create `.env` in the root directory (for frontend)
   - Create `.env` in the `backend/config` directory (for backend)

   Backend `.env` example:
   ```
   # LLM Configuration
   OPENAI_API_KEY=your_openai_api_key
   AZURE_OPENAI_ENDPOINT=your_azure_endpoint
   AZURE_OPENAI_KEY=your_azure_key
   AZURE_OPENAI_MODEL=your_azure_model

   # Qdrant Configuration
   QDRANT_HOST=your_qdrant_host
   QDRANT_API_KEY=your_qdrant_api_key

   # AWS Configuration (for DynamoDB)
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_DEFAULT_REGION=your_aws_region

   # Local Development (Optional)
   USE_LOCAL_DYNAMODB=true
   DYNAMODB_LOCAL_ENDPOINT=http://localhost:7000
   ```

5. Start the application:

   Backend:
   ```bash
   cd backend/src
   python -m main.py
   ```

   Frontend:
   ```bash
   # In another terminal, from project root
   npm run dev
   ```

6. Open your browser to [http://localhost](http://localhost)

## 💡 Usage

### Getting Started with Codex

1. **Create a User**: Register with your email address
2. **Upload a Repository**: Connect a Git repository or upload local files
3. **Ask Questions**: Start querying your codebase in natural language
4. **Explore Results**: Navigate through the answers and source references
5. **Save Sessions**: Return to previous conversations about your code

### Example Questions

Codex can answer a wide range of questions about your code:

- "How is authentication implemented in this project?"
- "Explain the data flow from frontend to database"
- "What design patterns are used in the user management module?"
- "Find places where we're not properly handling errors"
- "Summarize how the logging system works"
- "What dependencies does the payment processing component have?"

## 📡 API Endpoints

Codex provides a comprehensive API for integration with your tools:

### User and Session Management
- `POST /codex/create/user`: Create a new user
- `POST /codex/create/session/uploadproject`: Upload a repository
- `GET /codex/session/list`: List all sessions for a user
- `POST /codex/session/rename`: Rename a session
- `POST /codex/session/delete`: Delete a session
- `GET /codex/session/data`: Get session chat history

### Repository Analysis
- `POST /codex/storage`: Process and store repository in vector database
- `POST /codex/stats`: Get repository statistics

### Querying and Chat
- `POST /codex/query`: Query the repository (synchronous)
- `WS /codex/query/stream`: Stream query responses (WebSocket)
- `POST /codex/follow-up-questions`: Generate follow-up questions

Full API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs) when running the backend.

## 📁 Project Structure

```
codex/
├── backend/
│   ├── src/
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── api/
│   │   │   └── routes.py             # API endpoints
│   │   ├── chunking/                 # Code chunking modules
│   │   ├── config/                   # Configuration
│   │   ├── git_repo_parser/          # Repository parsing
│   │   └── vector_store/             # Vector embedding logic
│   ├── scripts/
│   │   └── query_engine.py           # Original implementation
│   └── rag_v2/                       # RAG implementation
├── app.py                            # Alternative entry point
├── public/                           # Next.js public assets
├── src/                              # Next.js frontend source
│   ├── app/
│   │   └── page.tsx                  # Main question page
│   ├── components/                   # React components
│   └── ...
├── package.json                      # Frontend dependencies
└── README.md                         # This file
```

## 🗺️ Roadmap

- [ ] Multi-user collaboration
- [ ] Visual code graph navigation
- [ ] IDE extensions (VS Code, JetBrains)
- [ ] Automated code documentation generation
- [ ] CI/CD integration
- [ ] Custom LLM fine-tuning
- [ ] Support for more programming languages
- [ ] On-premise deployment option

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) for code parsing
- [OpenAI](https://openai.com/) for language models
- [Qdrant](https://qdrant.tech/) for vector database
- [FastAPI](https://fastapi.tiangolo.com/) for backend framework
- [Next.js](https://nextjs.org/) for frontend framework
- All open-source contributors