import time
import logging

from awstools.session import s3, ecs
from awstools.env import ECSEnv
from awstools.config import ConfigManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def check_desired_count(cluster, service, count, time_step=30, time_limit=300):
    updated = False
    time_slept = 0
    while not updated:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_services
        response = ecs.describe_services(
            cluster=cluster,
            services=[service]
        )

        for service in response['services']:
            if service['serviceName'] == service:
                if time_slept < time_limit:
                    if service['runningCount'] != count:
                        time_slept += time_step
                        time.sleep(time_step)
                    else:
                        updated = True
                else:
                    raise Exception('Waiting more than %d s.', time_limit)
            else:
                raise Exception('No inquired service name in the response.')

    logger.info(
        'ECS service %s on cluster %s has been updated, desired count = %d',
        service, cluster, count)


def handler(event, context):
    response = s3.list_object_versions(
        Prefix=ECSEnv.STREAM_CONFIG_S3_KEY, Bucket=ECSEnv.BUCKET_NAME)

    # 1. Order by last modified
    # 2. Take two latest versions
    # 3. Create config_manager objects off of them
    # 4. Compare
    # 5. Take action based on changes
    #     - Stop streaming
    #     - Restart streaming

    versions = sorted(
        response['Versions'], key=lambda k: k['LastModified'], reverse=True)
    for version in versions:
        print(version)
    version_ids = [response['VersionId'] for response in versions]

    # Get 2 last versions
    config_manager_old = ConfigManager(version_id=version_ids[0])
    config_manager_new = ConfigManager(version_id=version_ids[1])

    older_slugs = {conf.slug for conf in config_manager_old.config}
    newer_slugs = {conf.slug for conf in config_manager_new.config}

    new_slugs = newer_slugs.difference(older_slugs)
    removed_slugs = older_slugs.difference(newer_slugs)
    same_slugs = older_slugs.intersection(newer_slugs)

    print(new_slugs)
    print(removed_slugs)
    print(same_slugs)

    if config_manager_old.write() != config_manager_new.write():
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

        check_desired_count(ECSEnv.CLUSTER, ECSEnv.SERVICE, 1)
