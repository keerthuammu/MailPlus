import os
from pathlib import Path
from dotenv import load_dotenv
from django.contrib.messages import constants as message_constants

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-development-secret-key-99283')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

# In production set ALLOWED_HOSTS to your actual domain(s) in .env
# e.g. ALLOWED_HOSTS=mailpulse.example.com,www.mailpulse.example.com
_allowed = os.getenv('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(',') if h.strip()] if _allowed else (['localhost', '127.0.0.1', '.ngrok-free.app', '.localhost.run', '.localtunnel.me', '.lhr.life', '.serveo.net', '.serveousercontent.com'] if DEBUG else ['*'])

# Base URL for email tracking links (e.g. public tunnel URL)
SITE_URL = os.getenv('SITE_URL', '')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',           # Required by allauth
    # django-allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # Our custom app
    'tracker.apps.TrackerConfig',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Required by allauth
]

ROOT_URLCONF = 'mailpulse.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # Templates will be placed inside tracker/templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mailpulse.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# =============================================================================
# Production Security Settings
# These activate automatically when DEBUG=False so local development is
# completely unaffected. Enable each once you have HTTPS configured.
# Reference: https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/
# =============================================================================
if not DEBUG:
    # Force all cookies over HTTPS only
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Redirect all plain HTTP requests to HTTPS
    SECURE_SSL_REDIRECT = True

    # HTTP Strict Transport Security (6 months; increase after confirming HTTPS)
    SECURE_HSTS_SECONDS = 15768000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Prevent browsers from MIME-sniffing the content type
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Enable browser XSS filter header
    SECURE_BROWSER_XSS_FILTER = True

    # Set this if running behind a reverse proxy (e.g. Nginx, AWS ALB)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
LOGIN_URL = 'tracker:login'
LOGIN_REDIRECT_URL = 'tracker:dashboard'
LOGOUT_REDIRECT_URL = 'tracker:login'

# =============================================================================
# django-allauth Configuration
# =============================================================================
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',          # Standard username/password
    'allauth.account.auth_backends.AuthenticationBackend', # Google OAuth
]

# allauth account settings (django-allauth v65+ API)
ACCOUNT_LOGIN_METHODS = {'email'}          # Login via email, not username
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']  # Required signup fields
ACCOUNT_EMAIL_VERIFICATION = 'none'  # Skip email verification for social login
SOCIALACCOUNT_AUTO_SIGNUP = True     # Auto-create account on first Google login
SOCIALACCOUNT_LOGIN_ON_GET = True    # Skip intermediate page

# Google OAuth scopes — name + email only (no Gmail access)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile', 
            'email',
            'https://www.googleapis.com/auth/gmail.send'
        ],
        'AUTH_PARAMS': {
            'access_type': 'offline',
            'prompt': 'consent'
        },
        'FETCH_USERINFO': True,
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
            'key': '',
        },
    }
}

SOCIALACCOUNT_STORE_TOKENS = True

# Bootstrap 5 styled tags for Django Messages Framework
MESSAGE_TAGS = {
    message_constants.DEBUG: 'secondary',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'danger',
}

# Email Backend Settings
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587')) if os.getenv('EMAIL_PORT') else 587
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
EMAIL_TIMEOUT = 15

# Use console backend if SMTP parameters are missing or contain default placeholders
PLACEHOLDERS = {'your-email@gmail.com', 'your-app-password', 'your-email', 'your_email', 'your_password'}
if not EMAIL_HOST or not EMAIL_HOST_USER or EMAIL_HOST_USER.lower() in PLACEHOLDERS or EMAIL_HOST_PASSWORD.lower() in PLACEHOLDERS:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# IMAP Settings for Inbox Viewer
IMAP_HOST = os.getenv('IMAP_HOST', 'imap.gmail.com')
IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))


# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Centralized Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'mailpulse.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'tracker': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

