# 🤖 Autonomous Research Agent

An autonomous AI agent that accepts a research topic, autonomously plans a search strategy, collects information from the web in parallel, deduplicates it using semantic similarity, and synthesizes a structured Markdown and PDF report — all backed by a free-tier stack.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🧠 **LLM Planner** | Groq (`qwen/qwen3.6-27b`) autonomously decides what to search and which pages to read |
| 🔍 **Web Search** | DuckDuckGo Search — no API key required |
| ⚡ **Parallel Fetching** | `aiohttp` async sessions fetch multiple pages simultaneously with custom headers |
| 🧹 **Semantic Deduplication** | `sentence-transformers` (`all-MiniLM-L6-v2`) removes near-duplicate content |
| 📄 **Report Generation** | Structured Markdown & PDF report with Executive Summary, Findings, and References |
| 💾 **SQLite Memory** | Re-running the same query instantly returns the cached result in under 1 second |
| 💸 **100% Free Stack** | Groq free tier + DuckDuckGo + local sentence-transformers (lazy-loaded for instant startup) |

---

## 🏗️ Architecture

```
User Query (CLI)
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                   main.py (Orchestrator)             │
│                                                      │
│  1. Check SQLite Memory  ──► Cache Hit? Return early │
│  2. run_agent()                                      │
│  3. chunk_text() + deduplicate()                     │
│  4. synthesize_report()                              │
│  5. export_markdown() / export_pdf()                 │
│  6. save_search() → SQLite                           │
└─────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│               agent.py (Agentic Loop)                │
│                                                      │
│  Groq LLM ◄──────────────────────────────────────┐  │
│      │                                            │  │
│      ▼  (tool_calls)                              │  │
│  ┌──────────────┐    ┌────────────────────────┐  │  │
│  │  web_search  │    │      fetch_page         │  │  │
│  │ (DuckDuckGo) │    │  (aiohttp, trafilatura) │  │  │
│  └──────┬───────┘    └───────────┬────────────┘  │  │
│         │  [parallel execution]  │               │  │
│         └──────────┬─────────────┘               │  │
│                    │ results                      │  │
│                    └──────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│             dedup.py (Semantic Deduplication)        │
│  sentence-transformers → cosine similarity > 0.85   │
└─────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│          Groq LLM Synthesis → Markdown & PDF         │
│  Sections: Executive Summary | Key Points | Findings │
│            Actionable Insights | References          │
└─────────────────────────────────────────────────────┘
```

---

## 📋 Comprehensive System Workflows

Below are the step-by-step guides for installing, running, and modifying the agent.

### 1. Setup & Environment Verification Workflow

Follow this procedure to configure API credentials and verify your execution workspace.

#### Step 1.1: Clone the Repository
```bash
git clone <your-repo-url>
cd research-agent
```

#### Step 1.2: Install Required Dependencies
Ensure you have all needed packages installed:
```bash
pip install -r requirements.txt
```

#### Step 1.3: Setup API Credentials
Create a `.env` file in the root of the `research-agent/` directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

#### Step 1.4: Run the Setup Verification Script
Execute the following verification commands to ensure the Groq API key works and to list active models available under your authorization profile:
```bash
python -c "import dotenv, os, groq; dotenv.load_dotenv(); c = groq.Groq(api_key=os.getenv('GROQ_API_KEY')); print('\n'.join(sorted([u.id for u in c.models.list().data])))"
```
*Expected Output includes:*
```text
openai/gpt-oss-120b
qwen/qwen3.6-27b
...
```

#### Step 1.5: Test DuckDuckGo Web Search Integration
Ensure search connectivity is working:
```bash
python -c "from tools.search import web_search; print(web_search('AI Agent breakthroughs 2026'))"
```

---

### 2. Executing Research Workflow

Follow this workflow to perform automated research and generate styled reports.

#### Option A: Run via Programmatic CLI Arguments
To run research on a specific topic directly from the terminal:
```bash
python main.py "Your research topic here"
```
*Example:*
```bash
python main.py "Quantum computing achievements predicted for 2026"
```

