import asyncio
import os
import sys
import logging
from typing import Dict, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniscope.scraper import Scraper, BASE_URL
from miniscope.database import get_db_connection, get_db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def refresh_placeholders():
    scraper = Scraper()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find all minis with 'unknown.jpg'
        cursor.execute("""
            SELECT id, name, set_name, image_url 
            FROM miniatures 
            WHERE image_url LIKE '%unknown.jpg%'
        """)
        rows = cursor.fetchall()
        
        if not rows:
            print("No 'unknown' placeholders found in database.")
            return

        print(f"Found {len(rows)} miniatures with 'unknown.jpg' placeholders.")
        
        # Group by set for efficient scraping
        sets_to_refresh: Dict[str, List[dict]] = {}
        for row in rows:
            s_name = row['set_name']
            if s_name not in sets_to_refresh:
                sets_to_refresh[s_name] = []
            sets_to_refresh[s_name].append(dict(row))

        total_updated = 0
        
        for set_id, minis in sets_to_refresh.items():
            print(f"\nChecking set: {set_id} ({len(minis)} placeholders)...")
            
            url = f"{BASE_URL}/index.php?id={set_id}"
            soup = await scraper.fetch_page(url)
            
            if not soup:
                print(f"  Failed to fetch set page for {set_id}")
                continue
            
            # Parse all minis on the current live page
            live_minis = scraper.parse_miniatures(soup, set_id, "Unknown Line")
            live_map = {m.name: m for m in live_minis}
            
            for mini in minis:
                mini_id = mini['id']
                name = mini['name']
                
                if name in live_map:
                    new_url = live_map[name].image_url
                    
                    if "unknown.jpg" not in new_url.lower():
                        print(f"  [UPDATE] Found real image for '{name}': {new_url}")
                        
                        # Download new image
                        new_path = await scraper.download_image(new_url, mini_id)
                        
                        if new_path:
                            # Run AI analysis
                            print(f"  [AI] Analyzing updated image...")
                            desc = scraper.ai.generate_description(new_path, name=name)
                            text_for_embedding = f"{name} {desc}"
                            emb = scraper.ai.get_embedding(text_for_embedding)
                            
                            import json
                            with get_db_cursor() as update_cursor:
                                update_cursor.execute("""
                                    UPDATE miniatures 
                                    SET image_url = ?, image_path = ?, vision_description = ?, embedding = ?
                                    WHERE id = ?
                                """, (new_url, new_path, desc, json.dumps(emb), mini_id))
                            
                            total_updated += 1
                        else:
                            print(f"  [ERROR] Failed to download {new_url}")
                    else:
                        print(f"  [SKIP] '{name}' is still unknown on the source site.")
                else:
                    print(f"  [INFO] '{name}' not found on the current set page (name may have changed?).")

            # Be nice to the server
            await asyncio.sleep(1.0)

    await scraper.close()
    print(f"\nRefresh complete. Updated {total_updated} placeholders.")

if __name__ == "__main__":
    asyncio.run(refresh_placeholders())
