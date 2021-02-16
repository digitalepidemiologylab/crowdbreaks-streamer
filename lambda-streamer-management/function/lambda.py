import time
import json
import logging

from awstools.session import s3, ecs
from awstools.env import ECSEnv
from awstools.config import ConfigManager
from awstools.s3 import get_s3_object

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def check_desired_count(
    cluster_name, service_name, count, status='running',
    time_step=30, time_limit=160
):
    assert status in ['running', 'pending']
    updated = False
    time_slept = 0
    logger.info('%s %s', cluster_name, service_name)
    while not updated:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_services
        response = ecs.describe_services(
            cluster=cluster_name,
            services=[service_name]
        )

        for service in response['services']:
            if service['serviceName'] == service_name:
                service_count = service[f'{status}Count']
                if time_slept < time_limit:
                    if service_count != count:
                        logger.info(
                            '%s count: %d, desired: %d.',
                            status.capitalize(),
                            service_count, count)
                        time_slept += time_step
                        time.sleep(time_step)
                    else:
                        updated = True
                else:
                    raise Exception('Waiting more than %d s.', time_limit)
            else:
                raise Exception('No inquired service name in the response.')

    logger.info(
        'ECS service %s on cluster %s has been updated, desired count = %d.',
        service_name, cluster_name, service_count)


def handle_stream_config():
    state = json.loads(get_s3_object(
        ECSEnv.BUCKET_NAME, ECSEnv.STREAM_STATE_S3_KEY))
    response = s3.list_object_versions(
        Prefix=ECSEnv.STREAM_CONFIG_S3_KEY, Bucket=ECSEnv.BUCKET_NAME)

    # Order versions by last modified
    versions = sorted(
        response['Versions'], key=lambda k: k['LastModified'], reverse=True)
    version_ids = [response['VersionId'] for response in versions]

    # Take 2 last versions
    config_manager_old = ConfigManager(version_id=version_ids[1])
    config_manager_new = ConfigManager(version_id=version_ids[0])

    # Restart streaming if configs are different
    if config_manager_old.write() != config_manager_new.write() and \
            state is True:
        logger.info('Config changed. Going to restart the streamer.')

        # To stop streaming, set desired count to 0 and wait
        # until tasks are stopped
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.update_service
        response = ecs.update_service(
            cluster=ECSEnv.CLUSTER,
            service=ECSEnv.SERVICE,
            desiredCount=0)

        check_desired_count(ECSEnv.CLUSTER, ECSEnv.SERVICE, 0)

        # To restart, set desired count to zero and wait
        # until a task is running
        response = ecs.update_service(
            cluster=ECSEnv.CLUSTER,
            service=ECSEnv.SERVICE,
            desiredCount=1)

        check_desired_count(
            ECSEnv.CLUSTER, ECSEnv.SERVICE, 1, status='pending')


def handle_stream_state():
    state = json.loads(get_s3_object(
        ECSEnv.BUCKET_NAME, ECSEnv.STREAM_STATE_S3_KEY))

    # - active => start streamer
    # - inactive => stop streamer

    state = json.loads(get_s3_object(
        ECSEnv.BUCKET_NAME, ECSEnv.STREAM_STATE_S3_KEY))

    if state is True:
        logger.info('Streamer state is currently active.')

        # To start streaming, set desired count to 1 and wait
        # until tasks are pending
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.update_service
        _ = ecs.update_service(
            cluster=ECSEnv.CLUSTER,
            service=ECSEnv.SERVICE,
            desiredCount=1)

        check_desired_count(
            ECSEnv.CLUSTER, ECSEnv.SERVICE, 1, status='pending')

    elif state is False:
        logger.info('Streamer state is currently inactive.')

        # To stop streaming, set desired count to 0 and wait
        # until tasks are stopped
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.update_service
        _ = ecs.update_service(
            cluster=ECSEnv.CLUSTER,
            service=ECSEnv.SERVICE,
            desiredCount=0)

        check_desired_count(ECSEnv.CLUSTER, ECSEnv.SERVICE, 0)


def handler(event, context):
    logger.debug(event)
    key = event['Records'][-1]['s3']['object']['key']
    if key == ECSEnv.STREAM_CONFIG_S3_KEY:
        handle_stream_config()
    elif key == ECSEnv.STREAM_STATE_S3_KEY:
        handle_stream_state()
