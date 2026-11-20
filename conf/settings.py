import os
from pathlib import Path
from conf.env_loader import load_dotenv


load_dotenv()

PROJECT_NAME = "🐼 BEARBLOG 🐼"

BASE_DIR = Path(__file__).resolve().parent.parent

# Location of optional exports and migrated static assets.
PERSONAL_CONTENT_DIR = os.getenv('PERSONAL_CONTENT_DIR') or (
    BASE_DIR / 'content' if os.getenv('SINGLE_BLOG') == 'True' else None
)
PERSONAL_CONTENT_AUTO_EXPORT = os.getenv('PERSONAL_CONTENT_AUTO_EXPORT') == 'True'

SECRET_KEY = os.getenv('SECRET')
PAYMENT_WEBHOOK_SECRET = os.getenv('PAYMENT_WEBHOOK_SECRET', '')
PAYMENT_CHECKOUT_URL = os.getenv('PAYMENT_CHECKOUT_URL', '')

DEBUG = (os.getenv('DEBUG') == 'True')

ADMINS = (('Webmaster', os.getenv('ADMIN_EMAIL')),)


# Host & proxy settings
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['https://bearblog.dev', 'https://www.bearblog.dev']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

X_FRAME_OPTIONS = 'ALLOWALL'

INTERNAL_IPS = ['127.0.0.1']

# Application definition
SITE_ID = 1

INSTALLED_APPS = [
    'judoscale.django',
    'django.contrib.admin',
    'django.contrib.sites',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'blogs.apps.BlogsConfig',
    'allauth.account',
    'allauth.socialaccount',
    'debug_toolbar',
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'blogs.stored_assets.MigratedAssetMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# Only enable tailnet mode on a separate process reachable exclusively via
# Tailscale Serve. Never expose that process through a public proxy or Funnel.
PERSONAL_BLOG_ACCESS = os.getenv('PERSONAL_BLOG_ACCESS', 'normal')
if PERSONAL_BLOG_ACCESS not in ('normal', 'public', 'tailnet'):
    raise ValueError('Invalid PERSONAL_BLOG_ACCESS')
if PERSONAL_BLOG_ACCESS != 'normal':
    if os.getenv('SINGLE_BLOG') != 'True':
        raise ValueError('Personal blog access requires SINGLE_BLOG=True')
    MIDDLEWARE.insert(MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware') + 1,
                      'blogs.private_access.PersonalBlogAccessMiddleware')

ROOT_URLCONF = 'conf.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.normpath(os.path.join(BASE_DIR, 'templates')),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'blogs.context_processors.extra'
            ],
        },
    },
]


WSGI_APPLICATION = 'conf.wsgi.application'

# All-auth setup
ACCOUNT_LOGIN_METHODS = {'email'}
if not DEBUG:
    ACCOUNT_EMAIL_VERIFICATION = 'none'
    ACCOUNT_CONFIRM_EMAIL_ON_GET = True
    ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*']
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
ACCOUNT_ADAPTER = 'blogs.adapters.AccountAdapter'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 90 # 90 days
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'dev.db'),
    }
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
# Preserve migrated article URLs on a clean deployment / collectstatic.
if PERSONAL_CONTENT_DIR and (Path(PERSONAL_CONTENT_DIR) / 'assets').is_dir():
    STATICFILES_DIRS.append(('migrated', Path(PERSONAL_CONTENT_DIR) / 'assets'))
GEOIP_PATH = "geoip/"

# Enable WhiteNoise compression and cache-safe, hashed static asset names.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Cache unhashed static paths (favicons, og-image, stylesheet previews) for 24 hours
WHITENOISE_MAX_AGE = 86400

LOGIN_REDIRECT_URL = '/dashboard/'

# Emailer
ACCOUNT_EMAIL_SUBJECT_PREFIX = '' # Allauth email setting
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', '')
SERVER_EMAIL = os.getenv('SERVER_EMAIL', '')
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.eu.mailgun.org'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# Referrer policy
SECURE_REFERRER_POLICY = "origin-when-cross-origin"
