from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from hashlib import sha256
from io import StringIO
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

DATE_FORMAT = '%Y-%m-%dT%T.000Z'


def only_digits(string):
    return re.sub('[^0-9]', '', string)


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

    for conf in relevant_confs:
        s = Search(using=es, index=conf.es_index_name)

        range_dict = {
            'created_at': {
                'gte': (date.today() + relativedelta(
                    months=-sample_each
                )).strftime(DATE_FORMAT)
            }
        }

        q = ~Q('exists', field='is_retweet') & \
            ~Q('exists', field='has_quote') & \
            Q('range', **range_dict)

        random_sample = { 'boost_mode':
            'replace', 'functions': [{ 'random_score': {} }], 'query': q }

        s.query = Q('function_score', **random_sample)
        s = s[0:1000]
        s = s.source(['id_str', 'text'])
        response = s.execute()

        sampled_tweets = [[hit.id_str, hit.text] for hit in response]

        sampled_tweets_df = pd.DataFrame(
            sampled_tweets, columns=['id_str', 'text'])

        # {'bool': {
        #     'must_not': [{'exists': {'field': 'is_retweet'}}, {'exists': {'field': 'has_quote'}}],
        #     'must': [{'range': {'created_at': {'gte': '2021-12-01T00:00:00.000Z'}}}]
        # }}

        csv_buffer = StringIO()
        sampled_tweets_df.to_csv(csv_buffer)
        df_sha256 = sha256(csv_buffer.getvalue().encode()).hexdigest()
        datetime_stamp = datetime.now().strftime('%Y-%m-%dT%T')
        output_key = join(
            AWSEnv.SAMPLES_PREFIX, f"project_{conf.slug}",
            f"auto-sample_{conf.slug}_{datetime_stamp}_{df_sha256}.csv")
        s3.put_object(
            Body=csv_buffer.getvalue(), Bucket=AWSEnv.BUCKET_NAME,
            Key=output_key)
