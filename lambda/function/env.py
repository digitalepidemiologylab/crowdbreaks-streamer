"""Application configuration."""
import os
from aenum import Constant


class Env(Constant):
    """Base configuration."""
    # Environment
    ENV = os.environ.get('ENV', 'stg').lower()
    APP_NAME = os.environ.get('APP_NAME').lower()
    DEBUG = os.environ.get('DEBUG')
    assert DEBUG in ['True', 'False']
    DEBUG = int(DEBUG == 'True')

    # Paths
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    CONFIG_PATH = os.path.abspath(os.path.join(APP_DIR, 'config'))

    # Stream config
    STREAM_CONFIG_PATH = os.path.join(CONFIG_PATH, 'stream.json')

    # Other
    TIMEZONE = os.environ.get('TIMEZONE', 'Europe/Zurich')
    S3_BUCKET_PREFIX = os.environ.get('S3_BUCKET_PREFIX', 'project_')


class AWSEnv(Env):
    """AWS config (for storing in S3, accessing Elasticsearch)."""
    REGION = os.environ.get('AWS_REGION', 'eu-central-1')
    BUCKET_NAME = os.environ.get(
        'AWS_BUCKET_NAME', Env.APP_NAME + '-' + Env.ENV)
    STREAM_CONFIG_S3_KEY = os.path.join(
        'CONFIG_S3_KEY', 'configs/stream/stream.json')
    ENDPOINTS_PREFIX = os.path.join(
        'ENDPOINTS_PREFIX', 'configs/models/')


class ESEnv(AWSEnv):
    HOST = os.environ.get('ES_HOST')
    PORT = os.environ.get('ES_PORT')
    INDEX_PREFIX = os.environ.get('ES_INDEX_PREFIX', 'project_')


class SMEnv(AWSEnv):
    BATCH_SIZE_DEFAULT = int(os.environ.get('BATCH_SIZE_DEFAULT', '1'))
    BATCH_SIZE_FASTTEXT = int(os.environ.get('BATCH_SIZE_FASTTEXT', '100'))
