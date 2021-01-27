import logging
import json
import os
from pathlib import Path
from datetime import datetime

import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from .env import ESEnv

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

# https://developer.twitter.com/en/docs/twitter-for-websites/supported-languages
twi_langs = {
    'en': 'english (default)',
    'ar': 'arabic',
    'bn': 'bengali',
    'cs': 'czech',
    'da': 'danish',
    'de': 'german',
    'el': 'greek',
    'es': 'spanish',
    'fa': 'persian',
    'fi': 'finnish',
    'fil': 'filipino',
    'fr': 'french',
    'he': 'hebrew',
    'hi': 'hindi',
    'hu': 'hungarian',
    'id': 'indonesian',
    'it': 'italian',
    'ja': 'japanese',
    'ko': 'korean',
    'msa': 'malay',
    'nl': 'dutch',
    'no': 'norwegian',
    'pl': 'polish',
    'pt': 'portuguese',
    'ro': 'romanian',
    'ru': 'russian',
    'sv': 'swedish',
    'th': 'thai',
    'tr': 'turkish',
    'uk': 'ukrainian',
    'ur': 'urdu',
    'vi': 'vietnamese',
    'zh-cn': 'chinese (simplified)',
    'zh-tw': 'chinese (traditional)'}

# https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-lang-analyzer.html
es_langs = [
    'arabic', 'armenian', 'basque', 'bengali', 'brazilian', 'bulgarian',
    'catalan', 'cjk', 'czech', 'danish', 'dutch', 'english', 'estonian',
    'finnish', 'french', 'galician', 'german', 'greek', 'hindi', 'hungarian',
    'indonesian', 'irish', 'italian', 'latvian', 'lithuanian', 'norwegian',
    'persian', 'portuguese', 'romanian', 'russian', 'sorani', 'spanish',
    'swedish', 'turkish', 'thai']


def create_index(slug, lang):
    mapping_path = os.path.join(
        Path(__file__).parent.absolute(),
        'config/tweet_mapping.json')
    with open(mapping_path, 'r') as f:
        mapping = json.load(f)

    logger.info(mapping)

    mapping_str = json.dumps(mapping)
    es_lang = twi_langs[lang] if twi_langs[lang] in es_langs else 'english'
    mapping_str = mapping_str.replace('english', es_lang)
    mapping = json.loads(mapping_str)

    # For rotating indices, maybe later
    # now = datetime.now()
    # index_name = ESEnv.INDEX_PREFIX + slug + '_' + str(now.date())
    index_name = ESEnv.INDEX_PREFIX + slug

    if es.indices.exists(index_name):
        logger.info('Index %s already exists.', index_name)
    else:
        logger.info('Created index %s.', index_name)
        es.indices.create(index_name, body=mapping)
