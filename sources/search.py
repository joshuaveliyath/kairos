from ddgs import DDGS

def fetch_duckduckgo(query: str) -> list:
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(
                query,
                max_results=10,
                timelimit='d'
            ):
                results.append({
                    "source": f"DDG: {r.get('source','Web')}",
                    "title": r.get('title', ''),
                    "content": r.get('body', '')[:500],
                    "url": r.get('href', ''),
                    "published": "Recent",
                    "freshness": "minutes",
                    "engine": "duckduckgo"
                })
        return results
    except Exception as e:
        print(f"DDG Error: {e}")
        return []

def fetch_all_search(query: str) -> list:
    return fetch_duckduckgo(query)