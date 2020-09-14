import logging
import time

import boto3

from .env import LEnv
from .env import ESEnv
from .aws_firehose import get_bucket_arn

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

iam = boto3.client(
    'iam',
    region_name=LEnv.REGION,
    aws_access_key_id=LEnv.ACCESS_KEY_ID,
    aws_secret_access_key=LEnv.SECRET_ACCESS_KEY)

aws_lambda = boto3.client(
    'lambda',
    region_name=LEnv.REGION,
    aws_access_key_id=LEnv.ACCESS_KEY_ID,
    aws_secret_access_key=LEnv.SECRET_ACCESS_KEY)

s3 = boto3.client(
    's3',
    region_name=LEnv.REGION,
    aws_access_key_id=LEnv.ACCESS_KEY_ID,
    aws_secret_access_key=LEnv.SECRET_ACCESS_KEY)


def get_function_name_arn():
    function_name = '{}-lambda-bucket-{}-es-{}'.format(
        LEnv.APP_NAME.lower(),
        LEnv.BUCKET_NAME, ESEnv.DOMAIN)
    function_arn = f'arn:aws:iam::{LEnv.ACCOUNT_NUM}:lambda/{function_name}'
    return function_name, function_arn


def get_layer_name_arn():
    layer_name = f'{LEnv.APP_NAME.lower()}-lambda-layer'
    layer_arn = f'arn:aws:lambda:{LEnv.REGION}:{LEnv.ACCOUNT_NUM}:' \
                f'layer:{layer_name}'
    return layer_name, layer_arn


def get_role_name_arn():
    role_name = 'service-role/{}LambdaBucket-{}'.format(
        LEnv.APP_NAME.capitalize(),
        LEnv.BUCKET_NAME)
    role_arn = f'arn:aws:iam::{LEnv.ACCOUNT_NUM}:role/{role_name}'
    return role_name, role_arn


def get_policy_name_arn():
    policy_name = '{}LambdaBucket-{}'.format(
        LEnv.APP_NAME.capitalize(),
        LEnv.BUCKET_NAME)
    policy_arn = f'arn:aws:iam::{LEnv.ACCOUNT_NUM}:policy/{policy_name}'
    return policy_name, policy_arn


def create_lambda_role():
    role_name, _ = get_role_name_arn()
    policy_name, policy_arn = get_policy_name_arn()

    with open(LEnv.ROLE_TRUST_RELATIONSHIP_PATH, 'r') as f:
        role_trust_relationship = f.read()
        role_trust_relationship = role_trust_relationship.replace(
            'ACCOUNT_NUM', LEnv.ACCOUNT_NUM)
        logger.debug(
            'Role trust relationship:\n\n%s\n',
            role_trust_relationship)

    try:
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=role_trust_relationship,
            Description=f'Role automatically created for Lambda '
                        f'by {LEnv.APP_NAME}.',
            # PermissionsBoundary='string',
            Tags=[
                {
                    'Key': 'project',
                    'Value': LEnv.APP_NAME
                },
            ]
        )

        logger.debug('Response:\n\n%s\n', response)
        logger.info(
            'Created role %s with ID %s for Lambda.',
            response['Role']['RoleName'], response['Role']['RoleId'])
    except iam.exceptions.EntityAlreadyExistsException:
        pass

    with open(LEnv.POLICY_PATH, 'r') as f:
        policy = f.read()
        policy = policy.replace('ACCOUNT_NUM', LEnv.ACCOUNT_NUM)
        policy = policy.replace('BUCKET_NAME', LEnv.BUCKET_NAME)
        policy = policy.replace('REGION', LEnv.REGION)
        policy = policy.replace('DOMAIN', ESEnv.DOMAIN)

    try:
        response = iam.create_policy(
            PolicyName=policy_name,
            PolicyDocument=policy,
            Description=f'Policy automatically created for Lambda '
                        f'by {LEnv.APP_NAME}.',
        )

        logger.debug('Response:\n\n%s\n', response)
        logger.info(
            'Created policy %s with ID %s for Lambda.',
            response['Policy']['PolicyName'], response['Policy']['PolicyId'])
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


