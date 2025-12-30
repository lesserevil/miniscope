import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miniscope.ai import AIClient

def test_ai():
    client = AIClient()
    image_path = "data/images/boar.jpg"
    if not os.path.exists(image_path):
        print("Image not found, pick another")
        return

    print(f"Testing description for {image_path}...")
    try:
        import ollama
        from miniscope.config import settings
        c = ollama.Client(host=settings.ollama_host)
        
        with open(image_path, "rb") as f: b = f.read()
        import base64
        b64 = base64.b64encode(b).decode('utf-8')
        
        print(f"Trying Base64 with {settings.vision_model}...")
        response = c.generate(model=settings.vision_model, prompt="Describe the entity in this image.", images=[b64])
        print(response['response'])
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ai()
