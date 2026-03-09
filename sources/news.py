from newsapi import NewsApiClient
import os

def fetch_news(query: str) -> list:
    try:
        newsapi = NewsApiClient(
            api_key=os.getenv("NEWS_API_KEY")
        )

        articles = newsapi.get_everything(
            q=query,
            language='en',
            sort_by='publishedAt',
            page_size=10
        )

        results = []
        for article in articles['articles']:
            results.append({
                "source": article['source']['name'],
                "title": article['title'],
                "content": article.get(
                    'description', '')[:500],
                "url": article['url'],
                "published": article['publishedAt'],
                "freshness": "minutes",
                "engine": "newsapi"
            })
        return results
    except Exception as e:
        print(f"NewsAPI Error: {e}")
        return []