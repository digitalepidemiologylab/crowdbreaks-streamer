"""Application configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

class Config(object):
    """Base configuration."""
    # Environment
    ENV = os.environ.get('ENV', 'dev')

    # Paths
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    CONFIG_PATH = os.path.abspath(os.path.join(APP_DIR, 'config'))

    # Stream config
    STREAM_CONFIG_FILE_PATH = os.path.join('stream.json')

    # Twitter API
    CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
    CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
    OAUTH_TOKEN = os.environ.get('OAUTH_TOKEN')
    OAUTH_TOKEN_SECRET = os.environ.get('OAUTH_TOKEN_SECRET')

    # AWS (for storing in S3, accessing Elasticsearch)
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    AWS_REGION = os.environ.get('AWS_REGION', 'eu-central-1')

    # Other
    TIMEZONE = os.environ.get('TIMEZONE', 'Europe/Zurich')


class ProdConfig(Config):
    """Production configuration."""
    CONFIG_ENV = 'prod'
    DEBUG = False


class DevConfig(Config):
    """Development configuration."""
    CONFIG_ENV = 'dev'
    DEBUG = True


class TestConfig(Config):
    """Test configuration."""
    TESTING = True
    DEBUG = True
