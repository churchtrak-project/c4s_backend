"""
Django settings for careforsheperds project.

Phase 1: Fundraising & Pastoral Wellness Fund (Care for Shepherds)
Simple multi-tenant backend with DRF + Admin.
"""

import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', 'testserver', '*'])  # * for dev/testing only; tighten in prod


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',  # for token-based login used by frontend roles

    # Project apps (simple structure)
    'accounts',
    'churches',
    'fundraising',
    'payments',
    'counseling',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'careforsheperds.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'careforsheperds.wsgi.application'

# Custom User model (defined in accounts app)
AUTH_USER_MODEL = 'accounts.User'


# Database - PostgreSQL (required)
# Use DATABASE_URL (preferred) or individual vars in .env
# Example: DATABASE_URL=postgres://user:pass@localhost:5432/dbname
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://careforsheperds:careforsheperds@localhost:5432/careforsheperds')
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = env('TIME_ZONE', default='Africa/Nairobi')
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = 'static/'

# Media files (for proof documents etc. - stored under MEDIA_ROOT on server)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework - simple start with Session + Token auth
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}


# =============================================================================
# KeshoPay Configuration (single merchant account for the whole platform)
# Use metadata + reference fields to attribute payments to specific Church/Campaign
# =============================================================================
KESHOPAY = {
    'PUBLIC_KEY': env('KESHOPAY_PUBLIC_KEY', default=''),
    'PRIVATE_KEY': env('KESHOPAY_PRIVATE_KEY', default=''),
    'WALLET_ID': env('KESHOPAY_WALLET_ID', default=''),
    'BASE_URL': env('KESHOPAY_BASE_URL', default='https://api.keshopay.co.ke'),
    'WEBHOOK_SECRET': env('KESHOPAY_WEBHOOK_SECRET', default=''),
}

# =============================================================================
# CORS — required for browser clients (Next.js dev server, hosted frontend)
# =============================================================================
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_URLS_REGEX = r'^/api/.*$'
