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
    resolve_pronouns
)
import os

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
        context += f"""
[{i}] Source: {r['source']}
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

async def kairos_query(question: str) -> str:

    # Step 1: Resolve pronouns 💀
    resolved_question = resolve_pronouns(question)

    # Step 2: Cache check on resolved question 😭
    cached = check_cache(resolved_question)
    if cached:
        return f"⚡ **Cached:**\n\n{cached}"

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
    history = get_recent_history()

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
    verified_results = verify_results(all_results)
    context = format_context(verified_results)

    prompt = f"""You are Kairos, a real-time AI assistant.
Today: {datetime.date.today()}
Query domain: {domain.upper()}

{tone}

CONVERSATION HISTORY:
{history if history else "No previous context."}

RESPONSE STRUCTURE:
Use rich Markdown formatting:
- **Bold** for key terms and primary answer
- *Italics* for emphasis
- Bullet points for multiple items
- Short readable paragraphs
- End with numbered citations

TIMELINE RULES (critical):
- Past events → past tense only
- Current status → present tense only
- Future events → clearly labeled "Upcoming:" or "Today:"
- NEVER mix tenses in same sentence

CITATION FORMAT:
- Use [1] [2] [3] inline after every fact
- End response with:
  Sources:
  [1] Source name — URL
  [2] Source name — URL

RULES:
- NEVER state facts without [citation]
- NEVER say "Based on live data..." ❌
- NEVER say "As of today..." ❌
- NEVER say "Great question!" ❌
- NEVER mix tenses ❌
- Confident, direct, journalist tone
- For predictions: give confident opinion
- For news: lead with most important fact
- For sports: lead with result or prediction

{f'AMBIGUITY NOTE: {ambiguity_note}' if ambiguities else ''}

Numbered sources for citations:
{context}

Question: {resolved_question}

Answer directly. Lead with the point."""

    config = types.GenerateContentConfig(
        temperature=0.2,
        thinking_config=types.ThinkingConfig(
            thinking_budget=thinking_budget
        ) if thinking_budget > 0 else None
    )

    # Step 7: Generate answer with error handling 💀
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
    except ResourceExhausted:
        return (
            "⚡ **Kairos is taking a breather**\n\n"
            "Too many questions fired today 😭\n\n"
            "Come back in a few minutes and "
            "Kairos will be ready 🔥"
        )
    except Exception as e:
        return (
            f"⚠️ **Something went wrong**\n\n"
            f"Error: `{str(e)}`\n\n"
            "Try again in a moment 💀"
        )

    answer = response.text

    # Step 8: Word limit 😭
    MAX_WORDS = 250
    words = answer.split()
    if len(words) > MAX_WORDS:
        answer = (
            " ".join(words[:MAX_WORDS]) +
            "...\n\n*(Note: Answer trimmed to respect "
            "250 word limit)*"
        )

    # Step 9: Store 💀
    store_result(resolved_question, answer)
    return answer