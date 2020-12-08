import logging
import time
import hashlib
from base64 import b64encode

import shutil
import subprocess
import sys
import os

import boto3

from .env import KFEnv, LEnv, ESEnv
from .firehose import get_bucket_arn

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


def zip_lambda_func():
    shutil.make_archive(
        LEnv.PATH_TO_FUNC, LEnv.EXTENSION, LEnv.PATH_TO_FUNC_DIR)


def zip_lambda_layer():
    # Install requirements.txt to python
    # https://stackoverflow.com/a/50255019/4949133
    subprocess.check_call([
        sys.executable, '-m',
        'pip', 'install',
        '-r', os.path.join(LEnv.PATH_TO_LAYER_DIR, 'requirements.txt'),
        '-t', os.path.join(LEnv.PATH_TO_LAYER_DIR, 'python')])
    # https://stackoverflow.com/a/25650295/4949133
    # https://docs.python.org/3/library/shutil.html#archiving-example-with-base-dir
    shutil.make_archive(
        LEnv.PATH_TO_LAYER, LEnv.EXTENSION,
        root_dir=LEnv.PATH_TO_LAYER_DIR,
        base_dir='python')


def get_function_name_arn():
    function_name = '{}-lambda-bucket-{}-es-{}'.format(
        LEnv.APP_NAME.lower(),
        LEnv.BUCKET_NAME, ESEnv.DOMAIN)
    function_arn = f'arn:aws:lambda:{LEnv.REGION}:{LEnv.ACCOUNT_NUM}:' \
                   f'function:{function_name}'
    return function_name, function_arn


def get_layer_name_arn():
    layer_name = f'{LEnv.APP_NAME.lower()}-lambda-layer'
    layer_arn = f'arn:aws:lambda:{LEnv.REGION}:{LEnv.ACCOUNT_NUM}:' \
                f'layer:{layer_name}'
    return layer_name, layer_arn


