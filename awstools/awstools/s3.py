import logging
import sys

import boto3
from botocore.exceptions import ClientError

from .env import AWSEnv

s3 = boto3.client(
    's3',
    region_name=AWSEnv.REGION,
    aws_access_key_id=AWSEnv.ACCESS_KEY_ID,
    aws_secret_access_key=AWSEnv.SECRET_ACCESS_KEY)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_s3_object(bucket, key, input_serialization, s3_client=s3):
    # Get S3 object
    records = b''
    repeat = True
    while repeat:
        try:
            response = s3_client.select_object_content(
                Bucket=bucket,
                Key=key,
                ExpressionType='SQL',
                Expression="select * from s3object",
                InputSerialization=input_serialization,
                OutputSerialization={'JSON': {}}
            )
        except ClientError as exc:
            if exc.response['Error']['Code'] == 'NoSuchKey':
                logger.error(
                    '%s: %s Key: %s',
                    exc.response['Error']['Code'],
                    exc.response['Error']['Message'],
                    key)
                continue
            else:
                raise exc

        for event in response['Payload']:
            if 'End' in event:
                repeat = False
            if 'Records' in event:
                records += event['Records']['Payload']

    return records.decode('utf-8')
