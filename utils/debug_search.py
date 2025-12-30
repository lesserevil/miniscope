import os
import sys
import json
import numpy as np
import re

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniscope.database import get_db_connection
from miniscope.ai import AIClient

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def debug_search(query):
    print(f"Query: '{query}'")
    client = AIClient()
    q_emb = client.get_embedding(query)
    
    query_tokens = [t.lower() for t in query.split() if len(t) > 2]

    with get_db_connection() as conn:
        rows = conn.execute("SELECT id, name, vision_description, embedding, set_name FROM miniatures WHERE embedding IS NOT NULL").fetchall()
        
        results = []
        for row in rows:
            emb = json.loads(row['embedding'])
            score = cosine_similarity(q_emb, emb)
            
            # App Logic: Token Boost + Penalty
            searchable_text = (row['name'] + " " + (row['vision_description'] or "") + " " + row['set_name']).lower()
            boost = 0
            any_word_match = False
            for token in query_tokens:
                if re.search(r'\b' + re.escape(token) + r'\b', searchable_text):
                    boost += 0.25
                    any_word_match = True
            
            if not any_word_match and len(query_tokens) > 0:
                score -= 0.15
            
            score += boost
            
            if score > 0.60:
                results.append({
                    "name": row['name'],
                    "desc": (row['vision_description'] or "")[:80] + "...",
                    "score": score,
                    "base_score": score - boost + (0.15 if not any_word_match else 0)
                })
            
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print("\nResults (Threshold 0.60):")
    for r in results[:20]:
        print(f"{r['score']:.4f} | {r['name']} | (Base: {r['base_score']:.4f})")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "archer"
    debug_search(q)
