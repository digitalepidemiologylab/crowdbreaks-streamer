import time
import json
import logging

from awstools.session import s3, ecs
from awstools.env import ECSEnv, AWSEnv
from awstools.config import ConfigManager, StorageMode
from awstools.s3 import get_s3_object
from awstools.llambda import get_function_name_arn

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def check_if_currently_active(cluster_name, service_name):
    response = ecs.describe_services(
        cluster=cluster_name,
        services=[service_name]
    )
    active = True
    name_in_response = False
    for service in response['services']:
        if service['serviceName'] == service_name:
            name_in_response = True
            service_count = service['runningCount']
            service_count += service['pendingCount']
            if service_count == 0:
                active = False
    if name_in_response is False:
        raise Exception('No inquired service name '
                        f'({service_name}) in the response.')
    if service_count > 1:
        raise logger.warning('Extra instances were found. Check the ECS.')

    return active


def wait_for_desired_count(
    cluster_name, service_name, count, time_step=30, time_limit=160
):
    updated = False
    time_slept = 0
    logger.info('%s %s', cluster_name, service_name)
    while not updated:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_services
        response = ecs.describe_services(
            cluster=cluster_name,
            services=[service_name]
        )
        name_in_response = False
        for service in response['services']:
            if service['serviceName'] == service_name:
                name_in_response = True
                service_count = service['runningCount']
                service_count += service['pendingCount']
                if time_slept < time_limit:
                    if service_count != count:
                        logger.info(
                            'Running/pending count: %d, desired: %d.',
                            service_count, count)
                        time_slept += time_step
                        time.sleep(time_step)
                    else:
                        updated = True
                else:
                    raise Exception('Waiting more than %d s.', time_limit)
        if name_in_response is False:
            raise Exception('No inquired service name in the response.')

    logger.info(
        'ECS service %s on cluster %s has been updated, desired count = %d.',
        service_name, cluster_name, service_count)


def start_streamer():
    # To start streaming, set the desired count to 1 and wait
    # until a task is running
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.update_service
    ecs.update_service(
        cluster=ECSEnv.CLUSTER,
        service=ECSEnv.SERVICE,
        desiredCount=1)
    wait_for_desired_count(ECSEnv.CLUSTER, ECSEnv.SERVICE, 1)


def stop_streamer():
    # To stop the streamer, set the desired count to 0 and wait
    # until tasks are stopped
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.update_service
    ecs.update_service(
        cluster=ECSEnv.CLUSTER,
        service=ECSEnv.SERVICE,
        desiredCount=0)
    wait_for_desired_count(ECSEnv.CLUSTER, ECSEnv.SERVICE, 0)


def handle_stream_config():
    state = json.loads(get_s3_object(
        ECSEnv.BUCKET_NAME, ECSEnv.STREAM_STATE_S3_KEY))
    state = state['state']
    response = s3.list_object_versions(
        Prefix=ECSEnv.STREAM_CONFIG_S3_KEY, Bucket=ECSEnv.BUCKET_NAME)

    # Order versions by last modified
    versions = sorted(
        response['Versions'], key=lambda k: k['LastModified'], reverse=True)
    version_ids = [response['VersionId'] for response in versions]

    # Take 2 last versions
    config_manager_old = ConfigManager(version_id=version_ids[1])
    config_manager_new = ConfigManager(version_id=version_ids[0])

    # Check if the streamer is currently active
    # streamer_currently_active = check_if_currently_active(
    #     ECSEnv.CLUSTER, ECSEnv.SERVICE)

    # Restart streaming if configs are different
    if config_manager_old.write() != config_manager_new.write():
        if state is True:
            logger.info('The config changed. Going to restart the streamer.')
            stop_streamer()
            start_streamer()
        elif state is False:
            logger.info('The config changed, the current state is False. '
                        'Going to stop the streamer.')
            stop_streamer()

        # Bucket Lambda event notifications
        notif_config = s3.get_bucket_notification_configuration(
            Bucket=ECSEnv.BUCKET_NAME
        )
        rules = []
        for conf in config_manager_new.config:
            if conf.storage_mode not in [StorageMode.S3,
                                         StorageMode.S3_NO_RETWEETS]:
                rules.append({
                    'Name': 'prefix',
                    'Value': AWSEnv.STORAGE_BUCKET_PREFIX + conf.slug})

        notif_config['LambdaFunctionConfigurations'] = [{
            'Id': 'streamer',
            'LambdaFunctionArn':
                get_function_name_arn(AWSEnv.LAMBDA_S3_ES_NAME),
            'Events': ['s3:ObjectCreated:*'],
            'Filter': {'Key': {'FilterRules': rules}}
        }]

        _ = s3.put_bucket_notification_configuration(
            Bucket=ECSEnv.BUCKET_NAME,
            NotificationConfiguration=notif_config
        )


def handle_stream_state():
    state = json.loads(get_s3_object(
        ECSEnv.BUCKET_NAME, ECSEnv.STREAM_STATE_S3_KEY))
    if state['from'] == 'rails':
        return
    state = state['state']

    # streamer_currently_active = check_if_currently_active(
    #     ECSEnv.CLUSTER, ECSEnv.SERVICE)

    # - active => start streamer
    # - inactive => stop streamer

    if state is True:
        logger.info('The new state is True. Starting the streamer.')
        start_streamer()
    elif state is False:
        logger.info('The new state is False. Stopping the streamer.')
        stop_streamer()


def handler(event, context):
    logger.debug(event)
    key = event['Records'][-1]['s3']['object']['key']
    if key == ECSEnv.STREAM_CONFIG_S3_KEY:
        handle_stream_config()
    elif key == ECSEnv.STREAM_STATE_S3_KEY:
        handle_stream_state()
