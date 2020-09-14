import logging
import time

import boto3

from .env import KFEnv

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

iam = boto3.client(
    'iam',
    region_name=KFEnv.REGION,
    aws_access_key_id=KFEnv.ACCESS_KEY_ID,
    aws_secret_access_key=KFEnv.SECRET_ACCESS_KEY)

firehose = boto3.client(
    'firehose',
    region_name=KFEnv.REGION,
    aws_access_key_id=KFEnv.ACCESS_KEY_ID,
    aws_secret_access_key=KFEnv.SECRET_ACCESS_KEY)


def get_bucket_arn(bucket_name):
    return f'arn:aws:s3:::{bucket_name}'


def get_role_name_arn(slug):
    role_name = '{}{}FirehoseBucket-{}'.format(
        KFEnv.APP_NAME.capitalize(), slug.capitalize(),
        KFEnv.BUCKET_NAME)
    role_arn = f'arn:aws:iam::{KFEnv.ACCOUNT_NUM}:role/{role_name}'
    return role_name, role_arn


def get_policy_name_arn(slug):
    policy_name = '{}{}FirehoseBucket-{}'.format(
        KFEnv.APP_NAME.capitalize(), slug.capitalize(),
        KFEnv.BUCKET_NAME)
    policy_arn = f'arn:aws:iam::{KFEnv.ACCOUNT_NUM}:policy/{policy_name}'
    return policy_name, policy_arn


def get_stream_name_arn(slug):
    stream_name = f'{KFEnv.APP_NAME}-{slug}'
    stream_arn = \
        f'arn:aws:iam::{KFEnv.ACCOUNT_NUM}:deliverystream/{stream_name}'
    return stream_name, stream_arn


def create_firehose_role(slug):
    role_name, _ = get_role_name_arn(slug)
    policy_name, policy_arn = get_policy_name_arn(slug)

    with open(KFEnv.ROLE_TRUST_RELATIONSHIP_PATH, 'r') as f:
        role_trust_relationship = f.read()
        role_trust_relationship = role_trust_relationship.replace(
            'ACCOUNT_NUM', KFEnv.ACCOUNT_NUM)
        logger.debug(
            'Role trust relationship:\n\n%s\n',
            role_trust_relationship)

    try:
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=role_trust_relationship,
            Description=f'Role automatically created for project {slug} '
                        f'by {KFEnv.APP_NAME}.',
            # PermissionsBoundary='string',
            Tags=[
                {
                    'Key': 'project',
                    'Value': KFEnv.APP_NAME
                },
            ]
        )

        logger.debug('Response:\n\n%s\n', response)
        logger.info(
            'Created role %s with ID %s for project %s.',
            response['Role']['RoleName'], response['Role']['RoleId'], slug)
    except iam.exceptions.EntityAlreadyExistsException:
        pass

    with open(KFEnv.POLICY_PATH, 'r') as f:
        policy = f.read()
        policy = policy.replace('ACCOUNT_NUM', KFEnv.ACCOUNT_NUM)
        policy = policy.replace('BUCKET_NAME', KFEnv.BUCKET_NAME)
        policy = policy.replace('REGION', KFEnv.REGION)

    try:
        response = iam.create_policy(
            PolicyName=policy_name,
            PolicyDocument=policy,
            Description=f'Policy automatically created for project {slug} '
                        f'by {KFEnv.APP_NAME}.',
        )

        logger.debug('Response:\n\n%s\n', response)
        logger.info(
            'Created policy %s with ID %s for project %s.',
            response['Policy']['PolicyName'], response['Policy']['PolicyId'],
            slug)
    except iam.exceptions.EntityAlreadyExistsException:
        pass

    response = iam.attach_role_policy(
        PolicyArn=policy_arn,
        RoleName=role_name
    )

    logger.debug('Response:\n\n%s\n', response)
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        logger.info(
            'Attached policy %s to the role %s.',
            policy_name, role_name)

    return


def create_delivery_stream(slug):
    create_firehose_role(slug)

    _, role_arn = get_role_name_arn(slug)
    stream_name, _ = get_stream_name_arn(slug)

    time.sleep(10)

    stream_name = f'{KFEnv.APP_NAME}-{slug}'

    try:
        response = firehose.create_delivery_stream(
            DeliveryStreamName=stream_name,
            DeliveryStreamType='DirectPut',
            S3DestinationConfiguration={
                'RoleARN': role_arn,
                'BucketARN': get_bucket_arn(KFEnv.BUCKET_NAME),
                'Prefix': f'{KFEnv.BUCKET_PREFIX}{slug}/',
                'ErrorOutputPrefix': f'{slug}/failed/',
                'BufferingHints': {
                    'SizeInMBs': KFEnv.BUFFER_SIZE,
                    'IntervalInSeconds': KFEnv.BUFFER_INTERVAL
                },
                'CompressionFormat': 'GZIP',
            },
            Tags=[
                {
                    'Key': 'project',
                    'Value': KFEnv.APP_NAME
                },
            ]
        )

        logger.info(
            'Successfully created delivery stream %s for project %s.',
            stream_name, slug)
    except firehose.exceptions.ResourceInUseException:
        logger.info(
            'Delivery stream %s already exists and in use.',
            stream_name)

    response = firehose.describe_delivery_stream(
        DeliveryStreamName=stream_name)
    status = response[
        'DeliveryStreamDescription']['DeliveryStreamStatus']
    start = time.time()
    while status != 'ACTIVE':
        if time.time() - start > 600:
            logger.warning(
                'Waiting for more than 10 min. '
                'Might be a problem with activation of delivery stream %s. '
                'Please check the AWS console.', stream_name)
            break
        response = firehose.describe_delivery_stream(
            DeliveryStreamName=stream_name)
        status = response[
            'DeliveryStreamDescription']['DeliveryStreamStatus']
        logger.info(
            'Waiting for delivery stream %s to become active.', stream_name)
        time.sleep(30)

    if status == 'ACTIVE':
        logger.info(
            'Delivery stream %s is active.', stream_name)
    else:
        logger.warning(
            'Waited too long for the activation of delivery stream %s.',
            stream_name)
        raise TimeoutError(
            'Waited too long for the activation of '
            f'delivery stream {stream_name}.'
        )

    return
