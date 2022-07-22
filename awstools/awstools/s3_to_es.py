import logging
import json
# import re
import os
from copy import deepcopy

from elasticsearch import ConflictError, ElasticsearchException, RequestError
# from elasticsearch.helpers import bulk
from geocode.geocode import Geocode

import twiprocess as twp
from twiprocess.processtweet import ProcessTweet
from awstools.env import ESEnv, SMEnv
from awstools.session import session, es
from awstools.s3 import get_long_s3_object

DEFAULT_STANDARDIZE_FUNC_NAME = 'standardize_anonymize'

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

geo_code = Geocode()
geo_code.load()

sagemaker = session.client('sagemaker-runtime')


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
        standardize_func_name = DEFAULT_STANDARDIZE_FUNC_NAME
    if standardize_func_name is not None:
        logger.debug('Standardizing data...')
        standardize_func = getattr(
            __import__(
                'twiprocess.standardize',
                fromlist=[standardize_func_name]),
            standardize_func_name)
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
            outputs.extend([None] * batch_size)
        finally:
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


def create_doc(
        status_id, status_es, index_name, loads, errors, request_errors):
    try:
        es.create(
            index=index_name, id=status_id,
            body=json.dumps(status_es), doc_type='_doc')
        logger.debug('Loaded status with id %s.', status_id)
        loads += 1
    except ConflictError as exc:
        # Happens when a document with the same ID
        # already exists.
        errors += 1
        logger.warning(
            'Status with id %s already exists.', status_id)
        # logger.error('%s: %s', type(exc).__name__, str(exc))
    except RequestError as exc:
        errors += 1
        request_errors += 1
        if request_errors < 5:
            # logger.error(json.dumps(status_es))
            # logger.error(type(status_es['geo_info']['country_code']))
            logger.error(
                '%s: %s. Retrying...', type(exc).__name__, str(exc))
            _ = create_doc(
                status_id, status_es, index_name,
                loads, errors, request_errors)
        else:
            request_errors = 0
    except ElasticsearchException as exc:
        errors += 1
        logger.error('%s: %s', type(exc).__name__, str(exc))
    return loads, errors


def load_to_es(statuses_es, index_name):
    loads = 0
    errors = 0
    request_errors = 0

    for status_es in statuses_es:
        logger.debug(status_es)
        status_id = status_es.pop('id')
        loads, errors = create_doc(
            status_id, status_es, index_name,
            loads, errors, request_errors)

    logger.info(
        'Loaded %d/%d to Elasticsearch, already exist %d/%d.',
        loads, len(statuses_es), errors, len(statuses_es))


def handle_jsonls(jsonls, model_endpoints):
    statuses = []
    for jsonl in jsonls.splitlines():
        try:
            statuses.append(json.loads(jsonl))
        except json.JSONDecodeError as exc:
            logger.error('%s: %s', type(exc).__name__, str(exc))
            logger.error('JSONL:\n%s', str(jsonl))
            continue

    logger.debug('Num statuses: %s.', len(statuses))

    texts = [status['text'] for status in statuses]

    # Read off stream config and prepare a template for metadata
    prediction = {}
    endpoint_names = {}
    run_names = {}
    model_types = {}
    preprocessing_configs = {}
    for question_tag in model_endpoints:
        endpoint_names[question_tag] = []
        run_names[question_tag] = []
        model_types[question_tag] = []
        prediction[question_tag] = {'endpoints': {}}
        preprocessing_configs[question_tag] = []
        for endpoint_name, info in \
                model_endpoints[question_tag]['active'].items():
            endpoint_names[question_tag].append(endpoint_name)
            run_names[question_tag].append(info['run_name'])
            model_types[question_tag].append(info['model_type'])

            key = os.path.join(
                ESEnv.ENDPOINTS_PREFIX, endpoint_name + '.json')
            logger.debug(f'Key: {key}')

            try:
                logger.debug('Trying to load from S3')
                run_config = json.loads(get_long_s3_object(
                    ESEnv.BUCKET_NAME, key,
                    {'CompressionType': 'NONE', 'JSON':
                        {'Type': 'DOCUMENT'}}))
            except Exception:
                logger.debug('Some error, addind an empty config')
                run_config = {'preprocess': {}}

            preprocessing_configs[question_tag].append(
                run_config['preprocess'])

    predictions = [deepcopy(prediction)] * len(texts)
    logger.info('Endpoint names:\n%s.', endpoint_names)

    def predictions_from_output(output, primary=False):
        max_prob = max(output['probabilities'])
        ind_max_prob = output['probabilities'].index(max_prob)
        predictions = {
            'probability': max_prob,
            'label': output['labels'][ind_max_prob],
            'label_val': output['label_vals'][ind_max_prob]
        }
        if primary:
            return {'primary': predictions}
        else:
            return predictions

    # Fill metadata with predictions
    for question_tag in endpoint_names:
        primary_endpoint_name = model_endpoints[question_tag]['primary']
        for (
            endpoint_name,
            model_type,
            run_name,
            preprocessing_config
        ) in zip(
            endpoint_names[question_tag],
            model_types[question_tag],
            run_names[question_tag],
            preprocessing_configs[question_tag]
        ):
            batch_size = get_batch_size(model_type)

            outputs = predict(
                endpoint_name, preprocessing_config, texts, batch_size)

            if outputs is None:
                continue

            if endpoint_name == primary_endpoint_name:
                for i, output in enumerate(outputs):
                    predictions[i][question_tag]['endpoints'] = \
                        predictions_from_output(output, primary=True)

            for i, output in enumerate(outputs):
                predictions[i][question_tag]['endpoints'][run_name] = \
                    predictions_from_output(output)

    # Process tweets for ES
    statuses_es = []
    for status in statuses:
        statuses_es.append(ProcessTweet(
            status, standardize_func='standardize_anonymize', geo_code=geo_code
        ).extract_es(extract_geo=True))

    # Add 'predictions' field to statuses
    for i in range(len(statuses)):
        # This way, if prediction fails, we at least store the tweet
        if predictions[i] != prediction:
            # Add the 'predictions' field to statuses that were
            # successfully predicted
            statuses_es[i]['predictions'] = predictions[i]
        # Else, keep the failed/inexistent predictions empty

    logger.debug('\n\n'.join([json.dumps(status) for status in statuses_es]))

    return statuses_es
