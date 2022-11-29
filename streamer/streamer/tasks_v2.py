import json
import logging
import os

from awstools.config import StorageMode
from awstools.firehose import firehose, get_stream_name_arn

from .setup_logging import LogDirs

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def is_retweet(data):
    referenced_tweets = data.get('referenced_tweets')
    if referenced_tweets is None: return False
    for rt in referenced_tweets:
        if rt['type'] == 'retweeted':
            return True
    return False


def handle_response(
        data_raw, config_manager,
        store_for_testing=False
):  
    data = json.loads(data_raw)
    tweet_id = data.get('data', {}).get('id')
    matching_rules = list(map(lambda x: x.get('tag'), data.get('matching_rules')))
    
    logger.debug(
        'SUCCESS: Found %d project(s) %s that match this tweet.',
        len(matching_rules), matching_rules)

    if store_for_testing:
        # Store for testing
        with open(os.path.join(
                LogDirs.MATCH_TEST.value, f"{tweet_id}.json"
        ), 'w') as f:
            json.dump(data, f)

    for slug in matching_rules:
        # Get config
        conf = config_manager.get_conf_by_slug(slug)
        if conf.storage_mode == StorageMode.TEST_MODE:
            logger.debug('Running in test mode. Not sending to S3.')
            return

        # Add tracking info
        data['project'] = slug

        if conf.storage_mode in [StorageMode.S3, StorageMode.S3_ES,
                                 StorageMode.S3_NO_RETWEETS,
                                 StorageMode.S3_ES_NO_RETWEETS]:
            if is_retweet(data) and conf.storage_mode in [
                StorageMode.S3_NO_RETWEETS,
                StorageMode.S3_ES_NO_RETWEETS
            ]:
                # Do not store retweets
                return
            # Send to the corresponding delivery stream
            stream_name, _ = get_stream_name_arn(slug)
            _ = firehose.put_record(
                DeliveryStreamName=stream_name,
                Record={'Data': f'{json.dumps(data)}\n'.encode()})

            logger.debug(
                'Pushed processed with id %s to stream %s.',
                tweet_id, stream_name)
