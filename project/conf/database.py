from pathlib import Path
import os
from decouple import config

BASE_DIR = Path(__file__).resolve().parents[2]  # up to project root

SQLITE = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# PostgreSQL configuration
POSTGRES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='mydb'),
        'USER': config('DB_USER', default='myuser'),
        'PASSWORD': config('DB_PASSWORD', default='strongpassword'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# MySQL configuration
MYSQL = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('MYSQL_DB', default='mydb'),
        'USER': config('MYSQL_USER', default='root'),
        'PASSWORD': config('MYSQL_PASSWORD', default=''),
        'HOST': config('MYSQL_HOST', default='localhost'),
        'PORT': config('MYSQL_PORT', default=3306, cast=int),
    }
}
