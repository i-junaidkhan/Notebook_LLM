cat > .\README.md << 'EOF'
# CogniFlow

<div align="center">

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Status](https://img.shields.io/badge/Status-Beta-orange)
![Languages](https://img.shields.io/badge/Languages-English%20%7C%20한국어-green)
![Tech](https://img.shields.io/badge/Tech-Next.js%20%7C%20FastAPI%20%7C%20SurrealDB-purple)

**AI-Powered Research Workspace & Knowledge Graph**

[Features](#-features) • [Tech Stack](#-tech-stack) • [Quick Start](#-quick-start) • [Roadmap](#-roadmap)

</div>

---

## 🚀 Overview

CogniFlow is a privacy-first research platform that transforms how you collect, process, and visualize knowledge. Leveraging advanced AI workflows, it turns scattered sources into structured insights, mind maps, and even audio podcasts.

**New in CogniFlow:**
- 🧠 **AI Mind Mapping:** Auto-generate visual knowledge graphs from your notes.
- 🇰🇷 **Korean Interface:** Full native support for Korean users (i18n).
- 🔒 **Privacy-First:** Local data control with optional cloud AI providers.

---

## ✨ Features

### 📊 Core Capabilities

| Feature | Description |
| :--- | :--- |
| **🧠 Mind Map Generator** | Automatically convert notebook content into interactive mind maps using LangGraph. |
| **💬 AI Chat Assistant** | Context-aware conversations with your sources. Ask questions, get cited answers. |
| **📝 Smart Notes** | Manual, AI-generated, or chat-saved notes with bidirectional linking. |
| **🎙️ Podcast Generator** | Convert research notes into multi-speaker audio episodes (TTS). |
| **🔍 Search & Ask** | Hybrid full-text + semantic search across all your knowledge bases. |
| **🔄 Transformations** | Custom AI pipelines to summarize, extract insights, or structure data. |

### 🌐 Internationalization
- **🇰🇷 Korean (한국어)**: Full UI translation.
- **🇺🇸 English**: Default language.
- *More languages coming soon.*

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Python 3.11+ |
| **Database** | SurrealDB (Graph + Vector) |
| **AI Workflows** | LangGraph, LangChain |
| **State** | Zustand, TanStack Query |

---

## 📦 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- SurrealDB

### 1. Clone & Install
```bash
git clone https://github.com/i-junaidkhan/Notebook_LLM.git
cd Notebook_LLM