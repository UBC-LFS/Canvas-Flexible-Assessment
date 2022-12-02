import os
from datetime import timedelta
from dotenv import load_dotenv, find_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(find_dotenv(os.path.join(BASE_DIR, '..', '.env')))

NAME = os.getenv('DB_NAME')
USER = os.getenv('DB_USERNAME')
PASSWORD = os.getenv('DB_PASSWORD')
HOST = os.getenv('DB_HOST')
PORT = os.getenv('DB_PORT')
DJANGO_SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
INTERNAL_IP = os.getenv('INTERNAL_IP')
ENCRYPT_SALT = os.getenv('ENCRYPT_SALT')
ENCRYPT_PASSWORD = os.getenv('ENCRYPT_PASSWORD')

SECRET_KEY = DJANGO_SECRET_KEY

DEBUG = False

ALLOWED_HOSTS = ['*']

INTERNAL_IPS = [INTERNAL_IP, '127.0.0.1']

# Application definition

INSTALLED_APPS = [
    'flexible_assessment.apps.FlexConfig',
    'instructor.apps.InstructorConfig',
    'student.apps.StudentConfig',
    'oauth.apps.OAuthConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_bootstrap5',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'oauth.middleware.OAuthMiddleware',
]

CANVAS_DOMAIN = os.getenv('CANVAS_DOMAIN')

CANVAS_OAUTH_CLIENT_ID = os.getenv('CANVAS_OAUTH_CLIENT_ID')
CANVAS_OAUTH_CLIENT_SECRET = os.getenv('CANVAS_OAUTH_CLIENT_SECRET')

CANVAS_OAUTH_AUTHORIZE_URL = '{}login/oauth2/auth'.format(CANVAS_DOMAIN)
CANVAS_OAUTH_ACCESS_TOKEN_URL = '{}login/oauth2/token'.format(CANVAS_DOMAIN)
# GraphQL Scope not present in Canvas
CANVAS_OAUTH_SCOPES = [
    'url:GET|/api/v1/courses/:id',
    'url:GET|/api/v1/courses/:course_id/assignment_groups',
    'url:GET|/api/v1/courses/:course_id/assignment_groups/:assignment_group_id',
    'url:PUT|/api/v1/courses/:course_id/assignment_groups/:assignment_group_id']
CANVAS_OAUTH_TOKEN_EXPIRATION_BUFFER = timedelta()

LTI_CONFIG = 'flexible_assessment.json'

ROOT_URLCONF = 'flexible_assessment.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, '..', 'instructor', 'templates'),
            os.path.join(BASE_DIR, '..', 'student', 'templates'),
        ],
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

WSGI_APPLICATION = 'flexible_assessment.wsgi.application'

SESSION_COOKIE_NAME = 'sessionid'
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_AGE = 15

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': NAME,
        'USER': USER,
        'PASSWORD': PASSWORD,
        'HOST': HOST,
        'PORT': PORT
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

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


AUTH_USER_MODEL = 'flexible_assessment.UserProfile'


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Vancouver'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'flexible_assessment.auth.SettingsBackend',
]

LOG_DIR = os.path.join(BASE_DIR, 'log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{course}] - {asctime} - {message} | {user}',
            'style': '{'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'info.log'),
            'formatter': 'simple',
            'backupCount': 10,
            'maxBytes': 5242880,
        },
    },
    'loggers': {
        'flexible_assessment': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'instructor': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'student': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        }
    }
}
