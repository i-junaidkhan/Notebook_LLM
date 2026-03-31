# 🧠 CogniFlow

**English | 한국어**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org)
[![SurrealDB](https://img.shields.io/badge/SurrealDB-latest-ff69b4)](https://surrealdb.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-3178c6)](https://langchain-ai.github.io/langgraph/)

**Privacy‑first research platform** that helps you collect, organize, and synthesize knowledge. AI‑powered note‑taking, mind maps, podcast generation, and full‑text + semantic search – all running locally or on your own infrastructure.

---

## ✨ Features

| Category | Capabilities |
|----------|---------------|
| **🤖 AI Chat Assistant** | Context‑aware conversations with full privacy controls. Chat with your entire knowledge base. |
| **📝 Smart Notes** | Manual notes, AI‑generated summaries, or notes saved directly from chat. |
| **🧠 AI Mind Maps** | One‑click generation of hierarchical mind maps from notebook sources – perfect for visualising complex topics. |
| **🔌 Content Integration** | Ingest **PDFs, YouTube videos, web articles, audio files, and video** – automatic transcription and chunking. |
| **⚙️ Transformations** | Create custom AI processing patterns (e.g., “extract all dates”, “summarise as bullet points”) and apply them to any source. |
| **🔍 Search & Ask** | Full‑text + **semantic vector search** with cited, source‑grounded answers. |
| **🎙️ Podcast Generator** | Convert any notebook or set of notes into an **audio podcast** – supports multiple languages (including Korean). |
| **🌐 Bilingual UI** | Full Korean and English localisation – switch seamlessly. |
| **🔒 Privacy‑First** | All data stays in your database. Bring your own API keys or use local models (Ollama). |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- SurrealDB (v2+)
- (Optional) Ollama for local AI

### Installation

```bash
# Clone the repo
git clone https://github.com/i-junaidkhan/Notebook_LLM.git
cd open-notebook

# Backend
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\Activate.ps1` on Windows
pip install -e .

# Frontend
cd frontend
npm install
