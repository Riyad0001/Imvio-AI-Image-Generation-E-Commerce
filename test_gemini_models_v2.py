import os
import sys

# Add the current directory to sys.path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

import django
try:
    django.setup()
except Exception as e:
    print(f'Django setup error: {e}')

try:
    from apps.image_gen.services.gemini_image_service import GeminiImageEditService
    models = GeminiImageEditService.get_available_models()
    print('Available Gemini models:')
    for m in models:
        print(f'  - {m}')
except Exception as e:
    import traceback
    traceback.print_exc()
