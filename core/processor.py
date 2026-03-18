import asyncio
import datetime
from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted
from sources.rss import fetch_rss
from sources.news import fetch_news
from sources.search import fetch_all_search
from core.verifier import verify_results
from core.memory import (
    store_result,
    check_cache,
    get_recent_history,
    resolve_pronouns,
    get_user_memory,
    update_source_reputation,
    get_source_reputation,
    get_watch_topics
)
import os
import re

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MAX_THINKING = 10000

def classify_domain(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["match", "score", "win", "lost",
        "cricket", "football", "ipl", "cup", "tournament",
        "player", "runs", "wicket", "goal", "team", "vs",
        "final", "semi", "quarter", "round", "innings"]):
        return "sports"
    elif any(w in q for w in ["election", "vote", "president",
        "minister", "government", "party", "parliament",
        "policy", "political", "campaign"]):
        return "politics"
    elif any(w in q for w in ["science", "research", "study",
        "discovery", "space", "physics", "biology",
        "chemistry", "experiment", "nasa", "climate"]):
        return "science"
    elif any(w in q for w in ["ai", "tech", "software",
        "hardware", "app", "startup", "google", "apple",
        "microsoft", "release", "update", "model",
        "gpu", "cpu"]):
        return "tech"
    elif any(w in q for w in ["stock", "market", "fund",
        "invest", "funding", "valuation", "ipo", "price",
        "crypto", "bitcoin", "rupee", "dollar"]):
        return "finance"
    else:
        return "general"

def detect_ambiguity(question: str) -> list:
    ambiguities = []
    q = question.lower()
    if "last round" in q:
        ambiguities.append(
            "Note: 'last round' interpreted as most recent "
            "match/stage. Clarify if you meant otherwise."
        )
    if "last match" in q:
        ambiguities.append(
            "Note: Answering for most recently completed match."
        )
    if "recently" in q or "latest" in q:
        ambiguities.append(
            "Note: Interpreting 'recently' as within last 7 days."
        )
    return ambiguities

def get_tone_instruction(domain: str) -> str:
    tones = {
        "sports":  "Tone: Analyst — factual and clear. NOT fan-heavy or dramatic. Report like a journalist not a commentator.",
        "politics":"Tone: Reportorial — strictly neutral. No opinions. No dramatic language. Just verified facts.",
        "science": "Tone: Academic — precise and clear. Use correct terminology. Cite studies where possible.",
        "tech":    "Tone: Technical journalist — clear and informed. Balance technical detail with readability.",
        "finance": "Tone: Financial analyst — neutral and data-driven. Always caveat predictions. Never give financial advice.",
        "general": "Tone: Neutral assistant — clear and helpful. Match complexity of question. Be concise but complete."
    }
    return tones.get(domain, tones["general"])

def get_thinking_budget(domain: str, question: str) -> int:
    q = question.lower()
    word_count = len(question.split())

    is_simple = any(w in q for w in [
        "who won", "what score", "how many",
        "when did", "what time", "which team",
        "who is", "did india", "what is the score"
    ])
    if is_simple:
        return 0

    is_complex = any(w in q for w in [
        "why", "explain", "analyze", "compare",
        "predict", "what will", "should i",
        "difference between", "how does", "impact of"
    ])

    is_very_complex = (
        word_count > 15 or
        q.count("and") >= 2 or
        q.count("?") >= 2
    )

    if is_very_complex:
        budget = 9000
    elif is_complex:
        budget = 7000
    else:
        domain_budgets = {
            "sports":   0,
            "politics": 3000,
            "science":  8000,
            "tech":     5000,
            "finance":  6000,
            "general":  1000,
        }
        budget = domain_budgets.get(domain, 1000)

    return min(budget, MAX_THINKING)

def format_context(results: list) -> str:
    if not results:
        return "No results found."

    context = ""
    for i, r in enumerate(results[:15], 1):
        freshness = r.get('freshness_tag', '')
        context += f"""
[{i}] Source: {r['source']} {freshness}
Title: {r['title']}
Content: {r['content']}
URL: {r['url']}
Published: {r['published']}
---"""
    return context

