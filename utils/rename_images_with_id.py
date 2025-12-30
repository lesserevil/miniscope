import os
import sys
import sqlite3
import shutil

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniscope.database import DB_PATH

def migrate_images():
    print("Renaming existing images to include db ID to prevent collisions...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, image_path FROM miniatures WHERE image_path IS NOT NULL")
    rows = cursor.fetchall()
    
    total = len(rows)
    migrated = 0
    skipped = 0
    errors = 0
    
    for row in rows:
        mini_id = row['id']
        old_path = row['image_path']
        
        if not old_path or not os.path.exists(old_path):
            skipped += 1
            continue
            
        # Check if already prefixed with ID
        filename = os.path.basename(old_path)
        if filename.startswith(f"{mini_id}_"):
            skipped += 1
            continue
            
        new_filename = f"{mini_id}_{filename}"
        new_path = os.path.join(os.path.dirname(old_path), new_filename)
        
        try:
            # Check if destination already exists (could happen if ID_filename exists from previous run or collision)
            # If it exists, we just update the DB if it's the right one, or overwrite if we're sure.
            # In this cleanup, we want to move it to the ID-prefixed one.
            
            if os.path.exists(new_path):
                # If it already exists, maybe a previous half-migration?
                # We'll just update the DB.
                pass
            else:
                shutil.move(old_path, new_path)
            
            cursor.execute("UPDATE miniatures SET image_path = ? WHERE id = ?", (new_path, mini_id))
            migrated += 1
            
            if migrated % 100 == 0:
                print(f"Processed {migrated}/{total}...")
                
        except Exception as e:
            print(f"Error migrating {old_path} to {new_path}: {e}")
            errors += 1
            
    conn.commit()
    conn.close()
    
    print(f"\nMigration complete.")
    print(f"Total: {total}")
    print(f"Migrated: {migrated}")
    print(f"Skipped: {skipped} (Already prefixed or missing)")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    migrate_images()
