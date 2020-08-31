import logging
import time

import boto3

from .env import KFEnv

logger = logging.getLogger(__name__)

iam = boto3.client('iam')
firehose = boto3.client('firehose')


def create_firehose_role(slug):
    role_name = '{}{}KinesisFirehoseRole'.format(
        KFEnv.APP_NAME.capitalize(), slug.capitalize())

    # If the role does not yet exist, create one
    if iam.Role(role_name).create_date is None:
        with open(KFEnv.ROLE_TRUST_RELATIONSHIP_PATH, 'r') as f:
            role_trust_relationship = f.read()
            role_trust_relationship = role_trust_relationship.replace(
                'ACCOUNT_NUM', KFEnv.ACCOUNT_NUM)

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

        logger.info(
            'Created role %s with ID %s for project %s.',
            response['RoleName'], response['RoleId'], slug)

    with open(KFEnv.POLICY_PATH, 'r') as f:
        policy = f.read()
        policy = policy.replace('ACCOUNT_NUM', KFEnv.ACCOUNT_NUM)
        policy = policy.replace('BUCKET_NAME', KFEnv.BUCKET_NAME)
        policy = policy.replace('REGION', KFEnv.REGION)

    policy_name = '{}{}KinesisFirehosePolicy'.format(
        KFEnv.APP_NAME.capitalize(), slug.capitalize())

    response = iam.create_policy(
        PolicyName=policy_name,
        PolicyDocument=policy,
        Description=f'Policy automatically created for project {slug} '
                    f'by {KFEnv.APP_NAME}.',
    )

    logger.info(
        'Created policy %s with ID %s for project %s.',
        response['PolicyName'], response['PolicyId'], slug)
    logger.debug('Response:\n\n%s\n', response)

    response = iam.attach_role_policy(
        PolicyArn=f'arn:aws:iam::aws:policy/{policy_name}',
        RoleName=role_name
    )

    logger.info(
        'Attached policy %s to the role %s.',
        response['PolicyName'], response['RoleName'])
    logger.debug('Response:\n\n%s\n', response)

    return role_name


def create_delivery_stream(slug):
    role_name = create_firehose_role(slug)

    stream_name = f'{KFEnv.APP_NAME}-{slug}'

    response = firehose.create_delivery_stream(
        DeliveryStreamName=stream_name,
        DeliveryStreamType='DirectPut',
        S3DestinationConfiguration={
            'RoleARN': f'arn:aws:iam::aws:policy/{role_name}',
            'BucketARN': KFEnv.BUCKET_ARN,
            'Prefix': f'{slug}/',
            'ErrorOutputPrefix': f'{slug}/failed/',
            'BufferingHints': {
                'SizeInMBs': 50,
                'IntervalInSeconds': 300
            },
            'CompressionFormat': 'GZIP',
            # 'CloudWatchLoggingOptions': {
            #     'Enabled': True|False,
            #     'LogGroupName': 'string',
            #     'LogStreamName': 'string'
            # }
        },
        Tags=[
            {
                'Key': 'project',
                'Value': KFEnv.APP_NAME
            },
        ]
    )

    http_status_code = response['ResponseMetadata']['HTTPStatusCode']
    if http_status_code != 200:
        logger.error(
            'Unable to create delivery stream %s. HTTP code %s.',
            stream_name, http_status_code)
        raise Exception(
            'Unable to create delivery stream {}. HTTP code {}.'.format(
                stream_name, http_status_code))

    status = None
    start = time.time()
    while status != 'ACTIVE':
        if time.time() - start > 600:
            logger.warning(
                'Waiting for more than 10 min. '
                'Might be a problem with activation of %s. '
                'Please check the AWS console.', stream_name)
            break
        time.sleep(60)
        response = firehose.describe_delivery_stream(
            DeliveryStreamName=stream_name)
        status = response[
            'DeliveryStreamDescription']['DeliveryStreamStatus']
        logger.info(
            'Waiting for the new %s stream to become active.', stream_name)

    if status == 'ACTIVE':
        logger.info(
            'Successfully created delivery stream %s for project %s.',
            response['DeliveryStreamARN'], slug)

    return response['DeliveryStreamDescription']['DeliveryStreamARN']
