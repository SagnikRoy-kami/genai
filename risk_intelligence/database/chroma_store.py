import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json
import chromadb
from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION


def get_client():
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


# ── Ingest ──────────────────────────────────────────────────────────

def ingest_company_history(json_path: str = "data/company_history.json"):
    """Load sample company history into ChromaDB for RAG retrieval."""
    with open(json_path) as f:
        records = json.load(f)

    collection = get_collection()

    ids, documents, metadatas = [], [], []
    for rec in records:
        doc_id = rec["id"]
        ids.append(doc_id)
        documents.append(rec["text"])
        metadatas.append({
            "category": rec.get("category", "general"),
            "year": str(rec.get("year", "")),
            "source": rec.get("source", "internal"),
        })

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"  Ingested {len(ids)} company history records into ChromaDB.")


# ── Query ───────────────────────────────────────────────────────────

def query_company_history(query: str, n_results: int = 5, categories: list = None, source_filter: str = None) -> list:
    """Retrieve relevant history with optional metadata filtering."""
    collection = get_collection()
    if collection.count() == 0:
        return []

    # Build metadata filter
    where_filter = None
    conditions = []

    if categories:
        if len(categories) == 1:
            conditions.append({"category": {"$eq": categories[0]}})
        else:
            conditions.append({"category": {"$in": categories}})

    if source_filter:
        conditions.append({"source": {"$eq": source_filter}})

    if len(conditions) == 1:
        where_filter = conditions[0]
    elif len(conditions) > 1:
        where_filter = {"$and": conditions}

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )
    except Exception:
        # Fallback without filter if filter fails
        results = collection.query(query_texts=[query], n_results=n_results)

    docs = []
    for i in range(len(results["ids"][0])):
        docs.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })

    # Filter out low-relevance results (distance > 1.5 means weak match)
    docs = [d for d in docs if d.get("distance") is None or d["distance"] < 1.5]

    return docs