def expand_query(
    question: str,
    domain: str,
    history: str
) -> list[str]:
    today = str(datetime.date.today())
    queries = [question]

    queries.append(f"{question} {today}")

    if domain == "sports":
        queries.append(f"{question} live score")
        queries.append(f"{question} result today")
    elif domain == "tech":
        queries.append(f"{question} 2026")
        queries.append(f"{question} latest update")
    elif domain == "finance":
        queries.append(f"{question} today market")
        queries.append(f"{question} latest")
    elif domain == "politics":
        queries.append(f"{question} latest news")
        queries.append(f"{question} 2026")
    elif domain == "science":
        queries.append(f"{question} research 2026")
        queries.append(f"{question} latest discovery")
    else:
        queries.append(f"{question} latest")
        queries.append(f"{question} news today")

    seen = set()
    unique = []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            unique.append(q)

    return unique[:4]

async def get_adaptive_style(username: str, history: str) -> str:
    """💀 Tier 8: Analyzes user history to detect preferred language and tone."""
    if not history:
        return "Language: English. Tone: Standard."
        
    prompt = f"""Analyze this chat history and describe the User's preferred communication style in 1 short sentence.
Detect:
- Language (e.g., English, Malayalam, Mixed, etc.)
- Tone (e.g., Concise, Verbose, Funny, Serious)

HISTORY:
{history}

Output only the style description."""
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0)
        )
        return response.text.strip()
    except:
        return "Language: English. Tone: Standard."

