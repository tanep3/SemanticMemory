[🇯🇵 日本語](./README_jp.md)

---

# SemanticMemory

A FastAPI application that provides conversation log / memo storage with vector search capabilities.

## 🌟 Features

- **Conversation Log Management**: Save, update, and delete with SQLite + ChromaDB dual storage
- **Vector Search**: Semantic search with SBERT embeddings
- **Auto Summarization**: Summary generation via Ollama
- **Neural Dive UI**: Web interface for managing memories from your browser
- **MCP Integration**: AI tool integration via Model Context Protocol
- **RESTful API**: Fast API server powered by FastAPI
- **Docker Ready**: Easy deployment

---

## 🚀 Getting Started

### 1. Start with Docker

```bash
docker compose up -d --build
```

Default settings:

* Data stored in `./datas` directory (SQLite / ChromaDB)
* Port: `6001`
* CPU-only PyTorch (CUDA/NVIDIA packages are not installed)

### 2. API Documentation

```
http://localhost:6001/docs
```

View the API documentation via FastAPI's Swagger UI.

---

## 🧠 Neural Dive UI (Admin Panel)

A web-based admin panel for browsing, editing, and deleting memories.

### Access

```
http://localhost:6001/
```

### Features

| Feature | Description |
|---|---|
| 📋 **Memory List** | Browse saved conversation logs by time or keyword search |
| ✏️ **Edit** | Edit main_text, sub_text, summary individually (auto-regenerates summary when main_text changes) |
| 🗑️ **Delete** | Delete unwanted memories |
| 🔍 **Orphan Detection** | Detect and fix inconsistencies between SQLite and ChromaDB |

### Authentication (Optional)

Configure Basic Auth in `.env`:

```env
UI_USER=admin
UI_PASS=secret
```

---

## 🔗 MCP Integration (AI Tool Linking)

Use MCP (Model Context Protocol) to operate memories from AI assistants.

### Available Tools

| Tool | Description |
|---|---|
| `recall_memory` | Explicitly search and retrieve past memories |
| `delete_memory` | Delete memories (with confirmation) |

### Configuration

See the following for details:
- [examples/usage.md](examples/usage.md) - Client examples & MCP setup
- [docs/MCP要件定義書.md](docs/MCP要件定義書.md) - MCP specification (Japanese)

---

## 📁 Client Examples

| File | Description |
|---|---|
| `examples/ai_sample.py` | Basic RAG client |
| `examples/ai_mcp_sample.py` | MCP-integrated client (with HITL) |
| `examples/open_webui_filter.py` | Filter for OpenWebUI |

See [examples/usage.md](examples/usage.md) for details.

---

## ⚙️ Environment Variables

Configure via `.env` or `docker-compose.yml`:

| Variable | Default | Description |
|---|---|---|
| `SQLITE_PATH` | `./datas/semantic_memory.db` | SQLite file path |
| `CHROMA_PATH` | `./datas/chroma/` | ChromaDB directory |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Host Ollama URL used by Docker |
| `SBERT_MODEL` | `cl-nagoya/ruri-v3-70m` | Embedding model for a new database |
| `SBERT_DEVICE` | `cpu` | SentenceTransformer device |
| `UI_USER` / `UI_PASS` | (empty) | UI authentication (enabled when both set) |
| `API_TIMEOUT` | `30` | Client API timeout (seconds) |

---

## Changing the Embedding Model

New databases use Ruri v3 by default. Existing databases keep the model stored
in their settings table and are not migrated automatically.

Do not change only `SBERT_MODEL` after vectors have been stored. Embedding
dimensions and vector spaces differ between models. Rebuild from SQLite:

```bash
curl -fsS -X POST \
  "http://127.0.0.1:6001/api/rebuild_vector?sbert_model=cl-nagoya/ruri-v3-70m"
curl -fsS http://127.0.0.1:6001/api/check_integrity
```

The replacement collection is fully built and validated before activation.
If model loading, encoding, or validation fails, the active collection and
model setting remain unchanged.

---

## 🔄 Update

```bash
./scripts/auto_update.sh
```

Automatically performs git pull, Docker build, and removes old images.

---

## 📚 Models & Licenses

This project uses the following external models:

* [cl-nagoya/ruri-small-v2](https://huggingface.co/cl-nagoya/ruri-small-v2) - Apache 2.0
* [cl-nagoya/ruri-v3-70m](https://huggingface.co/cl-nagoya/ruri-v3-70m) - Apache 2.0
* [SakanaAI/TinySwallow-1.5B-Instruct-GGUF](https://huggingface.co/SakanaAI/TinySwallow-1.5B-Instruct-GGUF) - Apache 2.0, Gemma Terms

Model licenses differ from this repository's license. Users are responsible for reviewing and complying with model license terms.

---

## ⚖️ License

This project is licensed under the MIT License.
See [LICENSE](./LICENSE) for details.
