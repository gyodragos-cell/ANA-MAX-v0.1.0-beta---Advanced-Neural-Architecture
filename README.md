# ANA MAX OS-22

[![GitHub Pages](https://img.shields.io/badge/Site-Live-brightgreen)](https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Advanced Neural Architecture - Operating System 22**

A local-first AI operating system and agent orchestrator with deterministic execution, self-healing capabilities, and strict security boundaries.

---

## 🚀 Overview

ANA MAX OS-22 is a sophisticated local AI runtime that combines:

- **Local-First Philosophy**: Runs entirely on your machine, no cloud required
- **OS-22 Core**: Deterministic orchestrator with bounded autonomy
- **ToolBridge**: 90+ production-ready tools for system control, web automation, code analysis
- **RAGBridge**: Semantic memory and knowledge retrieval
- **MCP Server**: Model Context Protocol integration for IDE tools
- **Self-Healing v2**: Automatic error detection and recovery
- **Autonomy v3**: Controlled agent initiative with confidence scoring

---

## 📦 Quick Start

```bash
# Clone the repository
git clone https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture.git
cd ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run OS-22
scripts\os22\start_os22_lab_chat.bat
```

---

## 🏗 Architecture

```
Input Layer (User prompts, MCP requests)
    ↓
Context Builder (Conversation memory, RAG context, Tool specs)
    ↓
AI Engine (Local LLM: Phi-3 Mini, Mistral, etc.)
    ↓
Tool Router (ToolBridge: orchestrates 90+ tools)
    ↓
Execution Layer (Sandbox: secure command execution)
    ↓
Observability (Telemetry, Self-Healing v2, Autonomy v3)
```

---

## 📚 Documentation

- [OS-22 Overview](docs/OS22_OVERVIEW.md)
- [Architecture](docs/ARCHITECTURE.md)
- [ToolBridge](docs/TOOLBRIDGE.md)
- [RAGBridge](docs/RAGBRIDGE.md)
- [MCP](docs/MCP.md)
- [Self-Healing](docs/SELF_HEALING.md)
- [Autonomy](docs/AUTONOMY.md)
- [Boot Sequence](docs/BOOT_SEQUENCE.md)

---

## 🌐 Live Site

Visit the official OS-22 site:  
👉 [https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/](https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/)

---

## 🤝 Contributing

We welcome contributions!

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Commit** your changes: `git commit -m "Add my feature"`
4. **Push** to the branch: `git push origin feature/my-feature`
5. **Open** a Pull Request

### Code Style

- Use type hints
- Write docstrings
- Follow PEP 8
- Keep functions small and focused

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## ❤️ Support

If you find this project useful, consider supporting development:

- ⭐ Star the repository
- 🐛 Report bugs via [Issues](https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/issues)
- 💡 Suggest features via [Discussions](https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/discussions)

---

**Made with ❤️ for the local-first AI community**