async def kairos_query(question: str, files: list = None, complexity: str = "Standard", username: str = "default") -> tuple[str, list]:
    files = files or []
    
    # Step 1: Resolve pronouns 💀
    resolved_question = resolve_pronouns(question, username)

    # Step 2: Cache check on resolved question 😭
    cached = check_cache(resolved_question, username)
    if cached:
        return f"⚡ **Cached:**\n\n{cached}", []

    print(f"🔍 Fetching: {resolved_question}")

    # Step 3: Classify domain FIRST 💀
    domain = classify_domain(resolved_question)
    ambiguities = detect_ambiguity(resolved_question)
    ambiguity_note = "\n".join(ambiguities) if ambiguities else ""
    tone = get_tone_instruction(domain)
    thinking_budget = get_thinking_budget(
        domain, resolved_question
    )

    print(f"📊 Domain: {domain}")
    print(f"🧠 Thinking budget: {thinking_budget}")

    # Step 4: Get history 😭
    history = get_recent_history(username)

    # 💀 Tier 8: Adaptive Style
    adaptive_style = await get_adaptive_style(username, history)
    print(f"🎭 Adaptive Style: {adaptive_style}")

    # Step 5: Expand query — sync, no await 💀
    search_queries = expand_query(
        resolved_question,
        domain,
        history
    )
    print(f"📈 Expanded Queries: {search_queries}")

    # Step 6: Fetch all sources in parallel 😭
    rss_coros = [fetch_rss(q) for q in search_queries]
    search_coros = [
        asyncio.to_thread(fetch_all_search, q)
        for q in search_queries
    ]
    news_coros = [
        asyncio.to_thread(fetch_news, q)
        for q in search_queries
    ]

    try:
        rss_results_list = await asyncio.wait_for(
            asyncio.gather(*rss_coros), timeout=6.0
        )
        rss_results = [
            item for sublist in rss_results_list
            for item in sublist
        ]
    except asyncio.TimeoutError:
        print("⚠️ RSS fetch timed out")
        rss_results = []

    try:
        search_results_list = await asyncio.wait_for(
            asyncio.gather(*search_coros), timeout=8.0
        )
        search_results = [
            item for sublist in search_results_list
            for item in sublist
        ]
    except asyncio.TimeoutError:
        print("⚠️ Search fetch timed out")
        search_results = []

    try:
        news_results_list = await asyncio.wait_for(
            asyncio.gather(*news_coros), timeout=6.0
        )
        news_results = [
            item for sublist in news_results_list
            for item in sublist
        ]
    except asyncio.TimeoutError:
        print("⚠️ News fetch timed out")
        news_results = []

    all_results = rss_results + search_results + news_results
    
    # 💀 Tier 3: Confidence and Source Quality
    verified_results, confidence_score = verify_results(all_results)
    context = format_context(verified_results)
    
    # 💀 Tier 6: Load user memory
    user_prefs = get_user_memory(username)
    user_context = ""
    override_style = ""
    if user_prefs:
        lines = [f"- {k}: {v}" for k, v in user_prefs.items() if k.lower() != "response style"]
        user_context = "USER PREFERENCES:\n" + "\n".join(lines)
        override_style = user_prefs.get("Response Style", "")

    # 💀 Tier 8 Style Priority: Manual Override > Adaptive Style
    effective_style = override_style if override_style else adaptive_style

    prompt = (
    f"You are Kairos, an expert teacher explaining concepts in a way that can be spoken directly in a classroom.\n"
    f"Today: {datetime.date.today()}\n"
    f"Domain: {domain.upper()}\n\n"

    f"{tone}\n"
    f"Complexity Target: {complexity}\n"
    f"Response Style: {effective_style}\n\n"

    f"{user_context}\n\n"

    "═══════════════════════════════════════════\n"
    "TEACHING MODE — SPEAKABLE OUTPUT\n"
    "═══════════════════════════════════════════\n\n"

    "Explain the topic as if you are teaching students LIVE.\n"
    "The explanation must sound natural when read aloud.\n\n"

    "STRUCTURE:\n\n"

    "## [Topic Title]\n\n"

    "### Simple Definition\n"
    "Give a very clear, spoken-style definition in 1–2 lines.\n"
    "Avoid jargon. Keep it conversational.\n\n"

    "### Real-World Understanding\n"
    "Explain how this appears in real life or business in 1–2 lines.\n\n"

    "### Key Concepts\n\n"

    "For each point, follow this EXACT flow:\n\n"

    "**[Number]. [Concept Name]**\n"
    "👉 Say what it does in one clean sentence (like you're speaking)\n\n"

    "Real example:\n"
    "Explain a realistic scenario in simple spoken English.\n"
    "Use tools, companies, or daily life examples.\n\n"

    "💡 Analogy:\n"
    "Give a very simple comparison that anyone can understand instantly.\n\n"

    "IMPORTANT:\n"
    "- Write like you are talking, NOT writing\n"
    "- Avoid robotic or textbook language\n"
    "- Avoid symbols like ### inside sentences\n"
    "- Keep sentences short and clear\n"
    "- Make it easy to read aloud without editing\n"
    "- No citations unless absolutely necessary\n\n"

    "### One-Line Summary\n"
    "👉 Give one powerful sentence that wraps up the idea clearly.\n\n"

    "═══════════════════════════════════════════\n"
    "STYLE RULES\n"
    "═══════════════════════════════════════════\n"
    "- Sound like a confident trainer\n"
    "- Clear, simple, and natural\n"
    "- No over-formatting\n"
    "- No unnecessary technical complexity\n"
    "- Every line should be easy to SPEAK\n\n"

    + (f"AMBIGUITY NOTE: {ambiguity_note}\n\n" if ambiguities else "")

    + f"Context:\n{context}\n\n"
    f"Question: {resolved_question}\n\n"

    "Teach this clearly so it can be spoken directly without editing."
)

    config = types.GenerateContentConfig(
        temperature=0.2,
        thinking_config=types.ThinkingConfig(
            thinking_budget=thinking_budget
        ) if thinking_budget > 0 else None
    )

    # Step 7: Generate answer with error handling 💀
    # 💀 Tier 3: Image Analysation capabilities
    contents_body = [prompt]
    uploaded_files = []
    
    if files:
        print(f"📸 Uploading {len(files)} files for analysis...")
        try:
            for file_path in files:
                # Upload file to Gemini API
                uploaded_file = await asyncio.to_thread(client.files.upload, file=file_path)
                uploaded_files.append(uploaded_file)
                contents_body.append(uploaded_file)
        except Exception as e:
            print(f"File Upload Error: {e}")
            
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=contents_body,
            config=config
        )
    except ResourceExhausted:
        return (
            "⚡ **Kairos is taking a breather**\n\n"
            "Too many questions fired today 😭\n\n"
            "Come back in a few minutes and "
            "Kairos will be ready 🔥"
        ), []
    except Exception as e:
        return (
            f"⚠️ **Something went wrong**\n\n"
            f"Error: `{str(e)}`\n\n"
            "Try again in a moment 💀"
        ), []

    answer = response.text
    
    # 🧼 Clean and Polish (Tier 9 Fixes)
    answer = re.sub(r"\[Image\]", "", answer) # Remove hallucinated placeholders
    answer = answer.strip() # Remove leading/trailing whitespace
    answer = re.sub(r'\n{3,}', '\n\n', answer) # Normalize excessive spacing

    # 💀 Tier 3: Answer Versioning / Diffing
    version_note = ""
    # Retrieve the last known answer to see if there's a big change (e.g., score changed)
    # We can use our get_recent_history but filter for the same exact question
    try:
        from core.memory import collection
        recent = collection.query(query_texts=[resolved_question], n_results=1)
        if recent['documents'] and recent['documents'][0]:
            last_ans = recent['documents'][0][0]
            # Simple heuristic: if length or words changed significantly, flag it
            old_words = set(last_ans.lower().split())
            new_words = set(answer.lower().split())
            if len(old_words) > 0 and len(new_words) > 0:
                overlap = len(old_words & new_words) / max(len(old_words), len(new_words))
                if overlap < 0.7:  # 30% difference in vocabulary represents a meaningful update
                    version_note = "\n\n🔔 *Live Update: Information has changed since your last check.*"
    except Exception:
        pass

    # Step 8: Word limit 😭
    MAX_WORDS = 500
    words_match = list(re.finditer(r'\S+', answer))
    if len(words_match) > MAX_WORDS:
        cutoff = words_match[MAX_WORDS - 1].end()
        answer = (
            answer[:cutoff] +
            "...\n\n*(Note: Answer trimmed to respect "
            "length limit)*"
        )
        
    # Append the confidence and version tags natively to the response
    final_answer = f"🌩️ **Kairos Confidence: {confidence_score}%**\n\n{answer}{version_note}"

    # Step 9: Store 💀
    store_result(resolved_question, final_answer, username)
    
    fetched_source_names = list(set([r.get('source') for r in all_results if r.get('source')]))
    return final_answer, fetched_source_names

