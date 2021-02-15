import logging
import time
import hashlib
from base64 import b64encode

import shutil
import subprocess
import sys
import os

from .env import LEnv, ESEnv
from .session import s3, iam, aws_lambda
from .firehose import get_bucket_arn

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def zip_lambda_func(lambda_dir):
    base_name = os.path.join(lambda_dir, 'lambda')
    root_dir = os.path.join(lambda_dir, 'function')
    shutil.make_archive(
        base_name, LEnv.EXTENSION, root_dir)
    return '.'.join([base_name, LEnv.EXTENSION])


def zip_lambda_layer(lambda_dir):
    base_name = os.path.join(lambda_dir, 'layer')
    root_dir = os.path.join(lambda_dir, 'layer')
    # Install requirements.txt to python
    # https://stackoverflow.com/a/50255019/4949133
    subprocess.check_call([
        sys.executable, '-m',
        'pip', 'install',
        '-r', os.path.join(base_name, 'requirements.txt'),
        '-t', os.path.join(base_name, 'python')])
    # https://stackoverflow.com/a/25650295/4949133
    # https://docs.python.org/3/library/shutil.html#archiving-example-with-base-dir
    shutil.make_archive(
        base_name, LEnv.EXTENSION,
        root_dir=root_dir,
        base_dir='python')
    return '.'.join([base_name, LEnv.EXTENSION])


def get_function_name_arn(lambda_name):
    function_name = f'{LEnv.APP_NAME.lower()}-lambda-{lambda_name}'
    function_arn = f'arn:aws:lambda:{LEnv.REGION}:{LEnv.ACCOUNT_NUM}:' \
                   f'function:{function_name}'
    return function_name, function_arn


def get_layer_name_arn(lambda_name):
    layer_name = f'{LEnv.APP_NAME.lower()}-lambda-layer-{lambda_name}'
    layer_arn = f'arn:aws:lambda:{LEnv.REGION}:{LEnv.ACCOUNT_NUM}:' \
                f'layer:{layer_name}'
    return layer_name, layer_arn


def lambda_to_iam_name(lambda_name):
    return ''.join([s.capitalize() for s in lambda_name.split('-')])


def get_role_name_arn(lambda_name):
    role_name = lambda_to_iam_name(lambda_name)
    role_name = f'{LEnv.APP_NAME.capitalize()}Lambda{role_name}'
    role_arn = f'arn:aws:iam::{LEnv.ACCOUNT_NUM}:role/{role_name}'
    return role_name, role_arn


def get_policy_name_arn(lambda_name):
    policy_name = lambda_to_iam_name(lambda_name)
    policy_name = f'{LEnv.APP_NAME.capitalize()}Lambda{policy_name}'
    policy_arn = f'arn:aws:iam::{LEnv.ACCOUNT_NUM}:policy/{policy_name}'
    return policy_name, policy_arn


def prepare_policy(policy_path, function_name):
    with open(policy_path, 'r') as f:
        policy = f.read()
        policy = policy.replace('ACCOUNT_NUM', LEnv.ACCOUNT_NUM)
        policy = policy.replace('BUCKET_NAME', LEnv.BUCKET_NAME)
        policy = policy.replace('REGION', LEnv.REGION)
        policy = policy.replace('DOMAIN', ESEnv.DOMAIN)
        policy = policy.replace('FUNCTION_NAME', function_name)
        policy = policy.replace('MODEL_NAME', LEnv.APP_NAME + '-*')
    return policy


def create_lambda_role(lambda_name, policy_path):
    role_name, _ = get_role_name_arn(lambda_name)
    policy_name, policy_arn = get_policy_name_arn(lambda_name)
    function_name, _ = get_function_name_arn(lambda_name)

    # Prepare the role trust relationship (fill in missing info)
    with open(LEnv.ROLE_TRUST_RELATIONSHIP_PATH, 'r') as f:
        role_trust_relationship = f.read()
        role_trust_relationship = role_trust_relationship.replace(
            'ACCOUNT_NUM', LEnv.ACCOUNT_NUM)
        logger.debug(
            'Role trust relationship:\n\n%s\n',
            role_trust_relationship)

    # Create a role
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

    # Prepare the policy (fill in missing info)
    policy = prepare_policy(policy_path, function_name)

    # Create a policy
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

    # Attach the policy to the role
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


