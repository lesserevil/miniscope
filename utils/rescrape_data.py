import os
import sys
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniscope.scraper import Scraper
from miniscope.database import init_db

async def rescrape():
    init_db()
    scraper = Scraper()
    print("Starting force rescrape of Dungeons & Dragons line...")
    try:
        # Force = True to bypass "existing set" check
        await scraper.scrape_line("dungeons-and-dragons", "Dungeons & Dragons", limit=50, force=True)
    finally:
        await scraper.close()
    print("Rescrape complete.")

if __name__ == "__main__":
    asyncio.run(rescrape())
