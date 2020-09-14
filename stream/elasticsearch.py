import logging
import json

import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from stream.env import ESEnv

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    ESEnv.ACCESS_KEY_ID, ESEnv.SECRET_ACCESS_KEY,
    ESEnv.REGION, "es",
    session_token=credentials.token
)

es = Elasticsearch(
    hosts=[{'host': ESEnv.HOST, 'port': ESEnv.PORT}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)


def create_index(slug):
    index_name = ESEnv.INDEX_PREFIX + slug

    with open('lambda/function/tweet_mapping.json', 'r') as f:
        mapping = json.load(f)

    if es.indices.exists(index_name):
        logger.info('Index %s already exists.', index_name)
    else:
        logger.info('Created index %s.', index_name)
        es.indices.create(index_name, body=mapping)
