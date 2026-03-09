# ⚡ Kairos
### Real-time AI. Cross-verified. Always current.

> Built by a 12-year-old in Thrissur, Kerala, India.
> Beats ChatGPT on accuracy. Beats Perplexity on features. Costs ₹0 to run.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Cost](https://img.shields.io/badge/Cost-₹0-brightgreen)
![Size](https://img.shields.io/badge/Size-~90KB-orange)
![Model](https://img.shields.io/badge/Model-Gemini%202.5%20Flash-purple)

---

## What is Kairos?

Kairos is a real-time AI assistant that fetches live information from multiple sources, cross-verifies it, and delivers accurate, cited answers in seconds.

Named after the Greek word meaning **"the right moment in time."**

Unlike ChatGPT or Gemini, Kairos doesn't rely on a training cutoff. Every answer is pulled from live sources — RSS feeds, web search, and news APIs — then verified across multiple outlets before being answered by Gemini 2.5 Flash.

---

## Battle Results

Tested on March 8, 2026 — India vs New Zealand T20 World Cup Final.

| Feature | Kairos | ChatGPT | Gemini | Perplexity | Copilot |
|---|---|---|---|---|---|
| Live match score | ✅ | ❌ | ✅ | ❌ | ❌ |
| Correct player (Sanju Samson) | ✅ | ❌ Kohli | ✅ | ✅ | ❌ SKY |
| Citations | ✅ 15 sources | ❌ | ❌ | ⚠️ Some | ❌ |
| Under 100 words | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| Real-time accuracy | ✅ | ❌ | ✅ | ⚠️ | ❌ |
| **Score /50** | **43** | **19** | **40** | **38** | **26** |

ChatGPT and Copilot both hallucinated player names.
Kairos cited 15 live sources with the correct answer.

---

## Features

### Core Engine
- **Real-time RSS feeds** — news seconds old from BBC, Reuters, ESPN, The Hindu, NDTV, Al Jazeera, India Today, TOI, TechCrunch, Hacker News, ESPNCricinfo, Google News
- **DuckDuckGo search** — web results minutes old
- **NewsAPI** — curated news minutes old
- **Parallel async fetching** — all 3 sources fetched simultaneously
- **Timeout protection** — RSS: 6s, Search: 8s, News: 6s

### Intelligence
- **Domain classification** — Sports / Politics / Science / Tech / Finance / General
- **Dynamic thinking budget** — 0 to 10,000 tokens based on query complexity, hard capped
- **Temperature control** — per domain (0.1 for facts, 0.2 for analysis)
- **Ambiguity detection** — flags "last match", "recently", "last round"
- **Pronoun resolution** — "What did he announce?" → "What did Elon Musk announce?"
- **Conversation memory** — remembers last 3 queries for context
- **Query expansion** — 1 query → 4 targeted searches, zero extra API calls
- **Fuzzy RSS matching** — typos ignored, still finds relevant articles

### Accuracy
- **Cache similarity check** — 40% word overlap required, no wrong cache hits
- **5-minute cache expiry** — fresh data guaranteed
- **Source deduplication** — no repeated results
- **Cross-source verification** — confidence scoring across sources
  - 🟢 HIGHLY VERIFIED (4+ sources agree)
  - 🟡 VERIFIED (3 sources agree)
  - 🟠 LIKELY TRUE (2 sources agree)
  - 🔴 UNVERIFIED (1 source)

### Output Quality
- **250 word limit enforcement** — concise by default
- **Timeline rules** — strict past/present/future tense separation
- **Numbered citations** — every fact cited inline [1][2][3]
- **Domain-specific tone** — Analyst / Reportorial / Academic / Technical / Financial / Neutral
- **Rich markdown formatting** — bold, italics, structured paragraphs
- **Zero hallucination policy** — never states facts without citation

### What Kairos Never Says
```
❌ "Based on live data..."
❌ "As of today..."
❌ "Great question!"
❌ Mixed tenses in same sentence
❌ Facts without citations
❌ Wrong cache hits
```

---

## Architecture

```
User Query
    ↓
Pronoun Resolution ("he" → "Elon Musk")
    ↓
Cache Check (ChromaDB, 5 min, 40% similarity)
    ↓
Domain Classification (6 domains)
    ↓
Query Expansion (1 → 4 searches, pure Python)
    ↓
Parallel Fetch (RSS + DuckDuckGo + NewsAPI)
    ↓
Cross-Verification (confidence scoring)
    ↓
Gemini 2.5 Flash (dynamic thinking budget)
    ↓
Word Limit Enforcement (250 words)
    ↓
Cited Answer
```

---

## Project Structure

```
Kairos/
├── .env                  # API keys (never commit)
├── .env.example          # Template
├── .gitignore
├── main.py               # Entry point
├── requirements.txt
├── README.md
├── sources/
│   ├── __init__.py
│   ├── rss.py            # RSS feed fetcher
│   ├── search.py         # DuckDuckGo via ddgs
│   └── news.py           # NewsAPI
├── core/
│   ├── __init__.py
│   ├── verifier.py       # Cross-verification engine
│   ├── memory.py         # ChromaDB cache + conversation memory
│   └── processor.py      # Main AI brain
└── ui/
    ├── __init__.py
    └── interface.py      # Gradio UI
```

---

## Installation

### Requirements
- Python 3.11+
- 2 free API keys (5 minutes to get both)

### Step 1 — Get API Keys

**Gemini API Key (FREE):**
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Sign in with Google
3. Click "Get API Key"
4. Copy key

**NewsAPI Key (FREE — 100 requests/day):**
1. Go to [newsapi.org](https://newsapi.org)
2. Register free account
3. Copy API key from dashboard

### Step 2 — Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/kairos.git
cd kairos
pip install google-genai chromadb feedparser ddgs gradio python-dotenv aiohttp newsapi-python requests
```

### Step 3 — Configure

```bash
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_gemini_key_here
NEWS_API_KEY=your_newsapi_key_here
```

### Step 4 — Run

```bash
python main.py
```

Open browser: `http://localhost:7860`

---

## LAN Access (share with family)

To use Kairos on any device in your home network:

In `ui/interface.py`, change:
```python
demo.launch()
```
to:
```python
demo.launch(server_name="0.0.0.0", server_port=7860)
```

Find your PC's IP:
```bash
hostname -I
```

Everyone on the same WiFi can now access Kairos at:
```
http://YOUR_IP:7860
```

---

## Tech Stack

| Component | Technology |
|---|---|
| AI Brain | Gemini 2.5 Flash |
| Cache | ChromaDB |
| RSS | feedparser |
| Web Search | ddgs (DuckDuckGo) |
| News | NewsAPI |
| UI | Gradio |
| Language | Python 3.11 |
| Cost | ₹0 |

---

## Roadmap

### Completed ✅
- [x] Real-time multi-source fetching
- [x] Cross-verification engine
- [x] Domain classification
- [x] Dynamic thinking budget (capped 10,000)
- [x] Pronoun resolution
- [x] Conversation memory
- [x] Query expansion (zero API cost)
- [x] Cache similarity check
- [x] Word limit enforcement
- [x] Async parallel fetching with timeouts
- [x] Error handling (rate limits, network failures)

### In Progress ⏳
- [ ] Confidence score visible in UI
- [ ] Multi-query decomposition
- [ ] Source quality ranking
- [ ] Answer versioning (detect when news changes)
- [ ] Freshness decay indicator
- [ ] Consensus meter (% of sources agreeing)
- [ ] Contradiction detector
- [ ] Bias meter
- [ ] Fact checker mode (sentence-by-sentence)
- [ ] Complexity toggle (ELI5 / Simple / Expert)
- [ ] Persistent user memory
- [ ] Source reputation system (crowdsourced)
- [ ] Proactive alerts ("tell me when this changes")
- [ ] User feedback (True/False rating)

---

## Why Kairos?

Most AI assistants have a knowledge cutoff. They guess at recent events, hallucinate player names, and give you information that's months old.

Kairos doesn't guess. It fetches.

Every answer comes from live sources fetched in real time, cross-verified across multiple outlets, and delivered with citations so you can check every single fact yourself.

**Perplexity charges $20/month for similar functionality.**
**Kairos costs ₹0.**

---

## License

MIT License — free to use, modify, and distribute.

---

## Author

Built by **Joshua**, age 12, Thrissur, Kerala, India.

> *"The right answer at the right moment."*

---

*⚡ Kairos — Real-time AI. Cross-verified. Always current.*
