import os
import google.generativeai as genai
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    # Try to find it in .env manually if not in environment
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "GEMINI_API_KEY" in line:
                    api_key = line.split("=")[1].strip().strip("'").strip('"')
                    break
genai.configure(api_key=api_key)
try:
    print(f"Using API Key: {bool(api_key)}")
    models = genai.list_models()
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(f"✓ {m.name}")
except Exception as e:
    print(f"Error: {e}")
