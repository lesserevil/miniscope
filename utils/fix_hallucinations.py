import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniscope.database import get_db_connection
from miniscope.ai import AIClient
import json

def fix_urns():
    client = AIClient()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find all urn hallucinations
        cursor.execute("SELECT id, name, image_path FROM miniatures WHERE vision_description LIKE '%urn%'")
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} problematic 'urn' descriptions.")
        
        for row in rows:
            mini_id = row['id']
            name = row['name']
            image_path = row['image_path']
            
            if image_path and os.path.exists(image_path):
                print(f"Re-analyzing {name} (ID: {mini_id})...")
                try:
                    desc = client.generate_description(image_path)
                    print(f"  -> New Description: {desc[:50]}...")
                    
                    text = f"{name} {desc}"
                    emb = client.get_embedding(text)
                    
                    cursor.execute("""
                        UPDATE miniatures 
                        SET vision_description = ?, embedding = ?
                        WHERE id = ?
                    """, (desc, json.dumps(emb), mini_id))
                    conn.commit()
                except Exception as e:
                    print(f"  Error: {e}")
            else:
                print(f"  Skipping {name} - Image not found at {image_path}")

if __name__ == "__main__":
    fix_urns()