#### Option B: Run via Interactive CLI Prompt
If you omit the topic argument, the agent will prompt you to enter the topic interactively:
```bash
python main.py
```
*Interactive Flow:*
```text
============================================================
       Autonomous Research Agent
============================================================
Enter your research topic: quantum computing trends
```

#### Option C: Force Refresh the Cache (Bypassing SQLite Memory)
By default, the agent saves all reports to an SQLite database (`searches.db`). Re-running the exact same query will return cached results instantly. To bypass the cache and fetch live, fresh data, use the `--force` flag:
```bash
python main.py "Your research topic" --force
```

#### Accessing your Research Reports
Once research is complete, the generated files are written to a dedicated `reports` sub-directory:
- **Markdown Report:** `reports/report_<query>.md` (Clean structured Markdown with references and URL links)
- **PDF Report:** `reports/report_<query>.pdf` (Beautiful printable PDF rendered via `xhtml2pdf`)

---

### 3. Developer Customizations & Extensions Workflow

Follow this workflow to customize, optimize, or extend the functionalities of the Autonomous Research Agent.

#### Modifying LLM Models
The models are defined in two main locations:
- **Agent Loop Model** (`agent.py` line 101):
  ```python
  _TOOL_USE_MODEL = "qwen/qwen3.6-27b"
  ```
  Change this value to use a different tool-calling model.
  
- **Report Synthesis Model** (`main.py` line 30):
  ```python
  _SYNTHESIS_MODEL = "openai/gpt-oss-120b"
  ```
  Change this value to target a different model for combining results into standard Markdown.

#### Modifying Semantic Deduplication Thresholds
If you find that the generated report is missing detail or contains redundant info:
- Edit the similarity thresholds inside `main.py` when calling `deduplicate()`:
  ```python
  unique_chunks = deduplicate(all_chunks, threshold=0.85)
  ```
  - **Increase** (e.g. `0.90`) to keep more chunks (allowing more similar text).
  - **Decrease** (e.g. `0.75`) to filter aggressively (less redundant text in report).

#### Modifying Web Fetch Crawler
To change the user-agent headers, timeout length, or character limits per page:
- Open `tools/extract.py`.
- Tweak `_MAX_CHARS_PER_PAGE` to limit how much text is extracted per source.
- Update headers to crawl sites with specific crawler protections.

#### Customizing PDF Styling
The PDF report is generated from the generated markdown using `xhtml2pdf`.
- Open `export.py`.
- Edit the CSS variable `_PDF_STYLE` to adjust margins, fonts, table cell styling, page dimensions, or header/footer borders.

---

## 📁 Project Structure

```text
research-agent/
├── main.py          # Entry point & orchestrator (caching check, dedup, synthesis)
├── agent.py         # Agentic LLM loop (tool-calling loop with Groq)
├── dedup.py         # Semantic deduplication with sentence-transformers (lazy-loaded)
├── memory.py        # SQLite persistence layer (caching past run summaries)
├── export.py        # Markdown & PDF report exporter
├── requirements.txt # Python package requirements
├── .env             # Your Groq API key (excluded from git)
├── searches.db      # SQLite cache database (created automatically)
├── tools/
│   ├── search.py    # DuckDuckGo web search tool
│   └── extract.py   # Async web page fetcher & text extractor (custom user-agent headers)
└── reports/         # Generated output reports saved here (created automatically)
```

---

## 🛠️ Tech Stack

| Component | Library / Model | Cost |
|---|---|---|
| LLM (Planner Loop) | Groq (`qwen/qwen3.6-27b`) | Free tier |
| LLM (Synthesizer) | Groq (`openai/gpt-oss-120b`) | Free tier |
| Web Search | `duckduckgo-search` (`ddgs`) | Free |
| Async Web Fetching | `aiohttp` (optimized crawler headers) | Free |
| HTML → Text Extraction | `trafilatura` | Free |
| Semantic Deduplication | `sentence-transformers` (lazy-loaded for instant startup) | Free, runs locally |
| Memory / Caching | `sqlite3` (stdlib) | Free |
| Report Export | Markdown + `xhtml2pdf` | Free |

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
