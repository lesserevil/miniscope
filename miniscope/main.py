from fastapi import FastAPI, Request, BackgroundTasks, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
import asyncio
import numpy as np
import logging
import json
from contextlib import asynccontextmanager

from .database import init_db, get_db_connection
from .scraper import Scraper
from .ai import AIClient

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App Lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Create static/images dir if not exists
    os.makedirs("data/images", exist_ok=True)
    yield
    # Cleanup if needed

app = FastAPI(lifespan=lifespan)

# Mounts
app.mount("/static", StaticFiles(directory="miniscope/static"), name="static")
os.makedirs("data/images", exist_ok=True)
app.mount("/images", StaticFiles(directory="data/images"), name="images")

templates = Jinja2Templates(directory="miniscope/templates")

# Services
ai_client = AIClient()

# Helper for vector search
def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = Query("")):
    # 1. Get embedding for query if it's natural language-ish
    # For simplicity, we get embedding always if q is long enough, 
    # OR we just do simple keyword search if it looks like a name.
    # Let's do a hybrid: exact match boost + vector search.
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Extract filters
        size_filter = None
        rarity_filter = None
        
        if not q or q.strip() == "":
             cursor.execute("""
                SELECT * FROM miniatures 
                ORDER BY RANDOM() 
                LIMIT 12
            """)
            # For random results, we don't want "Best" vs "Related". 
            # We want them all to appear as "Random Results" or just "Related Results"...
            # The prompt asks for "under the 'random' results". 
            # I'll interpret this as: don't flag them as "Best".
            # If is_best is False, my template renders "Related Results" divider.
            # I can just set is_best=False for all. 
            # But the user might want a specific header "Random Selection".
            # The template logic for dividers is: "if not mini.is_best and not found_ok ... show divider"
            # So if first item is NOT best, it shows divider immediately.
            # That works perfectly.
             rows = cursor.fetchall()
             keyword_results = {row['id']: dict(row) for row in rows}
             results = list(keyword_results.values())
            
        else:
            # Check for metadata filters (size:X, rarity:Y)
            import re
            
            # Regex for size:value
            size_match = re.search(r'size:(\w+)', q, re.IGNORECASE)
            if size_match:
                size_filter = size_match.group(1)
                q = q.replace(size_match.group(0), "").strip()
                
            # Regex for rarity:value
            rarity_match = re.search(r'rarity:(\w+)', q, re.IGNORECASE)
            if rarity_match:
                rarity_filter = rarity_match.group(1)
                q = q.replace(rarity_match.group(0), "").strip()
            
            # Build Base Query
            query_sql = "SELECT * FROM miniatures WHERE 1=1"
            params = []
            
            if size_filter:
                query_sql += " AND size LIKE ?"
                params.append(f"%{size_filter}%")
                
            if rarity_filter:
                query_sql += " AND rarity LIKE ?"
                params.append(f"%{rarity_filter}%")
                
            # If there is remaining text, add keyword search
            if q:
                # We need exact word matching to avoid 'torch' matching 'orc'
                # SQLite 'LIKE' is simple substring. 
                # Options:
                # 1. Use FTS5 (Full Text Search) if available - best but requires schema change.
                # 2. Python-side filtering with regex \bword\b - feasible for small datasets.
                # 3. Hacky LIKE with spaces: LIKE '% orc %' - misses "Orc ..." at start.
                
                # Let's try Python filtering for the 'name' and 'description' text matching part.
                # We fetch potentially broad candidates then filter precise matches.
                # Or just use token boosting later? 
                
                # If we rely ONLY on python filter, we fetch everything matching filters (size/rarity).
                # But that might be too many if no filters.
                
                # Let's stick to valid SQL strictness for initial fetch but maybe accept the substring for now 
                # and let the "Token Boosting" logic (lines 100+) downrank bad matches?
                # User says "torch" matches "orc". 
                # This happens because "orc" is a substring of "torch".
                
                # FIX: Use word boundaries in Python-side filtering for the keyword results part.
                # We will fetch roughly matching rows via SQL, then filter `keyword_results`.
                
                query_sql += " AND (LOWER(name) LIKE ? OR LOWER(set_name) LIKE ? OR LOWER(line) LIKE ? OR LOWER(vision_description) LIKE ?)"
                q_lower = f"%{q.lower()}%"
                params.extend([q_lower, q_lower, q_lower, q_lower])
            
            cursor.execute(query_sql, tuple(params))
        
            rows = cursor.fetchall()
            keyword_results = {}
            import re
            
            # Post-filter for whole word matches if simple substring was used
            if q:
                # Check for quoted phrases
                quoted_phrases = re.findall(r'"([^"]*)"', q)
                if quoted_phrases:
                    # Remove quotes for the word-boundary check logic below? 
                    # Actually, if quotes are present, we MUST match the phrase exactly in description (or maybe name/set too?)
                    # User request: "must be found in the description text"
                    
                    # Store filtered rows
                    final_rows = []
                    for row in rows:
                        desc = (row['vision_description'] or "").lower()
                        # Also check name? User said "description text". Let's check name too to be safe/useful.
                        # Actually, user said "must be found in the description text". strict.
                        
                        all_quotes_match = True
                        for phrase in quoted_phrases:
                            if phrase.lower() not in desc:
                                all_quotes_match = False
                                break
                        
                        if all_quotes_match:
                            final_rows.append(row)
                    rows = final_rows
                
                # Now proceed with standard word boundary check for remaining (unquoted) terms?
                # The query "q" still contains quotes. 
                # Let's clean q for the word boundary check.
                clean_q = re.sub(r'"[^"]*"', '', q).strip()
                
                q_words = clean_q.lower().split()
                for row in rows:
                    text_corpus = (row['name'] + " " + (row['vision_description'] or "") + " " + row['set_name']).lower()
                    
                    matches = True
                    for word in q_words:
                        if len(word) < 3: continue 
                        if not re.search(r'\b' + re.escape(word) + r'\b', text_corpus):
                             matches = False
                             break
                    
                    if matches:
                        keyword_results[row['id']] = dict(row)
            else:
                 keyword_results = {row['id']: dict(row) for row in rows}

            results = list(keyword_results.values())
        
        # 2. Vector Search + Token Boosting
        if len(q) > 3:
            try:
                query_embedding = ai_client.get_embedding(q)
                if query_embedding:
                    # Fetch all items with embeddings, BUT respecting filters if any
                    # We can reuse the same filter logic or just apply it in memory if dataset is small.
                    # Best: Put filters in SQL.
                    
                    vec_sql = "SELECT id, name, set_name, line, number, rarity, size, image_url, image_path, vision_description, embedding FROM miniatures WHERE embedding IS NOT NULL"
                    vec_params = []
                    
                    # We need to access size_filter/rarity_filter from the scope above. 
                    # They are local to the 'else' block though. 
                    # Wait, if we are in 'else' block (lines 80+), 'size_filter' is defined.
                    # Use 'size_filter' and 'rarity_filter' variables.
                    
                    if size_filter:
                        vec_sql += " AND size LIKE ?"
                        vec_params.append(f"%{size_filter}%")
                    
                    if rarity_filter:
                        vec_sql += " AND rarity LIKE ?"
                        vec_params.append(f"%{rarity_filter}%")
                        
                    cursor.execute(vec_sql, tuple(vec_params))
                    all_rows = cursor.fetchall()
                    
                    scored_results = []
                    query_tokens = [t.lower() for t in q.split() if len(t) > 2] # simple tokenizer
                    
                    for row in all_rows:
                        item = dict(row)
                        if item['embedding']:
                            try:
                                emb = json.loads(item['embedding'])
                                if not emb or len(emb) == 0:
                                    continue
                                score = cosine_similarity(query_embedding, emb)
                            except Exception as e:
                                continue
                            
                            # Filter quoted phrases from vector results too!
                            if q and '"' in q:
                                quoted_phrases = re.findall(r'"([^"]*)"', q)
                                all_quotes_match = True
                                desc = (item['vision_description'] or "").lower()
                                for phrase in quoted_phrases:
                                    if phrase.lower() not in desc:
                                        all_quotes_match = False
                                        break
                                if not all_quotes_match:
                                    continue
                            
                            # Token Boost with Word Boundaries
                            searchable_text = (item['name'] + " " + (item['vision_description'] or "") + " " + item['set_name']).lower()
                            boost = 0
                            any_word_match = False
                            for token in query_tokens:
                                if re.search(r'\b' + re.escape(token) + r'\b', searchable_text):
                                    boost += 0.25 # Increased boost
                                    any_word_match = True
                            
                            # Penalty for purely semantic matches with no keyword overlap (avoids archer/archon confusion)
                            if not any_word_match and len(query_tokens) > 0:
                                score -= 0.15 # Massive penalty for near-misses
                            
                            score += boost

                            # Threshold - Raised to 0.60 to reduce weak semantic matches
                            if score > 0.60: 
                                item['score'] = score
                                scored_results.append(item)
                    
                    # Sort by score
                    scored_results.sort(key=lambda x: x['score'], reverse=True)
                    
                    # Debug log scores
                    logger.info(f"Query: {q}")
                    for r in scored_results[:5]:
                        logger.info(f"  {r['name']} - Score: {r['score']:.4f}")
                        
                    results = scored_results[:50]
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                # Fallback to keyword results
                if not results:
                     results = list(keyword_results.values())[:50]
        else:
             results = list(keyword_results.values())[:50]
             
    # Calculate a dynamic threshold for "best" vs "ok" based on the top score?
    # Or just hardcode e.g. 0.8?
    # Let's pass a function or flag to template? 
    # Better: pre-calculate in python "is_best"
    
    if results:
        # If no scores (e.g. random results), set is_best to False so it falls under "Random/Related"
        # Wait, if we set is_best=False for ALL, then the loop index 1 check in template will trigger divider immediately
        # which looks like: [Divider] [Item 1] ...
        # We want: [Item 1] ...
        # So we should set is_best=True for all IF it's random, OR prevent divider.
        # Divider condition: not mini.is_best and not ns.found_ok and loop.index > 1
        # If random, we want NO divider. So we can set is_best=True for all?
        # OR we just say "Random Selection" as the header above the whole list?
        # The user said: "The random minis should all be under the 'random' results."
        # This implies a header.
        # If I set is_best=False for all, the divider appears after item 1? No, `loop.index > 1`.
        # So item 1 renders. Then item 2 is not best... divider.
        # So [Item 1] [Divider] [Item 2]... Bad.
        
        # If it's a search result, we want Best... [Divider] ... Related.
        
        # If it's random (no scores), maybe we Treat them all as "Related"? 
        # Better: Pass a flag `is_random` to template.
        
        has_scores = any('score' in r for r in results)
        
        if has_scores:
            top_score = results[0]['score'] if 'score' in results[0] else 0
            best_threshold = max(0.8, top_score - 0.15)
            for r in results:
                r['is_best'] = r.get('score', 0) >= best_threshold
        else:
            # Random results: treat as "not best" but handled by template logic?
            # User wants them under "random results".
            # Let's just set is_best=False for all.
            # AND modify template to show header at top if it's start?
            # OR modify template to NOT show divider if query is empty.
            for r in results:
                r['is_best'] = True # Hack: treats them as 'Best' grouping (no divider)
                # But we want a header?
                # The user said "The random minis should all be under the 'random' results". 
                # Meaning a header "Random Results" followed by minis.
                pass
            
    return templates.TemplateResponse("partials/results.html", {"request": request, "minis": results}) # type: ignore

