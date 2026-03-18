import feedparser
import asyncio

RSS_FEEDS = {
    "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
    "Reuters": "https://feeds.reuters.com/reuters/topNews",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Hacker News": "https://news.ycombinator.com/rss",
    "The Hindu": "https://www.thehindu.com/news/feeder/default.rss",
    "Times of India": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "Google News": "https://news.google.com/rss",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "NDTV": "https://feeds.feedburner.com/ndtvnews-top-stories",
    "India Today": "https://www.indiatoday.in/rss/home",
    "ESPNCricinfo": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
    "CricTracker": "https://www.crictracker.com/feed/",
}

async def fetch_feed(source: str, url: str, query_words: list, query: str) -> list:
    try:
        # Use to_thread for the blocking feedparser.parse call
        feed = await asyncio.to_thread(feedparser.parse, url)
        results = []
        for entry in feed.entries[:10]:
            from difflib import SequenceMatcher
            
            title_lower = entry.title.lower()
            summary = entry.get("summary", "")
            
            # Check for fuzzy overlap
            match_score = SequenceMatcher(None, query.lower(), title_lower).ratio()
            
            # Also check if multiple query words exist
            words_found = sum(1 for word in query_words if len(word) > 3 and word in title_lower)
            word_match_ratio = words_found / max(1, len([w for w in query_words if len(w) > 3]))
            
            is_match = match_score > 0.3 or word_match_ratio >= 0.5 or any(word in title_lower for word in query_words if len(word) > 5)

            if is_match:
                results.append({
                    "source": source,
                    "title": entry.title,
                    "content": summary[:500],
                    "url": entry.get("link", ""),
                    "published": entry.get("published", "Just now"),
                    "freshness": "seconds",
                    "engine": "rss"
                })
        return results
    except Exception as e:
        print(f"RSS Error {source}: {e}")
        return []

async def fetch_rss(query: str) -> list:
    query_words = query.lower().split()
    tasks = [fetch_feed(source, url, query_words, query) for source, url in RSS_FEEDS.items()]
    results_list = await asyncio.gather(*tasks)
    
    # Flatten results
    return [item for sublist in results_list for item in sublist]