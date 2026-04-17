from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
for m in client.models.list():
    if 'flash' in m.name.lower() and '3' in m.name.lower():
        print(m.name)
