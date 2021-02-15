import time
import json
import logging

from awstools.session import s3, ecs
from awstools.env import ECSEnv
from awstools.config import ConfigManager
from awstools.s3 import get_s3_object

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def check_desired_count(cluster_name, service_name, count, status='running', time_step=30, time_limit=160):
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

    # 1. Order by last modified
    # 2. Take two latest versions
    # 3. Create config_manager objects off of them
    # 4. Compare
    # 5. Restart streaming if configs are different

    versions = sorted(
        response['Versions'], key=lambda k: k['LastModified'], reverse=True)
    version_ids = [response['VersionId'] for response in versions]

    # Get 2 last versions
    config_manager_old = ConfigManager(version_id=version_ids[1])
    config_manager_new = ConfigManager(version_id=version_ids[0])

    # older_slugs = {conf.slug for conf in config_manager_old.config}
    # newer_slugs = {conf.slug for conf in config_manager_new.config}

    # new_slugs = newer_slugs.difference(older_slugs)
    # removed_slugs = older_slugs.difference(newer_slugs)
    # same_slugs = older_slugs.intersection(newer_slugs)

    # print(new_slugs)
    # print(removed_slugs)
    # print(same_slugs)

    if config_manager_old.write() != config_manager_new.write() and \
            state is True:
        logger.info('Config changed. Going to restart the streamer.')

        # To stop streaming, set desired count to 0 and wait until tasks are stopped
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.update_service
        response = ecs.update_service(
            cluster=ECSEnv.CLUSTER,
            service=ECSEnv.SERVICE,
            desiredCount=0)

        check_desired_count(ECSEnv.CLUSTER, ECSEnv.SERVICE, 0)

        # To restart, set desired count to zero and wait until a task is running
        response = ecs.update_service(
            cluster=ECSEnv.CLUSTER,
            service=ECSEnv.SERVICE,
            desiredCount=1)

        check_desired_count(
            ECSEnv.CLUSTER, ECSEnv.SERVICE, 1, status='pending')


def handle_stream_state():
    response = s3.list_object_versions(
        Prefix=ECSEnv.STREAM_STATE_S3_KEY, Bucket=ECSEnv.BUCKET_NAME)

    # 1. Order by last modified
    # 2. Take two latest versions
    # 3. Create config_manager objects off of them
    # 4. Compare
    #     - inactive -> active => start streamer
    #     - active -> inactive => stop streamer
    #     - active -> active, inactive -> inactive => do nothing

    versions = sorted(
        response['Versions'], key=lambda k: k['LastModified'], reverse=True)
    version_ids = [response['VersionId'] for response in versions]

    state_old = json.loads(get_s3_object(
        ECSEnv.BUCKET_NAME, ECSEnv.STREAM_STATE_S3_KEY,
        version_id=version_ids[1]))
    state_new = json.loads(get_s3_object(
        ECSEnv.BUCKET_NAME, ECSEnv.STREAM_STATE_S3_KEY,
        version_id=version_ids[0]))

    if state_old is False and state_new is True:
        logger.info(
            'Streamer state changed to active. Going to start the streamer.')

        # To start streaming, set desired count to 1 and wait until tasks are pending
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.update_service
        response = ecs.update_service(
            cluster=ECSEnv.CLUSTER,
            service=ECSEnv.SERVICE,
            desiredCount=1)

        check_desired_count(
            ECSEnv.CLUSTER, ECSEnv.SERVICE, 1, status='pending')

    elif state_old is True and state_new is False:
        logger.info(
            'Streamer state changed to inactive. Going to stop the streamer.')

        # To stop streaming, set desired count to 0 and wait until tasks are stopped
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.update_service
        response = ecs.update_service(
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