def create_s3_to_es_lambda(
        push_func=False, push_layer=False, create_layer=False
):
    function_name, function_arn = get_function_name_arn()
    layer_name, layer_arn = get_layer_name_arn()

    if push_func:
        s3.upload_file(
            LEnv.PATH_TO_FUNC, LEnv.BUCKET_NAME, 'lambda/lambda.zip')
        logger.info('Function %s pushed to S3.', function_name)
    if push_layer:
        s3.upload_file(
            LEnv.PATH_TO_FUNC, LEnv.BUCKET_NAME, 'lambda/layer.zip')
        logger.info('Layer %s pushed to S3.', layer_name)

    if push_layer or create_layer:
        response = aws_lambda.publish_layer_version(
            LayerName=layer_name,
            Description='Layer created automatically for Lambda '
                        f'by {LEnv.APP_NAME}.',
            Content={
                'S3Bucket': LEnv.BUCKET_NAME,
                'S3Key': 'lambda/layer.zip'
            },
            CompatibleRuntimes=[
                'python3.7'
            ]
        )

        if 'CreatedDate' in response:
            logger.info('Layer %s created.', layer_name)

    # Create lambda role
    create_lambda_role()

    time.sleep(10)

    try:
        aws_lambda.get_function(
            FunctionName=function_name)
    except aws_lambda.exceptions.ResourceNotFoundException:
        try:
            response = aws_lambda.list_layer_versions(
                CompatibleRuntime='python3.7',
                LayerName=layer_name
            )

            versions = [
                version['Version'] for version in response['LayerVersions']]

            latest_version = max(versions)
        except aws_lambda.exceptions.ResourceNotFoundException:
            raise Exception(
                f'Layer {layer_name} does not exist. '
                "Use 'push_layer=True' or 'create_layer=True' "
                'if layer has already been pushed to S3.'
            )

        response = None
        count = 0
        while response is None:
            if count > 6:
                raise TimeoutError
            try:
                response = aws_lambda.create_function(
                    FunctionName=function_name,
                    Runtime='python3.7',
                    Role=get_role_name_arn()[1],
                    Handler=LEnv.HANDLER,
                    Code={
                        'S3Bucket': LEnv.BUCKET_NAME,
                        'S3Key': 'lambda/lambda.zip'
                    },
                    Description=LEnv.DESCRIPTION,
                    Timeout=LEnv.TIMEOUT,
                    MemorySize=LEnv.MEMORY_SIZE,
                    Publish=True,
                    Environment={
                        'Variables': {
                            'ES_HOST': ESEnv.HOST,
                            'ES_PORT': ESEnv.PORT,
                            'ES_INDEX_PREFIX': ESEnv.INDEX_PREFIX
                        }
                    },
                    Tags={
                        'Key': 'project',
                        'Value': LEnv.APP_NAME
                    },
                    Layers=[
                        layer_arn + f':{latest_version}',
                    ]
                )
            except aws_lambda.exceptions.InvalidParameterValueException as exc:
                logger.warning('%s: %s', type(exc).__name__, str(exc))
                count += 1
                time.sleep(60)

        # Add S3 event trigger to the lambda
        response = s3.put_bucket_notification_configuration(
            Bucket=get_bucket_arn(LEnv.BUCKET_NAME),
            NotificationConfiguration={
                'LambdaFunctionConfigurations': [{
                    'LambdaFunctionArn': function_arn,
                    'Events': ['s3:ObjectCreated:*']
                }]
            }
        )

        # Wait until lambda is active
        response = aws_lambda.get_function(FunctionName=function_name)
        status = response['Configuration']['State']
        start = time.time()
        while status != 'Active':
            if time.time() - start > 600:
                logger.warning(
                    'Waiting for more than 10 min. '
                    'Might be a problem with activation of lambda %s. '
                    'Please check the AWS console.', function_name)
                break
            response = aws_lambda.get_function(FunctionName=function_name)
            status = response['Configuration']['State']
            logger.info(
                'Waiting for lambda %s to become active.',
                function_name)
            time.sleep(30)

        if status == 'Active':
            logger.info(
                'Lambda %s is active.', function_name)
        else:
            logger.warning(
                'Waited too long for the activation of lambda %s.',
                function_name)
            raise TimeoutError(
                'Waited too long for the activation of '
                f'lambda {function_name}.'
            )
