import chromadb

print("Connecting to ChromaDB...")

# 1. Point to your database folder
# (Change this path if your chroma folder is named something else or is inside /data)
client = chromadb.PersistentClient(path="./data/chroma_db")

# 2. See what collections (tables) exist
collections = client.list_collections()
print(f"\nFound collections: {[c.name for c in collections]}")

if collections:
    # 3. Open the first collection
    collection = client.get_collection(collections[0].name)
    
    # 4. Count the total records (This should say 4000+!)
    total_records = collection.count()
    print(f"\nTotal records securely stored: {total_records}")
    
    # 5. Look at the actual English text of 2 records
    print("\n--- PEEKING AT 2 RECORDS ---")
    data = collection.peek(limit=2)
    
    for i in range(len(data['ids'])):
        print(f"ID: {data['ids'][i]}")
        print(f"Text: {data['documents'][i]}")
        print(f"Metadata: {data['metadatas'][i]}")
        print("-" * 40)