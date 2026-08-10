"""
Django settings for projectspark project — production-ready version.
Secrets and environment-specific values now come from a `.env` file
(never committed) instead of being hardcoded.
"""
import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
# Reads a .env file placed next to manage.py. Create your own locally;
# it is git-ignored and never pushed.
environ.Env.read_env(BASE_DIR / '.env')

# --- Core security settings, all from environment ---
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '*.onrender.com'])

# --- Email, no longer hardcoded ---
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)

# Brevo's HTTPS API works on Render's free web service. SMTP is blocked there.
BREVO_API_KEY = env('BREVO_API_KEY', default='')
BREVO_FROM_EMAIL = env('BREVO_FROM_EMAIL', default=env('EMAIL_HOST_USER', default=''))
BREVO_FROM_NAME = env('BREVO_FROM_NAME', default='Sparky Events')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'cloudinary',
    'appspark',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'projectspark.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['appspark/templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'appspark.context_processors.workhand_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'projectspark.wsgi.application'

# --- Database ---
# Priority: DATABASE_URL (Render auto-provides) > DB_ENGINE > SQLite default
# Render provides DATABASE_URL automatically; locally set DB_ENGINE=postgresql|mysql|sqlite
if env('DATABASE_URL', default=None):
    # Render provides DATABASE_URL in this format:
    # postgresql://user:password@host:port/dbname
    # Note: Render's Internal Database URL omits the port (defaults to 5432),
    # so we use urlsplit instead of a strict regex that requires one.
    from urllib.parse import urlsplit
    db_url = env('DATABASE_URL')
    parsed = urlsplit(db_url)
    if not (parsed.scheme and parsed.hostname and parsed.path.lstrip('/')):
        raise ValueError(f"Invalid DATABASE_URL format: {db_url}")
    engine = 'postgresql' if parsed.scheme in ('postgres', 'postgresql') else parsed.scheme
    DATABASES = {
        'default': {
            'ENGINE': f'django.db.backends.{engine}',
            'NAME': parsed.path.lstrip('/'),
            'USER': parsed.username,
            'PASSWORD': parsed.password,
            'HOST': parsed.hostname,
            'PORT': parsed.port or 5432,
            'CONN_MAX_AGE': 60,
        }
    }
elif env('DB_ENGINE', default='sqlite') == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='sparky'),
            'USER': env('DB_USER', default='postgres'),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
        }
    }
elif env('DB_ENGINE', default='sqlite') == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': env('DB_NAME', default='sparky'),
            'USER': env('DB_USER', default='root'),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='3306'),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # used by `collectstatic` in production

# WhiteNoise serves everything gathered into STATIC_ROOT directly from the
# Django app itself - no separate server, no CDN, no S3 bucket needed, and
# it works the same whether DEBUG is True or False. Using the plain
# Compressed storage (not the Manifest variant) so a slightly stale/missing
# {% static %} reference just 404s that one file instead of failing the
# entire `collectstatic` run.

STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# User-uploaded files must not be stored on Render's ephemeral filesystem.
# When Cloudinary credentials are configured (production), Django's default
# storage sends uploads there. Without them, local development keeps using
# the normal filesystem storage.
CLOUDINARY_CLOUD_NAME = env('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = env('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = env('CLOUDINARY_API_SECRET', default='')

if all((CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)):
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY': CLOUDINARY_API_KEY,
        'API_SECRET': CLOUDINARY_API_SECRET,
    }
    STORAGES['default'] = {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')

# --- Auth redirects, needed for @login_required to work correctly ---
LOGIN_URL = 'workhandlogin'          # where anonymous users get bounced to
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'

# --- Messages framework ---
# Django's default tag for messages.error() is 'error', but Bootstrap has no
# .alert-error class (only .alert-danger) - without this mapping, error
# messages get an unrecognized CSS class and don't get styled as errors.
from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {
    message_constants.ERROR: 'danger',
}

# --- Security hardening: HTTPS enforcement ---
# This must be a SEPARATE switch from DEBUG, not tied to it. Django's local
# dev server (runserver) only ever speaks plain HTTP - it has no TLS support
# at all. If SECURE_SSL_REDIRECT is on locally, Django tries to force every
# request to HTTPS, which runserver can't fulfill, and you get garbled
# "You're accessing over HTTPS but only supports HTTP" crashes.
# Leave IS_PRODUCTION unset (or False) in your local .env, always.
# Only set IS_PRODUCTION=True in your actual deployment's .env (Render, etc.),
# where a real HTTPS-terminating proxy sits in front of the app.
IS_PRODUCTION = env.bool('IS_PRODUCTION', default=False)

if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# --- Celery, background task queue (uses Redis as the message broker) ---
# On free hosting tiers (Render, etc.) there's usually no way to run a
# persistent Celery worker process for free, so this lets production simply
# set USE_CELERY=False in its .env and emails send synchronously instead -
# slightly slower per-request, but zero infrastructure needed. Locally, this
# stays True so Celery + Redis keep working exactly as before.
# Default to False in production, True locally.
USE_CELERY = env.bool('USE_CELERY', default=not IS_PRODUCTION)
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# --- Logging, replaces scattered print() statements ---
(BASE_DIR / 'logs').mkdir(exist_ok=True)  # auto-create so fresh clones/deploys never crash on a missing folder

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 5 * 1024 * 1024,  # 5MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': env('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'appspark': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}