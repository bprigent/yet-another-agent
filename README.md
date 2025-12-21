# 📂 Project: "Deep-Personal-Assistant"

A long-horizon AI agent built with LangGraph DeepAgent, featuring Gmail integration, persistent local memory, and a 100% Python stack.

## 🚀 Overview

This agent isn't just a chatbot; it’s a Deep Agent. It uses a planning-first approach to manage work. It stores what it learns about you in local text files and can autonomously research your emails to answer complex questions.

## 🛠️ Tech Stack

- Orchestration: [LangGraph](https://github.com/langchain-ai/langgraph) (DeepAgent Framework)
- LLM: Gemini 2.5 Flash (Recommended free for planning logic)
- Frontend: Chainlit (100% Python Chat UI)
- Memory: Local JSON/File-based storage
- Integrations: Google Gmail API

yet-another-agent/
├── .env                # API Keys (OpenAI, Google)
├── app.py              # Main Chainlit entry point
├── agent_logic.py      # LangGraph DeepAgent definition
├── tools/
│   ├── gmail_tools.py  # Gmail read/search functions
│   └── memory_tools.py # Tools to write/read local preferences
├── memories/           # Persistent folder where agent "learns"
│   └── profile.txt     # Created by agent to store your habits
└── credentials.json    # Google OAuth credentials