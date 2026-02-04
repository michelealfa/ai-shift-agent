import httpx
import base64
from ..config.config import settings

class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.vision_model = settings.VISION_MODEL
        self.nlp_model = settings.NLP_MODEL

    async def analyze_image(self, image_path: str, prompt: str):
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                    "format": "json"
                }
            )
            return response.json()

    async def chat_nlp(self, prompt: str, context: str = ""):
        full_prompt = f"Context: {context}\n\nUser: {prompt}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.nlp_model,
                    "prompt": full_prompt,
                    "stream": False
                }
            )
            return response.json()
