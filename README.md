# Research Agent 🔍

An AI agent that researches any topic using Claude + real-time web search, then returns a structured summary.

## What it does

1. Takes a natural language query
2. Runs an **agentic loop** — Claude decides how many web searches to make
3. Synthesizes all results into a clean structured summary
4. Optionally saves output as a Markdown file

## Project structure

```
research-agent/
├── agent.py          # Core agent logic (agentic loop + tool use)
├── requirements.txt
├── results/          # Saved summaries (auto-created)
└── README.md
```

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/research-agent.git
cd research-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"

# 4. Run
python agent.py
```

## Concepts demonstrated

| Concept | Where |
|---|---|
| Agentic loop | `run_agent()` in `agent.py` |
| Tool use (web search) | `TOOLS` list + loop logic |
| System prompt engineering | `SYSTEM_PROMPT` |
| Structured output | Markdown formatting via prompt |
| File I/O | `save_result()` |

## Example

```
> Enter a research topic:
> What is retrieval-augmented generation?

  🌐 Searching: "retrieval augmented generation RAG explained"
  🌐 Searching: "RAG vs fine-tuning LLMs 2024"

──────────────────────────────────────────────────
## Overview
RAG (Retrieval-Augmented Generation) is a technique that ...
```

## Built with

- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- Claude Sonnet 4 with web search tool
