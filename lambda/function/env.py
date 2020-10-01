"""Application configuration."""
import os
from aenum import Constant


class Env(Constant):
    """Base configuration."""
    # Paths
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    CONFIG_PATH = os.path.abspath(os.path.join(APP_DIR, 'config'))

    # Stream config
    STREAM_CONFIG_PATH = os.path.join(CONFIG_PATH, 'stream.json')

    # Other
    TIMEZONE = os.environ.get('TIMEZONE', 'Europe/Zurich')


class ESEnv(Constant):
    REGION = os.environ.get('AWS_REGION')
    HOST = os.environ.get('ES_HOST')
    PORT = os.environ.get('ES_PORT')
    INDEX_PREFIX = os.environ.get('ES_INDEX_PREFIX', 'project_')


class SMEnv(Constant):
    BATCH_SIZE_DEFAULT = int(os.environ.get('BATCH_SIZE_DEFAULT', '1'))
    BATCH_SIZE_FASTTEXT = int(os.environ.get('BATCH_SIZE_FASTTEXT', '100'))
