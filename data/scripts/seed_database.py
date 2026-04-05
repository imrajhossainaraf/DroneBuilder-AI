"""
DroneMate – Database Seeder
Run from project root:  python data/scripts/seed_database.py
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from pymongo import MongoClient, TEXT, ASCENDING, DESCENDING
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

    print("\n  🔑 Creating indexes...\n")

    # ── drone_knowledge ──
    db.drone_knowledge.create_index([("keywords", ASCENDING)])
    db.drone_knowledge.create_index([("category", ASCENDING)])
    db.drone_knowledge.create_index([("difficulty", ASCENDING)])
    db.drone_knowledge.create_index(
        [("question", TEXT), ("answer", TEXT), ("keywords", TEXT)],
        name="knowledge_text_search",
        weights={"question": 10, "keywords": 5, "answer": 1},
    )
    print("  ✅ drone_knowledge: keyword + text indexes created")

    # ── troubleshooting_cases ──
    db.troubleshooting_cases.create_index([("keywords", ASCENDING)])
    db.troubleshooting_cases.create_index([("category", ASCENDING)])
    db.troubleshooting_cases.create_index([("severity", ASCENDING)])
    db.troubleshooting_cases.create_index(
        [("problem", TEXT), ("keywords", TEXT)],
        name="troubleshooting_text_search",
        weights={"problem": 10, "keywords": 5},
    )
    print("  ✅ troubleshooting_cases: keyword + text indexes created")

    # ── drone_components ──
    db.drone_components.create_index([("component_type", ASCENDING)])
    db.drone_components.create_index([("brand", ASCENDING)])
    db.drone_components.create_index([("rating", DESCENDING)])
    db.drone_components.create_index([("use_cases", ASCENDING)])
    db.drone_components.create_index(
        [("name", TEXT), ("brand", TEXT)],
        name="components_text_search",
    )
    print("  ✅ drone_components: indexes created")

    # ── build_guides ──
    db.build_guides.create_index([("drone_type", ASCENDING)])
    db.build_guides.create_index([("difficulty", ASCENDING)])
    db.build_guides.create_index([("tags", ASCENDING)])
    print("  ✅ build_guides: indexes created")

    # ── conversations ──
    db.conversations.create_index([("session_id", ASCENDING)], unique=True)
    db.conversations.create_index([("last_updated", DESCENDING)])
    print("  ✅ conversations: session_id unique index created")

    # ── user_feedback ──
    db.user_feedback.create_index([("conversation_id", ASCENDING)])
    db.user_feedback.create_index([("timestamp", DESCENDING)])
    print("  ✅ user_feedback: indexes created")

    print("\n✅ Seeding complete!\n")
    client.close()


if __name__ == "__main__":
    seed()
