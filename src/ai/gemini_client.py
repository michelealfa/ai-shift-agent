from google import genai
import logging
from ..config.config import settings
from PIL import Image

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: str = None):
        # Use provided key or fallback to global settings
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.vision_model_name = settings.VISION_MODEL
        self.nlp_model_name = settings.NLP_MODEL

    async def analyze_image(self, image_path: str, prompt: str):
        """Analyzes an image using Gemini Vision (New SDK)."""
        try:
            img = Image.open(image_path)
            # generate_content in the new SDK handles [text, image]
            response = self.client.models.generate_content(
                model=self.vision_model_name,
                contents=[prompt, img]
            )
            return {"response": response.text}
        except Exception as e:
            logger.error(f"Gemini Vision Error (New SDK): {e}")
            raise e

    async def chat(self, prompt: str):
        """Standard chat interaction with Gemini (New SDK)."""
        try:
            response = self.client.models.generate_content(
                model=self.nlp_model_name,
                contents=prompt
            )
            return {"response": response.text}
        except Exception as e:
            logger.error(f"Gemini NLP Error (New SDK): {e}")
            raise e
