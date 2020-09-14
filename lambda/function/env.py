"""Application configuration."""
import os
from aenum import Constant


class ESEnv(Constant):
    REGION = os.environ.get('AWS_REGION')
    HOST = os.environ.get('ES_HOST')
    PORT = os.environ.get('ES_PORT')
    INDEX_PREFIX = os.environ.get('ES_INDEX_PREFIX', 'project_')
