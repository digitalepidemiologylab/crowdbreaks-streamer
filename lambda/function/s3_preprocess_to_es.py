import logging
import json
# import re
import os
from copy import deepcopy

import boto3
from requests_aws4auth import AWS4Auth
from elasticsearch import Elasticsearch, RequestsHttpConnection, ConflictError
# from elasticsearch.helpers import bulk
import twiprocess as twp


from env import Env, ESEnv, SMEnv
from config import ConfigManager, get_s3_object


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key, credentials.secret_key,
    ESEnv.REGION, "es",
    session_token=credentials.token
)

sagemaker = boto3.client(
    'sagemaker-runtime',
    region_name=ESEnv.REGION,
    aws_access_key_id=credentials.access_key,
    aws_secret_access_key=credentials.secret_key,
    aws_session_token=credentials.token
)

es = Elasticsearch(
    hosts=[{'host': ESEnv.HOST, 'port': ESEnv.PORT}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

s3 = boto3.client(
    's3',
    region_name=ESEnv.REGION,
    aws_access_key_id=credentials.access_key,
    aws_secret_access_key=credentials.secret_key,
    aws_session_token=credentials.token
)


# def preprocess(status):
#     status = status.replace('\n', ' ')
#     status = re.sub(' +', ' ', status).strip()
#     return status


def get_batch_size(model_type):
    if model_type == 'fasttext':
        return SMEnv.BATCH_SIZE_FASTTEXT
    logger.warning(
        'Model type %s unknown. Using default batch size.', model_type)
    return SMEnv.BATCH_SIZE_DEFAULT


def labels_to_int(labels):
    """Heuristic to convert label to numeric value.
    Parses leading numbers in label tags such as 1_worried -> 1.
    If any conversion fails, returns None.
    """
    label_vals = []
    for label in labels:
        if label == 'positive':
            label_vals.append(1)
        elif label == 'negative':
            label_vals.append(-1)
        elif label == 'neutral':
            label_vals.append(0)
        else:
            label_split = label.split('_')
            try:
                label_val = int(label_split[0])
            except ValueError:
                return
            label_vals.append(label_val)
    return label_vals


def preprocess(preprocessing_config, texts):
    # Preprocess data
    try:
        standardize_func_name = preprocessing_config['standardize_func_name']
        del preprocessing_config['standardize_func_name']
    except KeyError:
        standardize_func_name = None
    if standardize_func_name is not None:
        logger.debug('Standardizing data...')
        standardize_func = getattr(
            __import__(
                'twiprocess.standardize',
                fromlist=[standardize_func_name]),
            standardize_func_name)
        logger.info(standardize_func)
        texts = [standardize_func(text) for text in texts]
    if preprocessing_config != {}:
        logger.debug('Preprocessing data...')
        texts = [
            twp.preprocess(text, **preprocessing_config) for text in texts]
    return texts


def predict(endpoint_name, preprocessing_config, texts, batch_size):
    """Runs prediction in batches."""
    outputs = []
    for i in range(0, len(texts), batch_size):
        logger.debug('Batch %d', i)
        batch = preprocess(preprocessing_config, texts[i:i + batch_size])
        logger.debug('Batch:\n%s', batch)

        try:
            response = sagemaker.invoke_endpoint(
                EndpointName=endpoint_name,
                Body=json.dumps({'text': batch}),
                ContentType='application/json'
            )
        except sagemaker.exceptions.ModelError as exc:
            logger.error('%s: %s', type(exc).__name__, str(exc))
            return None

        predictions = json.loads(
            response['Body'].read().decode('utf-8')
        )['predictions']

        outputs.extend([{
            'labels': pred['labels'],
            'probabilities': pred['probabilities']
        } for pred in predictions])

    label_valss = [labels_to_int(output['labels']) for output in outputs]
    if all(label_valss):
        outputs = [{
            'label_vals': label_vals, **output
        } for output, label_vals in zip(outputs, label_valss)]

    return outputs


def handler(event, context):
    for record in event['Records']:
        # Get stream config from S3
        config_manager = ConfigManager(s3)

        # Get bucket name and key for new file
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        # Get slug
        slug = [
            name for name in key.split('/')
            if name.startswith(Env.S3_BUCKET_PREFIX)
        ]
        if len(slug) != 1:
            logger.error('Slug len != 1.\nKey: %s.\nSlug: %s.', key, slug)
        slug = slug[0].split('_')[1]
        logger.debug('Slug: %s.', slug)

        # Get model endpoints from config
        model_endpoints = config_manager.get_conf_by_slug(slug).model_endpoints

        # Get S3 object
        records = get_s3_object(
            s3, bucket, key,
            {'CompressionType': 'GZIP', 'JSON': {'Type': 'LINES'}})

        try:
            statuses = [json.loads(record) for record in records.splitlines()]
        except json.JSONDecodeError as exc:
            logger.error('%s: %s', type(exc).__name__, str(exc))
            logger.error('Rec:\n%s', str(record))
            continue

        logger.debug('Num records: %s.', len(statuses))

        texts = [status['text'] for status in statuses]

        # Read off stream config and prepare a template for metadata
        meta = {}
        endpoint_names = {}
        run_names = {}
        model_types = {}
        preprocessing_configs = {}
        for problem_type in model_endpoints:
            endpoint_names[problem_type] = []
            run_names[problem_type] = []
            model_types[problem_type] = []
            meta[problem_type] = {'endpoints': {}}
            for endpoint_name, info in \
                    model_endpoints[problem_type]['active'].items():
                endpoint_names[problem_type].append(endpoint_name)
                run_names[problem_type].append(info['run_name'])
                model_types[problem_type].append(info['model_type'])

                key = os.path.join(
                    ESEnv.ENDPOINTS_PREFIX, endpoint_name + '.json')

                run_config = get_s3_object(
                    s3, ESEnv.BUCKET_NAME, key,
                    {'CompressionType': 'NONE', 'JSON': {'Type': 'DOCUMENT'}})

                preprocessing_configs[problem_type].append(
                    run_config['preprocess'])

        metas = [deepcopy(meta)] * len(texts)
        logger.info('Endpoint names:\n%s.', endpoint_names)

        # Fill metadata with predictions
        for problem_type in endpoint_names:
            for endpoint_name, model_type, run_name, preprocessing_config in zip(
                    endpoint_names[problem_type],
                    model_types[problem_type],
                    run_names[problem_type],
                    preprocessing_configs[problem_type]
            ):
                batch_size = get_batch_size(model_type)

                outputs = predict(
                    endpoint_name, preprocessing_config, texts, batch_size)

                if outputs is None:
                    continue

                for i, output in enumerate(outputs):
                    max_prob = max(output['probabilities'])
                    ind_max_prob = output['probabilities'].index(max_prob)
                    metas[i][problem_type]['endpoints'][run_name] = {
                        'probability': max_prob,
                        'label': output['labels'][ind_max_prob],
                        'label_val': output['label_vals'][ind_max_prob]
                    }

        # Add 'meta' field to statuses
        for i in range(len(statuses)):
            # This way, if prediction fails, we at least store the tweet
            statuses[i]['meta'] = metas[i] \
                if metas[i] != meta else None

        logger.debug('\n\n'.join([json.dumps(status) for status in statuses]))

        # Load to Elasticsearch
        index_name = \
            ESEnv.INDEX_PREFIX + slug

        loads = 0
        errors = 0
        for i, status in enumerate(statuses):
            try:
                es.create(
                    index=index_name, id=status['id'],
                    body=status, doc_type='tweet')
                logger.debug('Loaded rec %d, id %d.', i, status['id'])
                loads += 1
            except ConflictError as exc:
                # Happens when a document with the same ID
                # already exists.
                errors += 1
                logger.warning(
                    'Rec %d, id %d already exists.', i, status['id'])
                # logger.error('%s: %s', type(exc).__name__, str(exc))

        logger.info(
            'Loaded %d/%d to Elasticsearch, already exist %d/%d.',
            loads, len(statuses), errors, len(statuses))
