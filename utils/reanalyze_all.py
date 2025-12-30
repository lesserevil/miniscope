import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniscope.database import get_db_connection
from miniscope.ai import AIClient
import json
import argparse
from tqdm import tqdm

def reanalyze_all(force=False):
    client = AIClient()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if force:
            print("Force flag set. Clearing all existing descriptions and embeddings...")
            cursor.execute("UPDATE miniatures SET vision_description = NULL, embedding = NULL")
            conn.commit()
        
        # Select only miniatures that don't have a description yet
        cursor.execute("SELECT id, name, image_path FROM miniatures WHERE vision_description IS NULL")
        rows = cursor.fetchall()
        
        total = len(rows)
        if total == 0:
            print("No miniatures need re-analysis (all have descriptions). Use --force to redo all.")
            return

        print(f"Re-analyzing {total} miniatures...")
        
        pbar = tqdm(rows, unit="mini")
        for row in pbar:
            mini_id = row['id']
            name = row['name']
            image_path = row['image_path']
            
            pbar.set_description(f"Re-analyzing {name}")
            
            if image_path and os.path.exists(image_path):
                try:
                    desc = client.generate_description(image_path, name=name)
                    
                    if desc:
                        text = f"{name} {desc}"
                        emb = client.get_embedding(text)
                        
                        cursor.execute("""
                            UPDATE miniatures 
                            SET vision_description = ?, embedding = ?
                            WHERE id = ?
                        """, (desc, json.dumps(emb), mini_id))
                        conn.commit()
                except Exception as e:
                    tqdm.write(f"  Error processing {name}: {e}")
            else:
                tqdm.write(f"  Skipping {name} (Image missing)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-analyze miniatures using AI vision.")
    parser.add_argument("--force", action="store_true", help="Null out all descriptions and start from scratch.")
    args = parser.parse_args()
    
    reanalyze_all(force=args.force)
