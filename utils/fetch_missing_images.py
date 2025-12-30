import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import httpx
import asyncio
import json
from tqdm import tqdm
from miniscope.ai import AIClient

DB_PATH = "miniscope.db"
IMAGE_DIR = "data/images"

async def redownload():
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find all minis with image_url but missing file on disk or missing path in DB
    cursor.execute("SELECT id, name, image_url, image_path FROM miniatures WHERE image_url IS NOT NULL AND image_url != ''")
    rows = cursor.fetchall()
    
    missing = []
    for row in rows:
        path = row['image_path']
        if not path or not os.path.exists(path):
            missing.append(row)

    if not missing:
        print("No missing images found.")
        return

    print(f"Found {len(missing)} missing images. Downloading...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        ai = AIClient()
        for row in tqdm(missing, unit="img"):
            url = row['image_url']
            name = row['name']
            mini_id = row['id']
            
            # Use filename from URL with ID prefix as in scraper.py
            raw_filename = url.split("/")[-1]
            filename = f"{mini_id}_{raw_filename}"
            filepath = os.path.join(IMAGE_DIR, filename)

            try:
                response = await client.get(url)
                if response.status_code == 200:
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    
                    # Update DB with the correct path
                    cursor.execute("UPDATE miniatures SET image_path = ? WHERE id = ?", (filepath, mini_id))
                    conn.commit()

                    # Re-run AI analysis
                    tqdm.write(f"  Analyzing {name}...")
                    desc = ai.generate_description(filepath, name=name)
                    if desc:
                        text = f"{name} {desc}"
                        emb = ai.get_embedding(text)
                        cursor.execute("""
                            UPDATE miniatures 
                            SET vision_description = ?, embedding = ?
                            WHERE id = ?
                        """, (desc, json.dumps(emb), mini_id))
                        conn.commit()
                else:
                    tqdm.write(f"  Failed to download {name}: HTTP {response.status_code}")
            except Exception as e:
                tqdm.write(f"  Error processing {name}: {e}")
            
            await asyncio.sleep(0.5)

    conn.close()

if __name__ == "__main__":
    asyncio.run(redownload())
