import os
from dotenv import load_dotenv

# BUG FIX: Your env file is named '_env'. Rename it to '.env' in your project
# so python-dotenv picks it up automatically with load_dotenv().
# Alternatively, point to it explicitly as shown below (useful during dev):
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.1-8b-instant"