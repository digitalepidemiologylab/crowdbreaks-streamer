from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from hashlib import sha256
from io import StringIO
import json
import logging
from os.path import join
import re

import boto3
from elasticsearch_dsl import Search, Q
import pandas as pd

from awstools.config import config_manager
from awstools.env import AWSEnv
from awstools.session import es, s3

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

DATE_FORMAT_ES = '%Y-%m-%dT%T.000Z'
DATE_FORMAT_S3 = '%Y%m%d%H%M%S'


def only_digits(string):
    return re.sub('[^0-9]', '', string)


def put_csv_to_s3(csv_buffer, conf_slug, text=False):
    df_sha256 = sha256(csv_buffer.getvalue().encode()).hexdigest()
    datetime_stamp = datetime.now().strftime(DATE_FORMAT_S3)
    if text:
        f_name = f"auto_sample-text-{conf_slug}-{datetime_stamp}-{df_sha256}.csv"
    else:
        f_name = f"auto_sample-no_text-{conf_slug}-{datetime_stamp}-{df_sha256}.csv"
    output_key = join(
        AWSEnv.SAMPLES_PREFIX, f"project_{conf_slug}", f_name)
    s3.put_object(
        Body=csv_buffer.getvalue(), Bucket=AWSEnv.BUCKET_NAME,
        Key=output_key)
    return output_key


def handler(event, context):
    logger.debug(event['resources'][0])
    cron_arn = event['resources'][0]
    cron_name = cron_arn.split('/')[-1]
    client = boto3.client('events')
    rule_descr = client.describe_rule(Name=cron_name)
    logger.info(rule_descr)
    cron = rule_descr['ScheduleExpression']
    logger.info(cron)
    if 'cron' in cron:
        cron_inside = cron[5:-1]
        logger.info(cron_inside)
        sample_each = int(only_digits(cron_inside.split(' ')[3]))
        logger.info('Sample each %d months.', sample_each)
    else:
        logger.error('Then event is not cron.')
        return

    relevant_confs = [conf for conf in config_manager.config if conf.auto_mturking is True]

    sample_status = {'text': [], 'no_text': []}

    for conf in relevant_confs:
        s = Search(using=es, index=conf.es_index_name)

        range_dict = {
            'created_at': {
                'gte': (date.today() + relativedelta(
                    months=-sample_each
                )).strftime(DATE_FORMAT_ES)
            }
        }

        q = ~Q('exists', field='is_retweet') & \
            ~Q('exists', field='has_quote') & \
            Q('range', **range_dict)

        random_sample = { 'boost_mode':
            'replace', 'functions': [{ 'random_score': {} }], 'query': q }

        s.query = Q('function_score', **random_sample)
        try:
            s = s[0:conf.tweets_per_batch]
        except AttributeError as exc:
            logger.error('%s: %s', type(exc).__name__, str(exc))
            continue
        s = s.source(['text'])
        response = s.execute()

        sampled_tweets = [[hit.meta.id, hit.text] for hit in response]
        sampled_tweets_df = pd.DataFrame(
            sampled_tweets, columns=['id_str', 'text'])

        # Save a CSV for an MTurk batch
        csv_buffer = StringIO()
        sampled_tweets_df.to_csv(
            csv_buffer, header=False, index=False, columns=['id_str'])
        output_key = put_csv_to_s3(csv_buffer, conf.slug, text=False)
        sample_status['no_text'].append(output_key)

        # Save a CSV for manual inspection
        csv_buffer = StringIO()
        sampled_tweets_df.to_csv(
            csv_buffer, header=True, index=True)
        output_key = put_csv_to_s3(csv_buffer, conf.slug, text=True)
        sample_status['text'].append(output_key)

    s3.put_object(
        Body=json.dumps(sample_status), Bucket=AWSEnv.BUCKET_NAME,
        Key=AWSEnv.SAMPLE_STATUS_S3_KEY)
