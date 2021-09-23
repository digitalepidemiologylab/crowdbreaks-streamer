import logging
import json

from awstools.s3_to_es import load_to_es, handle_jsonls
# from awstools.s3_to_es import logger as logger_s3_to_es
from awstools.env import ESEnv
from awstools.config import config_manager
from awstools.s3 import get_long_s3_object

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger_s3_to_es.setLevel(logging.DEBUG)


def handler(event, context):
    logger.debug(event)
    for record in event['Records']:
        # Get bucket name and key for new file
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        # Get slug
        slug = [
            name for name in key.split('/')
            if name.startswith(ESEnv.INDEX_PREFIX)
        ]
        if len(slug) != 1:
            logger.error('Slug len != 1.\nKey: %s.\nSlug: %s.', key, slug)
        slug = slug[0][len(ESEnv.INDEX_PREFIX):]
        logger.debug('Slug: %s.', slug)

        # Get model endpoints from config
        model_endpoints = config_manager.get_conf_by_slug(slug).model_endpoints

        # Get S3 object
        jsonls = get_long_s3_object(
            bucket, key,
            {'CompressionType': 'GZIP', 'JSON': {'Type': 'LINES'}})

        statuses_es = handle_jsonls(jsonls, model_endpoints)

        # Load to Elasticsearch
        indices = json.loads(get_long_s3_object(
            ESEnv.BUCKET_NAME, ESEnv.CONFIG_S3_KEY,
            {'CompressionType': 'NONE', 'JSON': {'Type': 'DOCUMENT'}}))
        index_name = indices[slug][-1]
        logger.debug(index_name)

        load_to_es(statuses_es, index_name)
