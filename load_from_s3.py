import logging
import json

import boto3
from botocore.exceptions import ClientError
from requests_aws4auth import AWS4Auth
from elasticsearch import Elasticsearch, RequestsHttpConnection, ConflictError
# from elasticsearch.helpers import bulk

from stream.env import ESEnv

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    ESEnv.ACCESS_KEY_ID, ESEnv.SECRET_ACCESS_KEY,
    ESEnv.REGION, "es",
    session_token=credentials.token
)

es = Elasticsearch(
    hosts=[{'host': ESEnv.HOST, 'port': ESEnv.PORT}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

s3 = boto3.client(
    's3',
    region_name=ESEnv.REGION,
    aws_access_key_id=ESEnv.ACCESS_KEY_ID,
    aws_secret_access_key=ESEnv.SECRET_ACCESS_KEY)

bucket = ESEnv.BUCKET_NAME
key = 'tweets/project_flabbergasted/2020/09/03/13/' \
      'crowdbreaks-flabbergasted-1-2020-09-03-13-06-' \
      '54-3df63686-82a7-4c14-823a-3aa8b5704ec7.gz'


if __name__ == '__main__':
    # Get S3 object
    try:
        response = s3.select_object_content(
            Bucket=bucket,
            Key=key,
            ExpressionType='SQL',
            Expression="select * from s3object",
            InputSerialization={
                'CompressionType': 'GZIP', 'JSON': {'Type': 'LINES'}},
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
        if 'Records' in event:
            records = event['Records']['Payload'].decode('utf-8')

            bulk_data = []
            for rec in records.splitlines():
                status = json.loads(rec)
                index_name = \
                    ESEnv.INDEX_PREFIX + status['_tracking_info']['slug']

                try:
                    es.create(
                        index=index_name, id=status['id'],
                        body=status, doc_type='tweet')
                except ConflictError as exc:
                    # Happens when a document with the same ID already exists.
                    logger.error(exc)

            # Does not raise ConflictError, just loads new vesrions
            # of the same doc, if a duplicate.
            #     bulk_doc = {
            #         '_index': index_name,
            #         '_type': 'tweet',
            #         '_id': status['id'],
            #         '_source': status
            #     }
            #     bulk_data.append(bulk_doc)

            # success, _ = bulk(es, bulk_data)
            # logger.info('ElasticSearch indexed %d documents.', success)
