import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
import django
django.setup()

from apps.image_gen.services.gemini_image_service import GeminiImageEditService

try:
    models = GeminiImageEditService.get_available_models()
    print('Available Gemini models:')
    for m in models:
        print(f'  - {m}')
except Exception as e:
    print(f'Error: {e}')