def check_s3_diff(bucket, key, local_path=None):
    s3_obj = None
    try:
        response = s3.get_object(
            Bucket=bucket,
            Key=key
        )
        s3_obj = response['Body'].read()
    except s3.exceptions.NoSuchKey:
        return None, None

    s3_obj_hash = hashlib.sha256(s3_obj).digest()

    if local_path:
        with open(local_path, 'rb') as f:
            local_obj_hash = hashlib.sha256(f.read()).digest()

    diff = s3_obj_hash == local_obj_hash if local_path else None

    return diff, s3_obj_hash


def create_lambda_layer(
    lambda_name,
    layer_local_zip_path,
    push_to_s3=False
):
    layer_name, _ = get_layer_name_arn(lambda_name)
    layer_key = os.path.join(
        LEnv.BUCKET_FOLDER, f'{layer_name}.{LEnv.EXTENSION}')

    if push_to_s3:
        s3_diff, _ = check_s3_diff(
            LEnv.BUCKET_NAME, layer_key, layer_local_zip_path)
        if not s3_diff:
            s3.upload_file(
                layer_local_zip_path, LEnv.BUCKET_NAME, layer_key)
            logger.info('Layer %s pushed to S3.', layer_name)
        else:
            logger.info(
                'Layer %s not pushed to S3: '
                'local zip is the same as on S3.',
                layer_name)

        if push_to_s3 and not s3_diff:
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


def create_s3_to_es_lambda(
    lambda_name,
    lambda_local_zip_path,
    policy_path,
    push_to_s3=False,
    s3_trigger=False,
    s3_prefix=None
):
    _, role_arn = get_role_name_arn(lambda_name)
    function_name, function_arn = get_function_name_arn(lambda_name)
    layer_name, layer_arn = get_layer_name_arn(lambda_name)
    lambda_key = os.path.join(
        LEnv.BUCKET_FOLDER, f'{function_name}.{LEnv.EXTENSION}')

    # If push_to_s3 is True and the code has been changed
    if push_to_s3:
        hash_match, _ = check_s3_diff(
            LEnv.BUCKET_NAME, lambda_key, lambda_local_zip_path)
        if not hash_match:
            s3.upload_file(
                lambda_local_zip_path, LEnv.BUCKET_NAME, lambda_key)
            logger.info('Function %s pushed to S3.', function_name)
        else:
            logger.info(
                'Function %s not pushed to S3: '
                'local zip is the same as on S3.',
                function_name)

    # Create lambda role
    create_lambda_role(lambda_name, policy_path)

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
            "Use 'push_to_s3=True' or 'create_layer=True' "
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
                            'ES_INDEX_PREFIX': ESEnv.INDEX_PREFIX,
                            'AWS_ACCOUNT_NUM': ESEnv.ACCOUNT_NUM
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

    # Update function code
    _, s3_lambda_hash = check_s3_diff(LEnv.BUCKET_NAME, lambda_key)
    # To produce the same hash as AWS's CodeSha256
    # https://stackoverflow.com/questions/32038881/python-get-base64-encoded-md5-hash-of-an-image-object
    s3_lambda_hash_b64 = b64encode(s3_lambda_hash).strip().decode()
    aws_lambda_hash = response['Configuration']['CodeSha256']

    if aws_lambda_hash != s3_lambda_hash_b64:
        # Publish a new version if the code on S3 got updated
        _ = aws_lambda.update_function_code(
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

    # Update layer version
    aws_layer_version_num = \
        int(response['Configuration']['Layers'][0]['Arn'].split(':')[-1])

    if aws_layer_version_num < latest_version:
        _ = aws_lambda.update_function_configuration(
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

    if s3_trigger:
        # Add permission to invoke from S3
        try:
            _ = aws_lambda.add_permission(
                FunctionName=function_name,
                StatementId='1',
                Action='lambda:InvokeFunction',
                Principal='s3.amazonaws.com',
                SourceArn=get_bucket_arn(LEnv.BUCKET_NAME)
            )
        except aws_lambda.exceptions.ResourceConflictException:
            pass

        # Add S3 event trigger to the lambda
        print(s3_prefix)
        _ = s3.put_bucket_notification_configuration(
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
                                    'Value': s3_prefix
                                },
                            ]
                        }
                    }
                }]
            },
        )
        logger.info('An S3 trigger is set for lambda %s.', function_name)