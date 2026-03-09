import chromadb
from datetime import datetime
import re

client = chromadb.Client()
collection = client.get_or_create_collection(
    "kairos_memory"
)

def store_result(question: str, answer: str):
    try:
        collection.add(
            documents=[answer],
            metadatas=[{
                "question": question,
                "timestamp": str(datetime.now())
            }],
            ids=[f"q_{datetime.now().timestamp()}"]
        )
    except Exception as e:
        print(f"Storage Error: {e}")

def check_cache(question: str) -> str | None:
    try:
        results = collection.query(
            query_texts=[question],
            n_results=1
        )

        if results['documents'][0]:
            metadata = results['metadatas'][0][0]
            cached_time = datetime.fromisoformat(
                metadata['timestamp']
            )
            age = (datetime.now() - cached_time).seconds

            if age < 300:
                cached_question = metadata.get('question', '')

                original_words = set(
                    cached_question.lower().split()
                )
                new_words = set(
                    question.lower().split()
                )

                overlap = len(original_words & new_words)
                total = len(original_words | new_words)
                similarity = overlap / total if total > 0 else 0

                print(f"🔄 Cache similarity: {similarity:.2f}")

                if similarity >= 0.4:
                    print(f"⚡ Cache hit! ({age}s old)")
                    return results['documents'][0][0]
                else:
                    print(f"❌ Cache rejected (too different)")
                    return None

    except:
        pass
    return None

def get_recent_history(limit: int = 3) -> str:
    try:
        results = collection.get(
            limit=limit,
            include=['documents', 'metadatas']
        )

        if not results['documents']:
            return ""

        paired = list(zip(
            results['documents'],
            results['metadatas']
        ))
        paired.sort(
            key=lambda x: datetime.fromisoformat(
                x[1]['timestamp']
            )
        )

        history = []
        for doc, meta in paired[-limit:]:
            q = meta.get('question', '')
            a = doc
            if len(a.split()) > 50:
                a = " ".join(a.split()[:50]) + "..."
            history.append(f"User: {q}\nKairos: {a}")

        return "\n\n".join(history)
    except Exception as e:
        print(f"Memory Error: {e}")
        return ""

def get_last_entity() -> str:
    """
    Extract the most recent named entity 💀
    from conversation history
    Solves: "What did HE announce?" → Elon Musk
    """
    try:
        results = collection.get(
            limit=5,
            include=['metadatas']
        )

        if not results['metadatas']:
            return ""

        # Sort by timestamp newest first 😭
        metas = sorted(
            results['metadatas'],
            key=lambda x: datetime.fromisoformat(
                x['timestamp']
            ),
            reverse=True
        )

        # Pronouns that indicate reference to entity 💀
        pronouns = [
            "he", "she", "they", "him", "her",
            "his", "their", "it", "this", "that"
        ]

        # Common words to ignore 😭
        stop_words = {
            "who", "what", "where", "when", "why",
            "how", "is", "are", "was", "were", "the",
            "a", "an", "and", "or", "but", "in", "on",
            "at", "to", "for", "of", "with", "by"
        }

        # Look through recent questions for named entities
        for meta in metas:
            q = meta.get('question', '')
            words = q.split()

            # Skip if this question itself uses pronouns 💀
            if any(p in q.lower().split() for p in pronouns):
                continue

            # Extract capitalized words = likely names 😭
            entities = [
                w.strip('?,.')
                for w in words
                if w[0].isupper()
                and w.lower() not in stop_words
                and len(w) > 2
            ]

            if entities:
                # Return most likely full name 💀
                # Join consecutive capitalized words
                full_entity = []
                for i, w in enumerate(words):
                    clean = w.strip('?,.')
                    if (clean[0].isupper()
                            and clean.lower() not in stop_words
                            and len(clean) > 2):
                        full_entity.append(clean)
                    elif full_entity:
                        break

                if full_entity:
                    entity = " ".join(full_entity)
                    print(f"🧠 Last entity: {entity}")
                    return entity

        return ""

    except Exception as e:
        print(f"Entity Error: {e}")
        return ""

def resolve_pronouns(question: str) -> str:
    """
    Replace pronouns with actual entity 💀
    "What did he announce?" → 
    "What did Elon Musk announce?"
    """
    pronouns = [
        "he", "she", "they", "him", "her",
        "his", "their", "it"
    ]

    q_lower = question.lower()
    has_pronoun = any(
        f" {p} " in f" {q_lower} "
        for p in pronouns
    )

    if not has_pronoun:
        return question  # no pronouns, return as is 😭

    entity = get_last_entity()

    if not entity:
        return question  # no entity found, return as is 💀

    # Replace pronouns with entity 😭
    resolved = question
    for pronoun in pronouns:
        pattern = re.compile(
            rf'\b{pronoun}\b',
            re.IGNORECASE
        )
        resolved = pattern.sub(entity, resolved)

    print(f"🔗 Resolved: '{question}' → '{resolved}'")
    return resolved