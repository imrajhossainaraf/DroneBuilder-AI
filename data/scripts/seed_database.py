"""
DroneMate – Database Seeder
Run from project root:  python data/scripts/seed_database.py
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "seed_data")

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  ⚠️  {filename} not found – skipping.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def seed():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]

    print(f"\n🚀 Seeding database: {MONGO_DB_NAME}\n")

    collections = {
        "drone_knowledge":       "knowledge_base.json",
        "drone_components":      "components.json",
        "troubleshooting_cases": "troubleshooting.json",
        "build_guides":          "build_guides.json",
    }

    for collection_name, filename in collections.items():
        data = load_json(filename)
        if not data:
            continue
        col = db[collection_name]
        col.drop()   # fresh seed each time
        result = col.insert_many(data)
        print(f"  ✅ {collection_name}: inserted {len(result.inserted_ids)} documents")

    # Create indexes for faster search
    db.drone_knowledge.create_index([("keywords", 1)])
    db.drone_knowledge.create_index([("category", 1)])
    db.conversations.create_index([("session_id", 1)])
    print("\n  🔑 Indexes created.")

    print("\n✅ Seeding complete!\n")
    client.close()

if __name__ == "__main__":
    seed()
