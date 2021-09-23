import logging
import json
import os
import io
from pathlib import Path
from datetime import datetime
from elasticsearch import RequestError

from .env import ESEnv
from .session import s3, es
from .s3 import get_long_s3_object

logger = logging.getLogger(__name__)

if ESEnv.DEBUG == 1:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


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


def create_index(slug, lang, only_new=False):
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

    now = datetime.now()
    index_name = ESEnv.INDEX_PREFIX + \
        slug + '_' + now.strftime('%Y-%m-%d_%H-%M-%S')

    indices = json.loads(get_long_s3_object(
        ESEnv.BUCKET_NAME, ESEnv.CONFIG_S3_KEY,
        {'CompressionType': 'NONE', 'JSON': {'Type': 'DOCUMENT'}}))
    if only_new:
        # When a new project is created, we want to create an index for it
        # and not create new indices for the projects that are already there
        if indices.get(slug) is None:
            indices[slug] = [index_name]
        else:
            index_name = indices[slug][-1]
    else:
        try:
            indices[slug].append(index_name)
        except KeyError:
            indices[slug] = [index_name]

    # if es.indices.exists(index_name):
    #     logger.info('Index %s already exists.', index_name)
    # else:
    try:
        logger.info('Created index %s.', index_name)
        es.indices.create(index_name, body=mapping)
    except RequestError as exc:
        if 'already_exists' in exc.error:
            logger.info('Index %s already exists.', index_name)
        else:
            raise exc

    indices = io.BytesIO(bytes(json.dumps(indices), encoding='utf-8'))
    s3.upload_fileobj(indices, ESEnv.BUCKET_NAME, ESEnv.CONFIG_S3_KEY)
    logger.info('Indices JSON updated.')
