from datetime import datetime
from io import StringIO
import logging

import numpy as np
import pandas as pd

from awstools.session import s3
from awstools.env import AWSEnv
from awstools.s3 import get_s3_object

FUNCTION_NAME = f'{AWSEnv.APP_NAME}-subsample-annotations-{AWSEnv.ENV}'
MIN_TWEET_COUNT = 10

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

get_worker_tweets = lambda df, worker_id: df[df.worker_id == worker_id].tweet_id.unique()


def get_tweet_counts(unique_workers, df_sampled):
    tweet_counts = {}
    for worker_id in unique_workers:
        count = len(get_worker_tweets(df_sampled, worker_id))
        tweet_counts[worker_id] = count
    return tweet_counts


def sample_tweets_from_each_worker(df, n_samples=1, min_tweet_count=MIN_TWEET_COUNT):
    # Sample tweets from each worker
    df = df.convert_dtypes()
    df_dtypes = {k: pd.Series(dtype=v) for k, v in dict(df.dtypes).items()}

    # Exclude workers who have less than MIN_TWEET_COUNT tweets labeled
    tweet_counts = get_tweet_counts(df.worker_id.unique(), df)
    unique_workers = np.sort([k for k, v in tweet_counts.items() if v >= min_tweet_count])
    df_sampled = pd.DataFrame(df_dtypes)

    while not np.array_equal(np.sort(df_sampled.worker_id.unique()), unique_workers):
        sampled_workers = np.intersect1d(
            unique_workers,
            df_sampled.worker_id.unique()
        )
        if len(sampled_workers) > 0:
            unsampled_worker_ids = np.delete(
                unique_workers,
                np.where([
                    unique_worker in sampled_workers
                    for unique_worker in unique_workers
                ]))
        else:
            unsampled_worker_ids = unique_workers
        print('sample_tweets_from_each_worker: %s', unsampled_worker_ids)
        worker_id = np.random.choice(unsampled_worker_ids, 1)[0]

        df_worker = df[df.worker_id == worker_id]
        sampled_worker_tweets = df_worker.tweet_id.sample(n_samples)
        worker_tweets_in_df = [tweet_id in sampled_worker_tweets.tolist() for tweet_id in df.tweet_id]
        sampled_tweets = df[worker_tweets_in_df]
        df_sampled = pd.concat([df_sampled, sampled_tweets], ignore_index=True)
        
    return df_sampled


def sample_more_tweets_for_min_workers(df, df_sampled, n_samples=1, min_tweet_count=10):
    # Sample more tweets from workers with minimal number of tweets
    # Exclude workers who have less than MIN_TWEET_COUNT tweets labeled
    tweet_counts = get_tweet_counts(df.worker_id.unique(), df)
    unique_workers = np.sort([k for k, v in tweet_counts.items() if v >= min_tweet_count])
    
    while min(get_tweet_counts(unique_workers, df_sampled).values()) < min_tweet_count:
        min_count = min(tweet_counts.values())
        workers_with_min_count = [k for k, v in tweet_counts.items() if v == min_count]
        worker_id = np.random.choice(workers_with_min_count, 1)[0]
        worker_tweets = get_worker_tweets(df, worker_id)

        unsampled_worker_tweets = np.delete(
            worker_tweets,
            np.where([
                tweet_id in df_sampled.tweet_id.unique().tolist()
                for tweet_id in worker_tweets.tolist()
            ]))
        if len(unsampled_worker_tweets) == 0:
            return df_sampled

        print('sample_more_tweets_for_min_workers 2: %s', unsampled_worker_tweets)
        sampled_worker_tweets = np.random.choice(unsampled_worker_tweets, n_samples, replace=False)
        worker_tweets_in_df = [tweet_id in sampled_worker_tweets.tolist() for tweet_id in df.tweet_id]
        sampled_tweets = df[worker_tweets_in_df]
        df_sampled = pd.concat([df_sampled, sampled_tweets], ignore_index=True)

        tweet_counts = get_tweet_counts(unique_workers, df_sampled)
        
    return df_sampled


def sample_tweets_for_all_workers(df, n_samples=1, min_tweet_count=MIN_TWEET_COUNT):
    df_sampled = sample_tweets_from_each_worker(df, n_samples)
    df_sampled = sample_more_tweets_for_min_workers(
        df, df_sampled, n_samples, min_tweet_count)
    return df_sampled


def handler(event, context):
    logger.debug(event)

    key = event['Records'][-1]['s3']['object']['key']
    logger.debug(key)
    if 'results' not in key:
        logger.info("'%s' is not a results object.", key)
        return
    # Avoid vicious cycle
    elif 'evaluate' in key:
        logger.warning("'%s' is a subsample already.", key)
        return
    folder = key.split('/')[:-1]
    object_name = key.split('/')[-1]
    date_now = datetime.now().strftime('%Y%m%d')
    output_key = '/'.join([*folder, '-'.join(['evaluate', date_now, object_name])])
    output_key_ids = '/'.join([*folder, '-'.join(['evaluate_ids', date_now, object_name])])

    logger.debug(output_key)

    df = pd.read_csv(StringIO(get_s3_object(AWSEnv.BUCKET_NAME, key)))
    logger.info('Unique tweets in the original sample: %s', len(df.tweet_id.unique()))

    df_sampled = sample_tweets_for_all_workers(df, n_samples=1, min_tweet_count=MIN_TWEET_COUNT)
    logger.info('Unique tweets in the subsample: %s', len(df_sampled.tweet_id.unique()))
    csv_buffer = StringIO()
    df_sampled.to_csv(csv_buffer)
    s3.put_object(Body=csv_buffer.getvalue(), Bucket=AWSEnv.BUCKET_NAME, Key=output_key)

    csv_buffer = StringIO()
    df_sampled_ids = df_sampled[['tweet_id', 'text']].drop_duplicates()
    df_sampled_ids.to_csv(csv_buffer, header=False, index=False)
    s3.put_object(Body=csv_buffer.getvalue(), Bucket=AWSEnv.BUCKET_NAME, Key=output_key_ids)
