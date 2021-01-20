import logging
import os
import json

from twiprocess.processtweet import ProcessTweet
from awstools.env import Env, KFEnv
from awstools.firehose import firehose

from .setup_logging import LogDirs
from .config import StorageMode
from .utils.match_keywords import match_keywords

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def handle_tweet(
        status, config_manager,
        store_for_testing=False
):
    tweet = ProcessTweet(status)
    status_id = tweet.id
    # Reverse match to find project
    matching_keywords = match_keywords(tweet, config_manager.config)
    matching_projects = list(matching_keywords.keys())
    if matching_projects == []:
        # Could not match keywords.
        # This might occur quite frequently
        # e.g. when tweets are collected accross different languages/keywords
        logger.debug(
            'Status %s could not be matched against any existing projects.',
            status_id)
        if Env.UNMATCHED_STORE_LOCALLY == 1:
            # Store to a separate file for later analysis
            with open(os.path.join(
                    LogDirs.UNMATCHED.value, f"{status_id}.json"
            ), 'w') as f:
                json.dump(status, f)
        if Env.UNMATCHED_STORE_S3 == 1:
            _ = firehose.put_record(
                DeliveryStreamName=f'{KFEnv.APP_NAME}-'
                                   f'{KFEnv.UNMATCHED_STREAM_NAME}',
                Record={'Data': f'{json.dumps(status)}\n'.encode()})
        return

    logger.debug(
        'SUCCESS: Found %d project(s) %s that match this status.',
        len(matching_projects), matching_projects)
    status['matching_keywords'] = matching_keywords

    if store_for_testing:
        # Store for testing
        with open(os.path.join(
                LogDirs.MATCH_TEST.value, f"{status_id}.json"
        ), 'w') as f:
            json.dump(status, f)

    for slug in matching_projects:
        # Get config
        conf = config_manager.get_conf_by_slug(slug)
        if conf.storage_mode == StorageMode.TEST_MODE:
            logger.debug('Running in test mode. Not sending to S3.')
            return

        # Add tracking info
        # 19.01.2021: lang, slug and matching_keywords are there anyway,
        # and there's no point to store all keywords in every tweet
        # status['_tracking_info'] = config_manager.get_tracking_info(slug)
        status['project'] = slug

        if conf.storage_mode in \
                [StorageMode.S3_ES, StorageMode.S3_ES_NO_RETWEETS]:
            if tweet.is_retweet and \
                    conf.storage_mode == StorageMode.S3_ES_NO_RETWEETS:
                # Do not store retweets on ES
                return
            # Send to the corresponding delivery stream
            stream_name = f'{KFEnv.APP_NAME}-{slug}'
            _ = firehose.put_record(
                DeliveryStreamName=stream_name,
                Record={'Data': f'{json.dumps(status)}\n'.encode()})

            logger.debug(
                'Pushed processed with id %s to stream %s.',
                status_id, stream_name)
