from google import genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found in environment variables")
    exit(1)

client = genai.Client(api_key=api_key)
models = client.models.list()
print("Available models:")
for model in models:
    print(f"  - {model.name}")