def get_role_name_arn():
    role_name = '{}LambdaBucket-{}'.format(
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
    function_name, _ = get_function_name_arn()

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

        # response = iam.create_service_linked_role(
        #     AWSServiceName='lambda.amazonaws.com',
        #     Description=f'Role automatically created for Lambda '
        #                 f'by {LEnv.APP_NAME}.'
        # )

        # role_name = response['Role']['RoleName']
        # role_arn = response['Role']['Arn']

        logger.debug('Response:\n\n%s\n', response)
        logger.info(
            'Created role %s with ID %s for Lambda.',
            response['Role']['RoleName'], response['Role']['RoleId'])

        # response = iam.tag_role(
        #     RoleName=role_name,
        #     Tags=[
        #         {
        #             'Key': 'project',
        #             'Value': LEnv.APP_NAME
        #         },
        #     ]
        # )
    except iam.exceptions.EntityAlreadyExistsException:
        pass

    with open(LEnv.POLICY_PATH, 'r') as f:
        policy = f.read()
        policy = policy.replace('ACCOUNT_NUM', LEnv.ACCOUNT_NUM)
        policy = policy.replace('BUCKET_NAME', LEnv.BUCKET_NAME)
        policy = policy.replace('REGION', LEnv.REGION)
        policy = policy.replace('DOMAIN', ESEnv.DOMAIN)
        policy = policy.replace('FUNCTION_NAME', function_name)
        policy = policy.replace('MODEL_NAME', LEnv.APP_NAME + '-*')

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


def check_s3_diff(bucket, key, local_path):
    s3_obj = None
    try:
        response = s3.get_object(
            Bucket=bucket,
            Key=key
        )
        s3_obj = response['Body'].read()
    except s3.exceptions.NoSuchKey:
        pass

    # print(type(s3_obj), s3_obj, sys.getsizeof(s3_obj))
    s3_obj_hash = hashlib.sha256(s3_obj).digest()

    with open(local_path, 'rb') as f:
        local_obj_hash = hashlib.sha256(f.read()).digest()

    return s3_obj_hash == local_obj_hash, local_obj_hash


def create_lambda_layer(push_layer=False, create_layer=False):
    layer_name, _ = get_layer_name_arn()
    layer_key = LEnv.PATH_TO_LAYER + '.' + LEnv.EXTENSION

    if push_layer:
        s3_diff, _ = check_s3_diff(
            LEnv.BUCKET_NAME, layer_key, layer_key)
        if not s3_diff:
            s3.upload_file(
                layer_key, LEnv.BUCKET_NAME, layer_key)
            logger.info('Layer %s pushed to S3.', layer_name)
        else:
            logger.info(
                'Layer %s not pushed to S3: '
                'local zip is the same as on S3.',
                layer_name)

        if (push_layer and not s3_diff) or create_layer:
            response = aws_lambda.publish_layer_version(
                LayerName=layer_name,
                Description='Layer created automatically for Lambda '
                            f'by {LEnv.APP_NAME}.',
                Content={
                    'S3Bucket': LEnv.BUCKET_NAME,
                    'S3Key': layer_key
                },
                CompatibleRuntimes=[
                    'python3.8'
                ]
            )

            if 'CreatedDate' in response:
                logger.info('Layer %s created.', layer_name)


def create_s3_to_es_lambda(push_func=False):
    _, role_arn = get_role_name_arn()
    function_name, function_arn = get_function_name_arn()
    layer_name, layer_arn = get_layer_name_arn()
    lambda_key = LEnv.PATH_TO_FUNC + '.' + LEnv.EXTENSION

    # If push_func is True and the code has been changed
    if push_func:
        hash_match, local_lambda_hash = check_s3_diff(
            LEnv.BUCKET_NAME, lambda_key, lambda_key)
        if not hash_match:
            s3.upload_file(
                lambda_key, LEnv.BUCKET_NAME, lambda_key)
            logger.info('Function %s pushed to S3.', function_name)
        else:
            logger.info(
                'Function %s not pushed to S3: '
                'local zip is the same as on S3.',
                function_name)

    # Create lambda role
    create_lambda_role()

    time.sleep(10)

    try:
        response = aws_lambda.list_layer_versions(
            CompatibleRuntime='python3.8',
            LayerName=layer_name
        )

        versions = [
            version['Version'] for version in response['LayerVersions']]

        latest_version = max(versions)
    except aws_lambda.exceptions.ResourceNotFoundException as exc:
        raise Exception(
            f'Layer {layer_name} does not exist. '
            "Use 'push_layer=True' or 'create_layer=True' "
            'if layer has already been pushed to S3.'
        ) from exc

    try:
        response = aws_lambda.get_function(
            FunctionName=function_name)
    except aws_lambda.exceptions.ResourceNotFoundException:
        response = None
        count = 0
        while response is None:
            if count > 6:
                raise TimeoutError
            try:
                response = aws_lambda.create_function(
                    FunctionName=function_name,
                    Runtime='python3.8',
                    Role=role_arn,
                    Handler=LEnv.HANDLER,
                    Code={
                        'S3Bucket': LEnv.BUCKET_NAME,
                        'S3Key': lambda_key
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

        response = aws_lambda.add_permission(
            FunctionName=function_name,
            StatementId='1',
            Action='lambda:InvokeFunction',
            Principal='s3.amazonaws.com',
            SourceArn=get_bucket_arn(LEnv.BUCKET_NAME)
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

        # Add S3 event trigger to the lambda
        response = s3.put_bucket_notification_configuration(
            Bucket=LEnv.BUCKET_NAME,
            NotificationConfiguration={
                'LambdaFunctionConfigurations': [{
                    'LambdaFunctionArn': function_arn,
                    'Events': ['s3:ObjectCreated:*'],
                    'Filter': {
                        'Key': {
                            'FilterRules': [
                                {
                                    'Name': 'prefix',
                                    'Value': f'{KFEnv.BUCKET_FOLDER}'
                                             f'{KFEnv.BUCKET_PREFIX}'
                                },
                            ]
                        }
                    }
                }]
            },
        )
        logger.info('An S3 trigger is set for lambda %s.', function_name)

        print(response)

    aws_lambda_hash = response['Configuration']['CodeSha256']
    # To produce the same hash as AWS's CodeSha256
    # https://stackoverflow.com/questions/32038881/python-get-base64-encoded-md5-hash-of-an-image-object
    local_lambda_hash_b64 = b64encode(local_lambda_hash).strip().decode()

    aws_layer_version_num = \
        int(response['Configuration']['Layers'][0]['Arn'].split(':')[-1])

    if aws_lambda_hash != local_lambda_hash_b64:
        # Publish a new version if the code on S3 got updated
        response = aws_lambda.update_function_code(
            FunctionName=function_name,
            S3Bucket=LEnv.BUCKET_NAME,
            S3Key=lambda_key,
            Publish=True
        )
        logger.info(
            'The code for lambda %s got updated from '
            'the latest version in S3.',
            function_name)
    else:
        logger.info('Lambda %s already exists.', function_name)

    if aws_layer_version_num < latest_version:
        response = aws_lambda.update_function_configuration(
            FunctionName=function_name,
            Layers=[
                layer_arn + f':{latest_version}',
            ]
        )
        logger.info(
            'The layer for lambda %s got updated to the latest version.',
            function_name)
    else:
        logger.info(
            'The layer for lambda %s is already at the latest version.',
            function_name)