async def fact_check_text(text: str, username: str = "default") -> str:
    """💀 Tier 5: Fact Checker Mode. Analyzes text sentence by sentence."""
    if not text.strip():
        return "⚠️ Please paste some text to fact-check!"
        
    # Split by sentences (simple heuristic)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip()]
    if not sentences:
        sentences = [text]
        
    results = []
    print(f"🕵️ Fact-checking {len(sentences)} sentences...")
    
    for i, sent in enumerate(sentences[:10], 1): # Cap at 10 sentences for speed
        print(f"   [{i}/{len(sentences)}] checking: {sent[:50]}...")
        
        # Search for context for this specific sentence
        # We use a slimmed down version of the retrieval flow
        search_results = await asyncio.to_thread(fetch_all_search, sent)
        context = format_context(search_results[:5])
        
        prompt = f"""You are a professional fact-checker.
Compare this sentence against the provided real-time context.
Sentence: "{sent}"

Context:
{context}

Output format:
VERDICT: [TRUE / FALSE / MISLEADING / UNVERIFIED]
EXPLANATION: [1 short sentence explanation]
"""
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0)
            )
            results.append(f"**Sentence {i}:** {sent}\n{response.text.strip()}")
        except Exception as e:
            results.append(f"**Sentence {i}:** {sent}\n⚠️ Error: {e}")
            
    return "## 🕵️ Kairos Fact-Check Results\n\n---\n\n" + "\n\n---\n\n".join(results)

async def check_all_alerts(username: str = "default") -> str:
    """💀 Tier 6: Proactive Alerts. Scans all watch topics for updates."""
    from core.memory import collection
    topics = get_watch_topics(username)
    if not topics:
        return "⚠️ No topics currently being watched."
        
    results = []
    print(f"🔔 Checking alerts for {len(topics)} topics...")
    
    for topic in topics:
        # Search for current news on topic
        search_results = await asyncio.to_thread(fetch_all_search, topic)
        if not search_results:
            continue
            
        current_context = format_context(search_results[:5])
        
        # Check cache for last known answer
        last_answer = ""
        cached = collection.query(query_texts=[topic], n_results=1)
        if cached['documents'] and cached['documents'][0]:
            last_answer = cached['documents'][0][0]
            
        prompt = f"""You are Kairos, monitors for significant changes.
Topic: {topic}

LAST KNOWN INFO:
{last_answer if last_answer else "None"}

NEW REAL-TIME CONTEXT:
{current_context}

Evaluate if there is any NEW significant development.
If YES: Start with "🚨 UPDATE:" and summarize the change in 2 sentences.
If NO: Return "No significant change."
"""
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
            report = response.text.strip()
            if "No significant change" not in report:
                results.append(f"### 👁️ {topic}\n{report}")
        except Exception as e:
            print(f"Alert error for {topic}: {e}")
            
    if not results:
        return "✅ Checked all topics. No significant updates found in the last hour."
        
    return "## 🚨 Proactive Kairos Alerts\n\n" + "\n\n---\n\n".join(results)