import logging
import os
import json

from .config import Conf
from .logging import LogDirs
from .reverse_tweet_matcher import ReverseTweetMatcher
from .stream_config import StreamConfig

logger = logging.getLogger(__name__)


def handle_tweet(
        tweet, send_to_es=True, use_pq=True, store_unmatched_tweets=False
):
    tweet_id = tweet['id_str']
    # Reverse match to find project
    tweet_matcher = ReverseTweetMatcher(tweet=tweet)
    matching_keywords = tweet_matcher.match_projects()
    matching_projects = list(matching_keywords.keys())
    if len(matching_projects) == 0:
        # Could not match keywords.
        # This might occur quite frequently
        # e.g. when tweets are collected accross different languages/keywords
        logger.info(
            'Tweet %s could not be matched against any existing projects.',
            tweet_id)
        if store_unmatched_tweets:
            # Store to a separate file for later analysis
            with open(os.path.join(
                    LogDirs.UNMATCHED, f"{tweet_id}.json"
            ), 'w') as f:
                json.dump(tweet, f)
        return

    logger.info(
        'SUCCESS: Found %d project(s) %s that match this tweet.',
        len(matching_projects), matching_projects)
    tweet['matching_keywords'] = matching_keywords

    # Store for testing
    with open(os.path.join(
            LogDirs.REVERSE_MATCH_TEST, f"{tweet_id}.json"
    ), 'w') as f:
        json.dump(tweet, f)
    stream_config = StreamConfig()
    for slug in matching_projects:
        # Get config
        stream_config = stream_config.get_conf_by_slug(slug)
        if stream_config['storage_mode'] == 'test_mode':
            logger.debug('Running in test mode. Not sending to S3.')
            return

        # Add tracking info
        tweet['_tracking_info'] = stream_config.get_tracking_info(slug)
        tweet['_tracking_info']['matching_keywords'] = matching_keywords[slug]

    #     # Preprocess tweet
    #     pt = ProcessTweet(tweet, project_locales=stream_config['locales'])
    #     pt.process()

    #     # Possibly add tweet to trending tweets
    #     if stream_config['compile_trending_tweets']:
    #         trending_tweets = TrendingTweets(slug, project_locales=stream_config['locales'], connection=connection)
    #         trending_tweets.process(tweet)

    #     # Extract trending topics
    #     if stream_config['compile_trending_topics']:
    #         trending_topics = TrendingTopics(slug, project_locales=stream_config['locales'], project_keywords=stream_config['keywords'], connection=connection)
    #         trending_topics.process(tweet)
    #     if stream_config['compile_data_dump_ids'] and config.ENV == 'prd':
    #         data_dump_ids = DataDumpIds(slug, connection=connection)
    #         data_dump_ids.add(tweet_id)
    #         if pt.has_place:
    #             data_dump_ids = DataDumpIds(slug, mode='has_place', connection=connection)
    #             data_dump_ids.add(tweet_id)
    #         if pt.has_coordinates:
    #             data_dump_ids = DataDumpIds(slug, mode='has_coordinates', connection=connection)
    #             data_dump_ids.add(tweet_id)

    #     if use_pq and pt.should_be_annotated():
    #         # Add to Tweet ID queue for crowd labelling
    #         logger.info(f'Add tweet {tweet_id} to priority queue...')
    #         processed_tweet = pt.get_processed_tweet()
    #         tid = TweetIdQueue(stream_config['es_index_name'], priority_threshold=3, connection=connection)
    #         processed_tweet['text'] = pt.get_text(anonymize=True)
    #         tid.add_tweet(tweet_id, processed_tweet, priority=0)

    #     if stream_config['image_storage_mode'] != 'inactive':
    #         pm = ProcessMedia(tweet, slug, image_storage_mode=stream_config['image_storage_mode'])
    #         pm.process()

        # if send_to_es and \
        #         stream_config['storage_mode'] in \
        #         ['s3-es', 's3-es-no-retweets']:
        #     if tweet_matcher.is_retweet and \
        #             stream_config['storage_mode'] == 's3-es-no-retweets':
        #         # Do not store retweets on ES
        #         return
        #     # Send to ES
        #     processed_tweet = pt.get_processed_tweet()
        #     logger.debug(
        #         'Pushing processed with id %s to ES queue.', {tweet_id})
        #     es_tweet_obj = {'processed_tweet': processed_tweet, 'id': tweet_id}
        #     if len(stream_config['model_endpoints']) > 0:
        #         # Prepare for prediction
        #         es_tweet_obj['text_for_prediction'] = \
        #             {'text': pt.get_text(anonymize=True), 'id': tweet_id}
        #     es_queue.push(json.dumps(es_tweet_obj).encode(), slug)
