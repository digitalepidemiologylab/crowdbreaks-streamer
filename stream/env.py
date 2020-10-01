"""Application configuration."""
import os
from aenum import Constant
from dotenv import load_dotenv

load_dotenv()


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
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    CONFIG_PATH = os.path.abspath(os.path.join(APP_DIR, 'config'))

    # Stream config
    STREAM_CONFIG_PATH = os.path.join(CONFIG_PATH, 'stream.json')

    # Other
    TIMEZONE = os.environ.get('TIMEZONE', 'Europe/Zurich')


class TwiEnv(Constant):
    """Twitter API config."""
    CONSUMER_KEY = os.environ.get('TWI_CONSUMER_KEY')
    CONSUMER_SECRET = os.environ.get('TWI_CONSUMER_SECRET')
    OAUTH_TOKEN = os.environ.get('TWI_OAUTH_TOKEN')
    OAUTH_TOKEN_SECRET = os.environ.get('TWI_OAUTH_TOKEN_SECRET')


class AWSEnv(Env):
    """AWS config (for storing in S3, accessing Elasticsearch)."""
    ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    ACCOUNT_NUM = os.environ.get('AWS_ACCOUNT_NUM')
    BUCKET_NAME = os.environ.get(
        'AWS_BUCKET_NAME', Env.APP_NAME + '-' + Env.ENV)
    REGION = os.environ.get('AWS_REGION', 'eu-central-1')


class KFEnv(AWSEnv):
    BUCKET_PREFIX = os.environ.get('AWS_KF_BUCKET_PREFIX', 'tweets/project_')
    ROLE_TRUST_RELATIONSHIP_PATH = os.path.join(
        AWSEnv.CONFIG_PATH,
        os.environ.get('AWS_KF_ROLE_TRUST_RELATIONSHIP_FILENAME'))
    POLICY_PATH = os.path.join(
        AWSEnv.CONFIG_PATH,
        os.environ.get('AWS_KF_POLICY_PATH'))
    BUFFER_SIZE = int(os.environ.get('AWS_KF_BUFFER_SIZE', '50'))
    BUFFER_INTERVAL = int(os.environ.get('AWS_KF_BUFFER_INTERVAL', '60'))


class LEnv(AWSEnv):
    BUCKET_PREFIX = os.environ.get('AWS_KF_BUCKET_PREFIX', 'tweets/project_')
    ROLE_TRUST_RELATIONSHIP_PATH = os.path.join(
        AWSEnv.CONFIG_PATH,
        os.environ.get('AWS_L_ROLE_TRUST_RELATIONSHIP_FILENAME'))
    POLICY_PATH = os.path.join(
        AWSEnv.CONFIG_PATH,
        os.environ.get('AWS_L_POLICY_PATH'))
    HANDLER = os.environ.get(
        'AWS_L_HANDLER', 's3_preprocess_to_es.handler')
    DESCRIPTION = os.environ.get(
        'AWS_L_DESCRIPTION',
        'Take new tweets from S3, preprocess and put to ES.')
    TIMEOUT = int(os.environ.get('AWS_L_TIMEOUT', '300'))
    MEMORY_SIZE = int(os.environ.get('AWS_L_MEMORY_SIZE', '128'))
    PATH_TO_FUNC = os.environ.get('AWS_L_PATH_TO_FUNC')
    PATH_TO_LAYER = os.environ.get('AWS_L_PATH_TO_LAYER')


class ESEnv(AWSEnv):
    HOST = os.environ.get('ES_HOST')
    PORT = os.environ.get('ES_PORT')
    INDEX_PREFIX = os.environ.get('ES_INDEX_PREFIX', 'project_')
    DOMAIN = os.environ.get(
        'AWS_ES_DOMAIN', Env.APP_NAME + '-' + Env.ENV + '-es')


class SMEnv(AWSEnv):
    BATCH_SIZE_DEFAULT = int(os.environ.get('BATCH_SIZE_DEFAULT', '1'))
    BATCH_SIZE_FASTTEXT = int(os.environ.get('BATCH_SIZE_FASTTEXT', '100'))
