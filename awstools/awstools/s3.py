import logging

from botocore.exceptions import ClientError

from .session import s3

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_long_s3_object(bucket, key, input_serialization, s3_client=s3):
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
                repeat = False
                continue
            else:
                raise exc

        for event in response['Payload']:
            if 'End' in event:
                repeat = False
            if 'Records' in event:
                records += event['Records']['Payload']

    return records.decode('utf-8')


def get_s3_object(bucket, key, s3_client=s3, version_id=None):
    params = {'Bucket': bucket, 'Key': key}
    if version_id:
        params['VersionId'] = version_id
    response = s3_client.get_object(**params)

    return response['Body'].decode('utf-8')
