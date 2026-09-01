#!/usr/bin/env python
"""Check available Gemini models"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

# Add the project to path
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

from django.conf import settings
import google.generativeai as genai

api_key = getattr(settings, "GEMINI_API_KEY", "")
if not api_key:
    print("ERROR: GEMINI_API_KEY not configured in settings!")
    sys.exit(1)

print(f"API Key found: {bool(api_key)}")
print(f"API Key (first 20 chars): {api_key[:20]}...")

genai.configure(api_key=api_key)

print("\n" + "="*80)
print("AVAILABLE GEMINI MODELS")
print("="*80)

try:
    models = genai.list_models()
    
    print(f"\nTotal models available: {len(list(models))}\n")
    
    print("Models supporting generateContent:")
    print("-" * 80)
    
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"\n✓ {model.name}")
            print(f"  Display Name: {model.display_name}")
            print(f"  Supported Methods: {model.supported_generation_methods}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
