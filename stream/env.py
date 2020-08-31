"""Application configuration."""
import os
from aenum import Constant
from dotenv import load_dotenv

load_dotenv()


class Env(Constant):
    """Base configuration."""
    # Environment
    ENV = os.environ.get('ENV', 'dev')
    APP_NAME = os.environ.get('APP_NAME')
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


class AWSEnv(Constant):
    """AWS config (for storing in S3, accessing Elasticsearch)."""
    ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    ACCOUNT_NUM = os.environ.get('AWS_ACCOUNT_NUM')
    BUCKET_NAME = os.environ.get(
        'AWS_BUCKET_NAME', Env.APP_NAME + '-' + Env.ENV)
    REGION = os.environ.get('AWS_REGION', 'eu-central-1')


class KFEnv(Env, AWSEnv):
    BUCKET_ARN = f'arn:aws:s3:{AWSEnv.REGION}:{AWSEnv.ACCOUNT_NUM}:' \
                 f'{AWSEnv.BUCKET_NAME}'
    ROLE_TRUST_RELATIONSHIP_PATH = os.path.join(
        Env.CONFIG_PATH,
        os.environ.get('ROLE_TRUST_RELATIONSHIP_FILENAME'))
    POLICY_PATH = os.path.join(
        Env.CONFIG_PATH,
        os.environ.get('POLICY_PATH'))
