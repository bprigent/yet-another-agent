# Deep Personal Assistant

A long-horizon AI agent built with LangGraph DeepAgent, featuring Gmail integration, persistent local memory, and a 100% Python stack.

## Overview

This agent isn't just a chatbot; it's a **Deep Agent** that uses a planning-first approach to manage complex tasks. It stores what it learns about you in local text files and can autonomously research your emails to answer complex questions.

### What is a Deep Agent?

A Deep Agent uses hierarchical planning and reflection to break down complex tasks into manageable subtasks. Unlike simple chatbots, it:
- **Plans** before executing (creates a todo list)
- **Executes** tools in a structured manner
- **Reflects** on results to ensure completeness
- **Learns** from interactions and stores preferences locally

## Features

### 🧠 Persistent Preference Learning
The agent uses a Composite Backend to remember your preferences. When you say, "I prefer technical summaries," it saves this to `/memories/user_profile.txt`. Every time you restart the app, it reads this file first to maintain context about your preferences.

### 📧 Gmail Executive
- **Triage**: "Summarize any unread emails about the project deadline."
- **Drafting**: "Draft a polite reply to Sarah saying I'll be late, using my usual tone."
- **Context Management**: For long emails (e.g., 5,000 words), the agent spawns a Sub-Agent to read it, keeping its own "short-term memory" clean.

### 📅 Google Calendar Integration
- **Create Events**: "Schedule a 30-minute design review next week"
- **View Schedule**: "What's on my calendar today?"
- **Find Availability**: "When can I work out this week?"
- **Summarize**: "What does my week look like?"

### 🔄 Planning Loop
Every request follows this cycle:
1. **Plan**: Creates a todo list (e.g., "I need to 1. Check mail, 2. Check user_profile for tone, 3. Write draft.")
2. **Execute**: Runs the tools in order
3. **Reflect**: "Did I miss anything?" → Finalizes the response

## Tech Stack

- **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph) (DeepAgent Framework)
- **LLM**: Gemini 2.5 Flash (Recommended free tier for planning logic)
- **Frontend**: Chainlit (100% Python Chat UI)
- **Memory**: Local JSON/File-based storage
- **Integrations**: Google Gmail API (extensible for additional tools)

## Project Structure

```
yet-another-agent/
├── .env                # Stores your GOOGLE_API_KEY
├── app.py              # UI & Chainlit logic
├── agent_logic.py      # The Brain: LangGraph + DeepAgent config
├── tools/
│   ├── gmail_tools.py  # Custom tools for reading/searching mail
│   ├── memory_tools.py # Filesystem tools (read_file, write_file)
│   ├── calendar_auth.py # Google Calendar OAuth authentication
│   ├── calendar_utils.py # Shared calendar utilities
│   ├── create_update_calendar_event.py # Create/update events
│   ├── get_calendar_schedule.py # Get schedule for time window
│   ├── find_available_time_slots.py # Find free time slots
│   └── summarize_calendar.py # Natural language calendar summary
├── memories/           # 🧠 WHERE THE AGENT GROWS
│   └── profile.txt     # Local file where agent saves your preferences
└── credentials.json    # Your Google Cloud Gmail OAuth file
```

## Prerequisites

- Python 3.8+
- Google Cloud account (for Gmail API)
- Google AI Studio account (for Gemini API key)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd yet-another-agent
```

### 2. Install Dependencies

```bash
pip install deepagents chainlit langchain-google-genai google-api-python-client
```

### 3. Configure API Keys

#### Google AI Studio (Gemini API)
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Create a `.env` file in the root directory:

```bash
GOOGLE_API_KEY=your_api_key_here
```

#### Gmail API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials file and save it as `credentials.json` in the root directory

#### Google Calendar API Setup
1. In the same Google Cloud project, enable the **Google Calendar API**
2. Use the same OAuth 2.0 credentials file (`credentials.json`) - no need to create new credentials
3. Add the following to your `.env` file (optional, defaults shown):
   ```bash
   GOOGLE_CALENDAR_CREDENTIALS_PATH=credentials.json
   GOOGLE_CALENDAR_TOKEN_PATH=token.json
   ```
4. On first run, the app will open a browser window for OAuth authentication
5. After authentication, a `token.json` file will be created (automatically refreshed when needed)

### 4. Run the Application

```bash
chainlit run app.py
```

The application will open in your browser at `http://localhost:8000`

## Usage Examples

### Learning Preferences
```
You: "I prefer technical summaries with bullet points"
Agent: [Saves preference to memories/profile.txt]
```

### Email Triage
```
You: "Summarize any unread emails about the project deadline"
Agent: [Searches Gmail, reads relevant emails, provides summary]
```

### Drafting Emails
```
You: "Draft a polite reply to Sarah saying I'll be late, using my usual tone"
Agent: [Reads your profile for tone preferences, drafts email]
```

### Calendar Management
```
You: "Schedule a 30-minute design review next week"
Agent: [Finds available slots, creates calendar event]

You: "What's on my calendar today?"
Agent: [Retrieves and summarizes today's events]

You: "When can I work out this week?"
Agent: [Analyzes schedule, finds available 1-hour slots]
```

## Privacy & Security

### Data Storage
- **Local Only**: All memories are stored in `./memories/` directory on your local machine
- **No Cloud Storage**: Your preferences and learned information never leave your device
- **Easy Deletion**: Simply delete the `memories/` folder to reset the agent

### Email Processing
- **Session-Based**: Your emails are only processed by the LLM during your active session
- **No Persistent Storage**: Email content is not stored locally or on external servers
- **API Calls Only**: Only transient prompts are sent to Gemini API; no email data is stored on external servers

## Architecture

The agent follows the Deep Agent architecture pattern:

1. **Planning Phase**: Breaks down user requests into actionable todos
2. **Tool Execution**: Uses available tools (Gmail API, file system) to gather information
3. **Memory Integration**: Reads from and writes to local memory files
4. **Reflection Phase**: Reviews results to ensure completeness
5. **Response Generation**: Synthesizes information into a coherent response

## Roadmap

- [ ] Basic Deep Agent structure with LangGraph
- [ ] Gmail API integration
- [ ] Local memory persistence
- [ ] Enhanced email triage capabilities
- [ ] Multi-email thread analysis
- [x] Calendar integration
- [ ] Additional tool integrations
- [ ] Advanced preference learning


## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph)
- UI powered by [Chainlit](https://github.com/Chainlit/chainlit)
- LLM powered by [Google Gemini](https://ai.google.dev/)
