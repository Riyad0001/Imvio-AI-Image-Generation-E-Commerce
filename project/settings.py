import os
from pathlib import Path
from decouple import config
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-$!@#^*&%^!@#*^&*!%$#@$^%!^@$')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ["*"]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  
    "http://127.0.0.1:5173",
    'http://localhost:5173',
    'http://localhost:5174',
    'https://imvio.softvencealpha.com',


]

CORS_ALLOW_ALL_ORIGINS = True
# Application definition
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    'https://imvio.softvencealpha.com',

]
INSTALLED_APPS = [
    # django unfold theme 
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    "unfold.contrib.guardian",
    "unfold.contrib.simple_history",
    "unfold.contrib.location_field",
    # default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',

    # 3rd party
    "django_ckeditor_5",

    # lcoal
    # 'apps.account',
    'apps.socialauth',
    'apps.core',
    'apps.sub',
    'apps.image_gen',
    'apps.designs',
    'apps.product_mookup',

]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 3rd party middleware
    "drf_response_wrapper.middleware.APIResponseWrapperMiddleware",
    # custom middleware
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR/'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # custom context processors
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

# for asgi
# ASGI_APPLICATION = 'project.asgi.application'



AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


###################################
#             DATABASE            #
###################################
from .conf import database
DATABASES = database.POSTGRES 



###################################
#             SMTP            #
###################################
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = config("EMAIL_HOST", default="smtp-relay.brevo.com")
EMAIL_PORT = config("EMAIL_PORT", default=2525, cast=int)

EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)

EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="support@imvio.com.au")
SERVER_EMAIL = config("SERVER_EMAIL", default="support@imvio.com.au")

###################################
#         STATIC FILES            #
###################################

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR/'static',
]
STATIC_ROOT = BASE_DIR/'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR/'media'

# Default file storage
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

###################################
#                DRF              #
###################################

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',        
    ],
    # 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    # 'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'project.custom_exception.custom_exception_handler',

}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=2),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}

# Custom User Model
AUTH_USER_MODEL = 'core.User'

GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID", default="")

STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")

STABILITY_API_KEY = config("STABILITY_API_KEY", default="")
GELATO_API_KEY = config("GELATO_API_KEY", default="")
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
GEMINI_API_KEY = config("GEMINI_API_KEY", default="")
GELATO_BASE_URL = config("GELATO_BASE_URL", default="https://order.gelatoapis.com/v4")
BACKEND_BASE_URL = config("BACKEND_BASE_URL", default="https://api.imvio.com.au")
GELATO_SUPPORTED_PRODUCT_UIDS = [
    uid.strip()
    for uid in config("GELATO_SUPPORTED_PRODUCT_UIDS", default="").split(",")
    if uid.strip()
]

FRONTEND_BASE_URL = config("FRONTEND_BASE_URL", default="http://localhost:5173")
OPENAI_PROJECT_ID = config("OPENAI_PROJECT_ID", default="")
OPENAI_ORG_ID = config("OPENAI_ORG_ID", default="")
OPENAI_BASE_URL = config("OPENAI_BASE_URL", default="")

# Stripe products/prices
STRIPE_CREDIT_PRICE_40 = config("STRIPE_CREDIT_PRICE_40", default="price_1RoY9VRfX6BK6Cwps0rAdYAc")
STRIPE_CREDIT_PRICE_50 = config("STRIPE_CREDIT_PRICE_50", default="price_1SZQLORfX6BK6CwpH39t8ya6")
STRIPE_CREDIT_PRICE_60 = config("STRIPE_CREDIT_PRICE_60", default="price_1RoYC2RfX6BK6CwpO51ZAqOO")
STRIPE_SUBSCRIPTION_PRICE_29 = config("STRIPE_SUBSCRIPTION_PRICE_29", default="price_1TTHwnGylhf8TVYzNF9DP8x5")

# Meta Pixel Conversions API (CAPI) Settings
META_PIXEL_ID = config("META_PIXEL_ID", default="")
META_ACCESS_TOKEN = config("META_ACCESS_TOKEN", default="")

# CKEditor 5 Configuration
CKEDITOR_5_CUSTOM_CSS = "custom_ckeditor/ckeditor_custom.css"
CK_EDITOR_5_UPLOAD_FILE_TYPES = ["jpeg", "jpg", "png", "gif", "webp"]

CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading",
            "|",
            "bold",
            "italic",
            "link",
            "bulletedList",
            "numberedList",
            "blockQuote",
            "imageUpload",
        ],
    },
    "extends": {
        "blockToolbar": [
            "paragraph",
            "heading1",
            "heading2",
            "heading3",
            "|",
            "bulletedList",
            "numberedList",
            "|",
            "blockQuote",
        ],
        "toolbar": [
            "heading",
            "|",
            "outdent",
            "indent",
            "|",
            "bold",
            "italic",
            "link",
            "underline",
            "strikethrough",
            "code",
            "subscript",
            "superscript",
            "highlight",
            "|",
            "codeBlock",
            "sourceEditing",
            "insertImage",
            "mediaEmbed",
            "|",
            "bulletedList",
            "numberedList",
            "todoList",
            "|",
            "blockQuote",
            "insertTable",
            "|",
            "fontSize",
            "fontFamily",
            "fontColor",
            "fontBackgroundColor",
            "|",
            "specialCharacters",
            "horizontalLine",
            "pageBreak",
            "|",
            "sourceEditing",
        ],
        "image": {
            "toolbar": [
                "imageTextAlternative",
                "|",
                "imageStyle:alignLeft",
                "imageStyle:alignCenter",
                "imageStyle:alignRight",
                "|",
                "imageStyle:full",
                "imageStyle:side",
                "|",
            ],
            "styles": [
                "full",
                "side",
                "alignLeft",
                "alignCenter",
                "alignRight",
            ],
        },
        "table": {
            "contentToolbar": [
                "tableColumn",
                "tableRow",
                "mergeTableCells",
                "tableProperties",
                "tableCellProperties",
            ],
        },
        "heading": {
            "options": [
                {
                    "model": "paragraph",
                    "title": "Paragraph",
                    "class": "ck-heading_paragraph",
                },
                {
                    "model": "heading1",
                    "view": "h1",
                    "title": "Heading 1",
                    "class": "ck-heading_heading1",
                },
                {
                    "model": "heading2",
                    "view": "h2",
                    "title": "Heading 2",
                    "class": "ck-heading_heading2",
                },
                {
                    "model": "heading3",
                    "view": "h3",
                    "title": "Heading 3",
                    "class": "ck-heading_heading3",
                },
            ],
        },
    },
}


UNFOLD = {
    "SITE_TITLE": "Imvio Admin Dashboard",
    "SITE_HEADER": "Imvio Admin Panel",
    "DARK_MODE": True,
    "DASHBOARD_CALLBACK": "apps.product_mookup.views.dashboard_callback",

    "SIDEBAR": {
        "show_search": True,
        "command_search": True,
        "show_all_applications": False,
        "navigation": [

            # ================= MAIN =================
            {
                "title": _("Navigation"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": _("Dashboard"), "icon": "dashboard", "link": reverse_lazy("admin:index")},
                ],
            },

            # ================= USERS =================
            {
                "title": _("Users & Wallets"),
                "collapsible": True,
                "items": [
                    {"title": _("Users"), "icon": "people", "link": reverse_lazy("admin:core_user_changelist")},
                    {"title": _("Credit Wallets"), "icon": "account_balance_wallet", "link": reverse_lazy("admin:core_creditwallet_changelist")},
                ],
            },

            # ================= SUB & ORDERS =================
            {
                "title": _("Subscriptions & Orders"),
                "collapsible": True,
                "items": [
                    {"title": _("Subscriptions"), "icon": "card_membership", "link": reverse_lazy("admin:sub_subscription_changelist")},
                    {"title": _("Print Orders"), "icon": "local_shipping", "link": reverse_lazy("admin:sub_printorder_changelist")},
                    {"title": _("Credit Packages"), "icon": "redeem", "link": reverse_lazy("admin:sub_creditpackage_changelist")},
                    {"title": _("Product Sizes"), "icon": "photo_size_select_actual", "link": reverse_lazy("admin:sub_productsize_changelist")},
                ],
            },

            # ================= PRODUCT MOCKUP =================
            {
                "title": _("Product Mockups"),
                "collapsible": True,
                "items": [
                    {"title": _("Product Types"), "icon": "category", "link": reverse_lazy("admin:product_mookup_producttype_changelist")},
                    {"title": _("Product Variants"), "icon": "widgets", "link": reverse_lazy("admin:product_mookup_productvariant_changelist")},
                    {"title": _("Other Pages"), "icon": "description", "link": reverse_lazy("admin:product_mookup_other_pages_changelist")},
                ],
            },

            # ================= AI IMAGE GEN =================
            {
                "title": _("AI Image Generation"),
                "collapsible": True,
                "items": [
                    {"title": _("Image Styles"), "icon": "palette", "link": reverse_lazy("admin:image_gen_imagestyle_changelist")},
                    {"title": _("Generated Images"), "icon": "image", "link": reverse_lazy("admin:image_gen_generatedimage_changelist")},
                    {"title": _("Image Generation Jobs"), "icon": "work", "link": reverse_lazy("admin:image_gen_imagegenerationjob_changelist")},
                    {"title": _("Image Credit Settings"), "icon": "settings", "link": reverse_lazy("admin:image_gen_imagecreditsettings_changelist")},
                ],
            },

            # ================= DESIGNS & CONTACT =================
            {
                "title": _("Designs & Site Info"),
                "collapsible": True,
                "items": [
                    {"title": _("Newsletter Subscriptions"), "icon": "mail", "link": reverse_lazy("admin:designs_newslettersubscription_changelist")},
                    {"title": _("Footer Data"), "icon": "info", "link": reverse_lazy("admin:designs_footerdata_changelist")},
                    {"title": _("Contact Messages"), "icon": "contact_mail", "link": reverse_lazy("admin:designs_contact_changelist")},
                    {"title": _("Generation Examples"), "icon": "auto_awesome", "link": reverse_lazy("admin:designs_genexample_changelist")},
                ],
            },

            # ================= AUTH & SECURITY =================
            {
                "title": _("Auth & Security"),
                "collapsible": True,
                "items": [
                    {"title": _("Groups"), "icon": "group", "link": reverse_lazy("admin:auth_group_changelist")},
                    {"title": _("Outstanding Tokens"), "icon": "key", "link": reverse_lazy("admin:token_blacklist_outstandingtoken_changelist")},
                    {"title": _("Blacklisted Tokens"), "icon": "block", "link": reverse_lazy("admin:token_blacklist_blacklistedtoken_changelist")},
                ],
            },
        ],
    },
}