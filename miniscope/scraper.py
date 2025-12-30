import asyncio
import httpx
from bs4 import BeautifulSoup
import os
import logging
from typing import List, Optional
from .models import Miniature
from .database import get_db_cursor
from .ai import AIClient

logger = logging.getLogger(__name__)

BASE_URL = "https://www.minisgallery.com"
IMAGE_DIR = "data/images"

class Scraper:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.ai = AIClient()
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)

    async def close(self):
        await self.client.aclose()

    async def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def parse_miniatures(self, soup: BeautifulSoup, set_name: str, line: str) -> List[Miniature]:
        minis = []
        # Based on exploration: .miniboxStandard contains the mini
        cells = soup.select(".miniboxStandard")
        for cell in cells:
            try:
                # Name
                name_elem = cell.select_one(".miniNameNormal")
                if not name_elem:
                    continue
                name = name_elem.get_text(strip=True)

                # Image
                img_elem = cell.select_one(".miniImageStandard img")
                image_url = ""
                if img_elem and img_elem.has_attr("src"):
                    src = img_elem["src"]
                    # src might be relative "images/..."
                    if not src.startswith("http"):
                        image_url = f"{BASE_URL}/{src}"
                    else:
                        image_url = src
                
                # Number
                number = ""
                num_elem = cell.select_one(".miniInfo2_num")
                if num_elem:
                    number = num_elem.get_text(strip=True).strip("()")

                # Rarity
                rarity = ""
                rarity_elem = cell.select_one(".miniRarity")
                if rarity_elem:
                     # e.g. class="miniRarity rarity_common"
                     classes = rarity_elem.get("class", [])
                     for c in classes:
                         if c.startswith("rarity_"):
                             rarity = c.replace("rarity_", "")
                             break

                # Size
                size = ""
                size_elem = cell.select_one(".miniSize")
                if size_elem:
                    # MinisGallery uses class names like "miniSize size_L" or "miniSize size_M"
                    # But sometimes just text? Let's check text first.
                    size_text = size_elem.get_text(strip=True)
                    if size_text and len(size_text) > 0:
                        size = size_text
                    
                    # Fallback to class extraction if text is empty/weird
                    if not size:
                        classes = size_elem.get("class", [])
                        for c in classes:
                            if c.startswith("size_"):
                                size = c.replace("size_", "").upper()
                                break

                mini = Miniature(
                    name=name,
                    line=line,
                    set_name=set_name,
                    number=number,
                    rarity=rarity,
                    size=size,
                    image_url=image_url
                )
                minis.append(mini)

            except Exception as e:
                logger.error(f"Error parsing mini in set {set_name}: {e}")
                continue
        return minis

    async def download_image(self, url: str, mini_id: int) -> Optional[str]:
        if not url:
            return None
        
        # Prefix filename with DB ID to prevent collisions
        raw_filename = url.split("/")[-1]
        filename = f"{mini_id}_{raw_filename}"
        filepath = os.path.join(IMAGE_DIR, filename)
        
        if os.path.exists(filepath):
            return filepath

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
            return filepath
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None

    async def save_minis(self, minis: List[Miniature]):
        import json
        with get_db_cursor() as cursor:
            for mini in minis:
                embedding_json = json.dumps(mini.embedding) if mini.embedding else None
                
                cursor.execute("""
                    SELECT id FROM miniatures WHERE name = ? AND set_name = ?
                """, (mini.name, mini.set_name))
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute("""
                        UPDATE miniatures SET 
                            image_url = ?, number = ?, rarity = ?, size = ?,
                            vision_description = ?, embedding = ?
                        WHERE id = ?
                    """, (mini.image_url, mini.number, mini.rarity, mini.size, 
                          mini.vision_description, embedding_json, existing[0]))
                    mini.id = existing[0]
                else:
                    cursor.execute("""
                        INSERT INTO miniatures (name, line, set_name, number, rarity, size, image_url, image_path, vision_description, embedding)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (mini.name, mini.line, mini.set_name, mini.number, mini.rarity, mini.size, 
                          mini.image_url, mini.image_path, mini.vision_description, embedding_json))
                    mini.id = cursor.lastrowid
    
    async def scrape_set(self, set_id: str, set_name: str, line: str):
        # Rate limiting
        await asyncio.sleep(1.0) # 1 second delay
        
        url = f"{BASE_URL}/index.php?id={set_id}"
        logger.info(f"Scraping set: {set_name} ({url})")
        soup = await self.fetch_page(url)
        if not soup:
            return
        
        # Check if this is a terminal set page (has miniatures)
        minis = self.parse_miniatures(soup, set_name, line)
        if minis:
            logger.info(f"Found {len(minis)} miniatures in {set_name}")
            
            # First pass: Save to get IDs
            await self.save_minis(minis)
            
            for mini in minis:
                mini.image_path = await self.download_image(mini.image_url, mini.id)
                if mini.image_path:
                    logger.info(f"Analyzing image for {mini.name}...")
                    mini.vision_description = self.ai.generate_description(mini.image_path, name=mini.name)
                    # Create embedding from name + description
                    text_for_embedding = f"{mini.name} {mini.vision_description}"
                    mini.embedding = self.ai.get_embedding(text_for_embedding)
            
            # Second pass: Update with image_path and AI results
            await self.save_minis(minis)
        else:
             # It might be a category page (e.g. "Core Sets"), let's digest its links
             logger.info(f"{set_name} appears to be a category, looking for subsets...")
             # Avoid infinite loops or going back up
             links = soup.select("a[href*='index.php?id=']")
             for link in links:
                 href = link["href"]
                 s_id = href.split("id=")[1].split("&")[0]
                 if s_id != set_id and s_id not in ["dungeons-and-dragons", "main-menu", "pathfinder-battles"]: 
                     # Heuristic: verify if it's likely a child set
                     # detailed validation is hard without visiting, but we can just try visiting
                     # recursing one level might be safe if we track visited
                     # For this "scrape_line" entry point, we are already iterating links.
                     pass
                     # Ideally we need a 'crawl' method but for now let's just assume 
                     # scrape_line handles the top level links which are categories, 
                     # and we need to drill down ONE level if empty.
                     
    async def scrape_line(self, line_id: str, line_name: str, limit: int = 0, force: bool = False):
        url = f"{BASE_URL}/index.php?id={line_id}"
        soup = await self.fetch_page(url)
        if not soup: return
        
        seen_sets = set()
        queue = [(line_id, line_name, 0)] # id, name_hint, attempt
        visited = set([line_id])
        
        count = 0
        
        while queue:
            if limit > 0 and count >= limit: break
            
            current_id, current_name_hint, attempt = queue.pop(0)
            
            # Optimization: Pre-check DB if name is known
            if not force and current_name_hint:
                safe_name = current_name_hint.strip()
                with get_db_cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM miniatures WHERE set_name = ?", (safe_name,))
                    pre_count = cursor.fetchone()[0]
                
                if pre_count > 0:
                    logger.info(f"Skipping set '{safe_name}' (cached name found with {pre_count} minis).")
                    continue
            url = f"{BASE_URL}/index.php?id={current_id}"
            
            # Delay (base 1s + exponential backoff if retrying)
            wait_time = 1.0 * (2 ** attempt) if attempt > 0 else 1.0
            if attempt > 0:
                logger.info(f"Retry attempt {attempt} for {current_id}. Waiting {wait_time}s...")
            await asyncio.sleep(wait_time)
            
            try:
                soup = await self.fetch_page(url)
            except Exception as e:
                if attempt < 5:
                    logger.error(f"Error fetching {url}: {e}. Retrying...")
                    queue.insert(0, (current_id, current_name_hint, attempt + 1))
                else:
                    logger.error(f"Failed to fetch {url} after 5 attempts. Skipping.")
                continue
                
            if not soup: 
                # If fetch didn't throw but returned None (e.g. 404 or empty)
                continue
            
            # Try to parse minis directly
            minis = self.parse_miniatures(soup, line_name, line_name) # simplified naming for now
            if minis:
                # It's a set page
                # Fix up set_name if possible? We used 'line_name' as set_name placeholder above. 
                # We can use soup title or header.
                header = soup.select_one("h1, h2, .content_header_text") # guessing header class
                real_set_name = header.get_text(strip=True) if header else current_id
                
                # CHECK if we already have this set in DB
                if not force:
                    with get_db_cursor() as cursor:
                        cursor.execute("SELECT COUNT(*) FROM miniatures WHERE set_name = ?", (real_set_name,))
                        count_existing = cursor.fetchone()[0]
                        
                    if count_existing > 0:
                        logger.info(f"Skipping set '{real_set_name}' (already has {count_existing} minis).")
                        continue

                for m in minis:
                    m.set_name = real_set_name
                
                # First pass: Save to get IDs
                await self.save_minis(minis)
                
                for mini in minis:
                    # Check DB for existing AI data to avoid re-running expensive AI
                    # Note: We now have mini.id from the first save_minis call
                    with get_db_cursor() as cursor:
                        cursor.execute("SELECT vision_description, embedding FROM miniatures WHERE id = ?", (mini.id,))
                        existing_row = cursor.fetchone()
                        
                    if existing_row and existing_row[0]:
                        mini.vision_description = existing_row[0]
                        import json
                        if existing_row[1]:
                            try:
                                mini.embedding = json.loads(existing_row[1])
                            except:
                                mini.embedding = None
                    
                    # Download image using the ID as prefix
                    mini.image_path = await self.download_image(mini.image_url, mini.id)
                    
                    # Only run AI if description is missing
                    if mini.image_path and not mini.vision_description:
                        logger.info(f"Analyzing image for {mini.name}...")
                        mini.vision_description = self.ai.generate_description(mini.image_path, name=mini.name)
                        text_for_embedding = f"{mini.name} {mini.vision_description}"
                        mini.embedding = self.ai.get_embedding(text_for_embedding)
                    
                # Second pass: Update with image_path and AI results
                await self.save_minis(minis)
                count += 1
            else:
                # It's a category page, find children
                logger.info(f"Exploring category: {current_id}")
                links = soup.select("a[href*='index.php?id=']")
                for link in links:
                    href = link["href"]
                    child_id = href.split("id=")[1].split("&")[0]
                    
                    # Filter noise
                    if child_id in visited or child_id in ["main-menu", "contact", "links", "privacy-policy", "search", "dungeons-and-dragons", "pathfinder-battles"]:
                        continue
                        
                    visited.add(child_id)
                    link_text = link.get_text(strip=True)
                    queue.append((child_id, link_text, 0))


