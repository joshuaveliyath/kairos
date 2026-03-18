import chromadb
from datetime import datetime
import re

client = chromadb.Client()
collection = client.get_or_create_collection(
    "kairos_memory"
)

def store_result(question: str, answer: str, username: str = "default"):
    try:
        collection.add(
            documents=[answer],
            metadatas=[{
                "question": question,
                "username": username,
                "timestamp": str(datetime.now())
            }],
            ids=[f"q_{username}_{datetime.now().timestamp()}"]
        )
    except Exception as e:
        print(f"Storage Error: {e}")

def check_cache(question: str, username: str = "default") -> str | None:
    try:
        results = collection.query(
            query_texts=[question],
            where={"username": username},
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

                if similarity >= 0.9:
                    print(f"⚡ Cache hit! ({age}s old)")
                    return results['documents'][0][0]
                else:
                    print(f"❌ Cache rejected (too different)")
                    return None

    except:
        pass
    return None

def get_recent_history(username: str = "default", limit: int = 3) -> str:
    try:
        results = collection.get(
            where={"username": username},
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

def get_last_entity(username: str = "default") -> str:
    """
    Extract the most recent named entity 💀
    from conversation history
    Solves: "What did HE announce?" → Elon Musk
    """
    try:
        results = collection.get(
            where={"username": username},
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

    # Extract username if available via context or passed as arg?
    # In processor, it will be passed. Let's add arg.
    # But resolve_pronouns only takes question. Let's fix.
    return question

def resolve_pronouns(question: str, username: str = "default") -> str:
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

    entity = get_last_entity(username)

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

# ─────────────────────────────────────────────
# 💀 TIER 6: Persistent User Memory
# ─────────────────────────────────────────────
_user_profile_collection = client.get_or_create_collection("kairos_user_profile")

def get_user_memory(username: str = "default") -> dict:
    """Retrieve user preferences stored in ChromaDB."""
    try:
        r = _user_profile_collection.get(ids=[f"user_prefs_{username}"])
        if r['documents'] and r['documents'][0]:
            import json
            return json.loads(r['documents'][0])
    except Exception:
        pass
    return {}

def update_user_memory(username: str, key: str, value: str):
    """Update a single user preference field."""
    try:
        import json
        prefs = get_user_memory(username)
        prefs[key] = value
        _user_profile_collection.upsert(
            documents=[json.dumps(prefs)],
            metadatas=[{"updated": str(datetime.now()), "username": username}],
            ids=[f"user_prefs_{username}"]
        )
        print(f"💾 User pref updated for {username}: {key} = {value}")
    except Exception as e:
        print(f"User Memory Error: {e}")

# ─────────────────────────────────────────────
# 💀 TIER 6: Source Reputation System (base 50)
# ─────────────────────────────────────────────
_reputation_collection = client.get_or_create_collection("kairos_source_reputation")

def get_source_reputation(source_name: str) -> int:
    """Get reputation score for a source. Returns a value 0-100 (base 50)."""
    try:
        r = _reputation_collection.get(ids=[f"src_{source_name}"])
        if r['documents'] and r['documents'][0]:
            return int(r['documents'][0])
    except Exception:
        pass
    return 50  # default base score

def update_source_reputation(source_name: str, delta: int):
    """Adjust source reputation by +/- delta. Clamped to 0-100."""
    try:
        current = get_source_reputation(source_name)
        new_score = max(0, min(100, current + delta))
        _reputation_collection.upsert(
            documents=[str(new_score)],
            metadatas=[{
                "source": source_name,
                "last_updated": str(datetime.now())
            }],
            ids=[f"src_{source_name}"]
        )
        arrow = "📈" if delta > 0 else "📉"
        print(f"{arrow} {source_name} reputation: {current} → {new_score}")
        return new_score
    except Exception as e:
        print(f"Reputation Error: {e}")
        return 50

# ─────────────────────────────────────────────
# 💀 TIER 6: Proactive Alert Watching System
# ─────────────────────────────────────────────
_alerts_collection = client.get_or_create_collection("kairos_watch_topics")

def add_watch_topic(topic: str, username: str = "default"):
    """Register a topic for proactive alert watching."""
    try:
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', topic[:50])
        _alerts_collection.upsert(
            documents=[topic],
            metadatas=[{"added": str(datetime.now()), "last_checked": "", "username": username}],
            ids=[f"watch_{username}_{safe_id}"]
        )
        print(f"👁️ Watching for {username}: {topic}")
    except Exception as e:
        print(f"Watch Error: {e}")

def get_watch_topics(username: str = "default") -> list[str]:
    """Return all registered watch topics."""
    try:
        r = _alerts_collection.get(where={"username": username}, include=['documents'])
        return r['documents'] if r['documents'] else []
    except Exception:
        return []

def remove_watch_topic(topic: str, username: str = "default"):
    """Remove a topic from the watch list."""
    try:
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', topic[:50])
        _alerts_collection.delete(ids=[f"watch_{username}_{safe_id}"])
        print(f"🗑️ Unwatched for {username}: {topic}")
    except Exception as e:
        print(f"Unwatch Error: {e}")