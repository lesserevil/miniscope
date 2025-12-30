import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniscope.ai import AIClient

def debug_image():
    client = AIClient()
    image_path = "data/images/orc-archer.jpg"
    
    if os.path.exists(image_path):
        print(f"Analyzing {image_path}...")
        desc = client.generate_description(image_path)
        print(f"Description: {desc}")
    else:
        print("Image not found.")

if __name__ == "__main__":
    debug_image()
