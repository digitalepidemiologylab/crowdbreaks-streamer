import logging
import os
import json

from .setup_logging import LogDirs
from .config import StorageMode
from .utils.match_keywords import match_keywords

logger = logging.getLogger(__name__)


def handle_tweet(
        status, config, store_unmatched_tweets=False
):
    status_id = status['id_str']
    # Reverse match to find project
    matching_keywords = match_keywords(status, config)
    matching_projects = list(matching_keywords.keys())
    if len(matching_projects) == 0:
        # Could not match keywords.
        # This might occur quite frequently
        # e.g. when tweets are collected accross different languages/keywords
        logger.info(
            'Status %s could not be matched against any existing projects.',
            status_id)
        if store_unmatched_tweets:
            # Store to a separate file for later analysis
            with open(os.path.join(
                    LogDirs.UNMATCHED.value, f"{status_id}.json"
            ), 'w') as f:
                json.dump(status, f)
        return

    logger.info(
        'SUCCESS: Found %d project(s) %s that match this status.',
        len(matching_projects), matching_projects)
    status['matching_keywords'] = matching_keywords

    # Store for testing
    with open(os.path.join(
            LogDirs.MATCH_TEST.value, f"{status_id}.json"
    ), 'w') as f:
        json.dump(status, f)
    for slug in matching_projects:
        # Get config
        conf = config.get_conf_by_slug(slug)
        if conf.storage_mode == StorageMode.TEST_MODE:
            logger.debug('Running in test mode. Not sending to S3.')
            return

        # Add tracking info
        status['_tracking_info'] = config.get_tracking_info(slug)
        status['_tracking_info']['matching_keywords'] = matching_keywords[slug]

        if send_to_es and \
                conf.storage_mode in \
                [StorageMode.S3_ES, StorageMode.S3_ES_NO_RETWEETS]:
            if 'retweeted_status' in status and \
                    conf.storage_mode == StorageMode.S3_ES_NO_RETWEETS:
                # Do not store retweets on ES
                return
            # Send to ES
            processed_tweet = pt.get_processed_tweet()
            logger.debug(
                'Pushing processed with id %s to ES queue.', {status_id})
            es_tweet_obj = {'processed_tweet': processed_tweet, 'id': status_id}
            if len(conf['model_endpoints']) > 0:
                # Prepare for prediction
                es_tweet_obj['text_for_prediction'] = \
                    {'text': pt.get_text(anonymize=True), 'id': status_id}
            es_queue.push(json.dumps(es_tweet_obj).encode(), slug)
