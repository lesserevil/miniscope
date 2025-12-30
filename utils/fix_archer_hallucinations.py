import sqlite3
import os
import logging
import json
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniscope.ai import AIClient
from miniscope.database import get_db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_archers():
    ai = AIClient()
    
    with get_db_cursor() as cursor:
        # Find anything with 'archer' or 'archon' in description that shouldn't be matched
        # Or just anything mentioning 'archer' in description to be safe
        cursor.execute("SELECT id, name, image_path, vision_description FROM miniatures WHERE vision_description LIKE '%archer%'")
        rows = cursor.fetchall()
        
        logger.info(f"Checking {len(rows)} potential archer hallucinations...")
        
        for row in rows:
            mini_id = row['id']
            name = row['name']
            image_path = row['image_path']
            old_desc = row['vision_description']
            
            if not image_path or not os.path.exists(image_path):
                logger.warning(f"Image not found for {name}: {image_path}")
                continue
                
            logger.info(f"Re-analyzing {name}...")
            new_desc = ai.generate_description(image_path, name=name)
            
            # Re-generate embedding
            text_for_embedding = f"{name} {new_desc}"
            new_emb = ai.get_embedding(text_for_embedding)
            
            # Update DB
            cursor.execute("UPDATE miniatures SET vision_description = ?, embedding = ? WHERE id = ?", (new_desc, json.dumps(new_emb), mini_id))
            logger.info(f"Updated {name} (desc + embedding).")

if __name__ == "__main__":
    fix_archers()
