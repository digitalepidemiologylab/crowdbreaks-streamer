"""Application configuration."""
import os
from pathlib import Path
from aenum import Constant
from dotenv import load_dotenv

env_path = os.path.join(Path(__file__).parent.absolute(), 'awstools.env')
load_dotenv(dotenv_path=env_path)


class Env(Constant):
    """Base configuration."""
    # Environment
    ENV = os.environ.get('ENV', 'stg').lower()
    APP_NAME = os.environ.get('APP_NAME').lower()
    DEBUG = int(os.environ.get('DEBUG', 'False') == 'True')

    # Unmatched tweets
    UNMATCHED_STORE_LOCALLY = int(os.environ.get(
        'UNMATCHED_STORE_LOCALLY', 'False') == 'True')

    UNMATCHED_STORE_S3 = int(os.environ.get(
        'UNMATCHED_STORE_S3', 'False') == 'True')

    # Paths
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    CONFIG_PATH = os.path.abspath(os.path.join(APP_DIR, 'config'))

    # Other
    NUM_WORKERS = os.environ.get('NUM_WORKERS', 4)
    TIMEZONE = os.environ.get('TIMEZONE', 'Europe/Zurich')


class AWSEnv(Env):
    """AWS config (for storing in S3, accessing Elasticsearch)."""
    REGION = os.environ.get('AWS_REGION', 'eu-central-1')
    ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    SESSION_TOKEN = os.environ.get('AWS_SESSION_TOKEN', -1)
    ACCOUNT_NUM = os.environ.get('AWS_ACCOUNT_NUM')

    BUCKET_NAME = os.environ.get(
        'AWS_BUCKET_NAME', Env.APP_NAME + '-' + Env.ENV)
    STORAGE_BUCKET_PREFIX = os.environ.get(
        'AWS_STORAGE_BUCKET_PREFIX', 'tweets/project_')

    STREAM_CONFIG_S3_KEY = os.environ.get(
        'AWS_STREAM_CONFIG_S3_KEY', 'configs/stream/stream.json')
    STREAM_STATE_S3_KEY = os.environ.get(
        'AWS_STREAM_STATE_S3_KEY', 'configs/stream/state.json')
    ENDPOINTS_PREFIX = os.environ.get(
        'ENDPOINTS_PREFIX', 'configs/models/')

    LAMBDA_S3_ES_NAME = os.environ.get(
        'LAMBDA_S3_ES_NAME', 's3-to-es')


class KFEnv(AWSEnv):
    ROLE_TRUST_RELATIONSHIP_PATH = os.path.join(
        AWSEnv.CONFIG_PATH,
        os.environ.get('AWS_KF_ROLE_TRUST_RELATIONSHIP_FILENAME'))
    POLICY_PATH = os.path.join(
        AWSEnv.CONFIG_PATH,
        os.environ.get('AWS_KF_POLICY_FILENAME'))
    BUFFER_SIZE = int(os.environ.get('AWS_KF_BUFFER_SIZE', '50'))
    BUFFER_INTERVAL = int(os.environ.get('AWS_KF_BUFFER_INTERVAL', '60'))
    UNMATCHED_STREAM_NAME = os.environ.get(
        'AWS_KF_UNMATCHED_STREAM_NAME', 'unmatched')


class LEnv(AWSEnv):
    ROLE_TRUST_RELATIONSHIP_PATH = os.path.join(
        AWSEnv.CONFIG_PATH,
        os.environ.get('AWS_L_ROLE_TRUST_RELATIONSHIP_FILENAME'))
    HANDLER = os.environ.get(
        'AWS_L_HANDLER', 'lambda.handler')
    TIMEOUT = int(os.environ.get('AWS_L_TIMEOUT', '300'))
    MEMORY_SIZE = int(os.environ.get('AWS_L_MEMORY_SIZE', '128'))
    BUCKET_FOLDER = os.environ.get('AWS_L_BUCKET_FOLDER', 'lambda/')
    EXTENSION = os.environ.get('AWS_L_EXTENSION', 'zip')


class ESEnv(AWSEnv):
    HOST = os.environ.get('ES_HOST')
    PORT = os.environ.get('ES_PORT')
    INDEX_PREFIX = os.environ.get('ES_INDEX_PREFIX', 'project_')
    DOMAIN = os.environ.get('ES_DOMAIN', Env.APP_NAME + '-' + Env.ENV)
    CONFIG_S3_KEY = os.environ.get(
        'ES_CONFIG_S3_KEY', 'configs/stream/elasticsearch.json')


class ECSEnv(AWSEnv):
    CLUSTER = os.environ.get('ECS_CLUSTER')
    SERVICE = os.environ.get('ECS_SERVICE')


class SMEnv(AWSEnv):
    BATCH_SIZE_DEFAULT = int(os.environ.get('BATCH_SIZE_DEFAULT', '1'))
    BATCH_SIZE_FASTTEXT = int(os.environ.get('BATCH_SIZE_FASTTEXT', '100'))
