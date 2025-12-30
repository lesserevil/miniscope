import ollama
import logging
import json
from typing import List, Optional

from .config import settings

logger = logging.getLogger(__name__)

# Models are now in settings

class AIClient:
    def __init__(self):
        self.client = ollama.Client(host=settings.ollama_host)

    def generate_description(self, image_path: str, name: str = "") -> str:
        try:
            # Check if model exists, if not maybe pull? 
            # For now assume it's there or let it error/auto-pull if Ollama supports it.
            
            import base64
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
                
            b64_image = base64.b64encode(image_bytes).decode('utf-8')

            prompt = "Describe the character or creature depicted in this image"
            if name:
                prompt += f" (specifically a {name})"
            prompt += (
                ". Describe it in detail as if it were a real entity in a fantasy setting. "
                "IMPORTANT: Describe visible clothing, armor, and any items held in hands. "
                "Only describe items **clearly visible**. Do not guess weapons if hands are empty. "
                "Focus on appearance, gear, and pose. Try to get specific about the types of things in hands. "
                "Try to tell the difference between swords, shields, clubs, daggers, polearms, spears, axes, "
                "bows, crossbows, firearms, and the like. Avoid mentioning that it is a model, "
                "miniature, or figurine. Ignore the base and background."
            )

            # Retry loop
            max_retries = 3
            for attempt in range(max_retries):
                response = self.client.generate(
                    model=settings.vision_model,
                    prompt=prompt,
                    images=[b64_image],
                    options={
                        "num_ctx": 8192,  # Standardize context
                        "temperature": 0.2 # Lower temperature for more stable descriptions
                    },
                    keep_alive="30m" # Keep in VRAM to prevent runner stop/start errors
                )
                
                desc = response['response']
                
                # Post-processing to remove sentences with forbidden words
                forbidden_words = ["miniature", "figurine", "statue", "toy", "model", "base", "stand", "background", "plastic", "render", "video game"]
                
                sentences = desc.split('. ')
                clean_sentences = []
                for s in sentences:
                    lower_s = s.lower()
                    if not any(bad in lower_s for bad in forbidden_words):
                        clean_sentences.append(s)
                
                cleaned_desc = ". ".join(clean_sentences)
                if cleaned_desc and not cleaned_desc.endswith('.'):
                    cleaned_desc += '.'
                    
                # Validation
                is_valid = True
                if not cleaned_desc.strip() or len(cleaned_desc) < 15:
                    is_valid = False
                if "!!!" in cleaned_desc:
                    is_valid = False
                
                if is_valid:
                     # Ensure the name is included in the description for context
                    if name:
                         if not cleaned_desc.lower().startswith(name.lower()):
                             cleaned_desc = f"{name}. {cleaned_desc}"
                    return cleaned_desc
                
                # If we are here, it failed validation
                logger.warning(f"AI generation attempt {attempt+1} failed validation: '{cleaned_desc}'. Retrying...")
            
            # If all retries failed, return just name
            logger.error(f"AI generation failed after {max_retries} attempts for {name}.")
            return f"{name}."
        except Exception as e:
            logger.error(f"Error generating description: {e}")
            return ""

    def get_embedding(self, text: str) -> List[float]:
        try:
            # Truncate text to avoid context limits (6k chars is ~1.5k tokens)
            safe_text = text[:6000]
            response = self.client.embeddings(
                model=settings.embedding_model,
                prompt=safe_text,
                options={
                    "num_ctx": 16384
                }
            )
            return response['embedding']
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return []