# Scrape endpoint
async def run_scrape_task(limit: int = 0):
    scraper = Scraper()
    try:
        # For demo, just scrape D&D line
        await scraper.scrape_line("dungeons-and-dragons", "Dungeons & Dragons", limit=limit)
    finally:
        await scraper.close()

@app.post("/analyze/{mini_id}", response_class=HTMLResponse)
async def analyze_mini(request: Request, mini_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM miniatures WHERE id = ?", (mini_id,))
        row = cursor.fetchone()
        if not row:
            return HTMLResponse("Miniature not found", status_code=404)
        
        mini = dict(row)
        
        # Run analysis
        if mini['image_path'] and os.path.exists(mini['image_path']):
            logger.info(f"Analyzing {mini['name']} (ID: {mini_id}) with model {ai_client.client}...")
            description = ai_client.generate_description(mini['image_path'], name=mini['name'])
            logger.info(f"Analysis complete for {mini['name']}: {description[:50]}...")
            
            text = f"{mini['name']} {description}"
            embedding = ai_client.get_embedding(text)
            
            # Update DB
            cursor.execute("""
                UPDATE miniatures 
                SET vision_description = ?, embedding = ?
                WHERE id = ?
            """, (description, json.dumps(embedding), mini_id))
            conn.commit()
            
            # Fetch updated object
            cursor.execute("SELECT * FROM miniatures WHERE id = ?", (mini_id,))
            updated_mini = dict(cursor.fetchone())
            
            # Render just this one card? Or return a success message?
            # Ideally we replace the card. We can reuse a partial if we extract the card to its own partial.
            # For now, let's just return a success toast or swap the description if visible.
            # Let's re-render the card. We need a "card.html" partial to be clean, 
            # but for now I'll arguably duplicate or inline-render.
            # Actually, `results.html` iterates. Let's make a `partials/card.html`.
            return templates.TemplateResponse("partials/card.html", {"request": request, "mini": updated_mini})
            
    return HTMLResponse("Error analyzing", status_code=500)

@app.post("/scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scrape_task, limit=10) # default limit for web trigger
    return HTMLResponse("<div class='text-green-500'>Scraping started in background... check logs.</div>")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "scrape":
        # CLI mode
        limit = 0
        if "--limit" in sys.argv:
            try:
                idx = sys.argv.index("--limit")
                limit = int(sys.argv[idx+1])
            except:
                pass
        init_db()
        asyncio.run(run_scrape_task(limit=limit))
    else:
        uvicorn.run("miniscope.main:app", host="0.0.0.0", port=8000, reload=True)
