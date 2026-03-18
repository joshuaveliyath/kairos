# ⚡ Kairos: Real-time AI Assistant

Kairos is a high-performance, real-time AI teaching and research assistant powered by **Gemini 3.1 Flash Lite Preview**, designed for cross-verified information retrieval, multimodal analysis, and personalized learning.

## 🚀 Key Features

### 🧠 Intelligent Processing
- **Multimodal Analysis**: Upload images alongside your queries. Kairos uses `gemini-3.1-flash-lite-preview` to analyze visual data in context with real-time web results.
- **Dynamic Thinking Budget**: Automatically adjusts internal reasoning time (up to 10,000 tokens) based on query complexity and domain (Science/Finance get more "thought" than Sports).
- **Domain-Specific Tones**: Responses adapt based on the topic (e.g., Academic for Science, Neutral for Politics, Analyst for Sports).

### 🔍 Real-time Verification & Search
- **Multi-Source Aggregation**: Simultaneously fetches data from DuckDuckGo, NewsAPI, and a curated list of global RSS feeds (BBC, Reuters, TechCrunch, etc.).
- **Confidence Engine**: Calculates a "Kairos Confidence Score" based on source reputation and cross-verification across multiple engines.
- **Fact-Checker Mode**: A dedicated interface to verify pasted text sentence-by-sentence against live web data.

### 💾 Memory & Personalization
- **Adaptive Style Detection**: Analyzes chat history to detect your preferred language (English, Malayalam, etc.) and tone.
- **Persistent User Memory**: Save specific preferences (Location, Interests) into a `ChromaDB` vector store for personalized context in every answer.
- **Pronoun Resolution**: Tracks entities across the conversation. Ask "Who is Elon Musk?" followed by "What did he announce?" and Kairos knows who "he" is.

### 🛡️ Trust & Proactivity
- **Source Reputation System**: Users can provide feedback (👍/👎) on answers, which dynamically updates the reputation score of the information sources used.
- **Proactive Alerts**: Register "Watch Topics." Kairos can scan the web for updates and alert you only when significant changes occur compared to last known info.

## 🛠️ Tech Stack

- **LLM**: Google Gemini API (`gemini-3.1-flash-lite-preview`)
- **Vector Database**: `ChromaDB` (Local persistent storage for memory and reputation)
- **Frontend**: `Gradio` (Multimodal chat interface with multi-user authentication)
- **Search**: `duckduckgo-search`, `newsapi-python`, `feedparser`
- **Async**: `asyncio` for parallelized source fetching

## 📦 Installation & Setup

1. **Clone & Install**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_google_ai_studio_key
   NEWS_API_KEY=your_newsapi_org_key
   ```
   
3. **Run**:
   ```bash
   python main.py
   ```

> 💡 **Note:** Don't forget to update the users list in `main.py`.

## 👥 Multi-User Support
Kairos includes built-in authentication. Current default users are configured in `main.py`. Access via `http://localhost:7860` (or your LAN IP provided in the console).

## 📜 License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
