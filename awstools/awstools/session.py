import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from .env import AWSEnv, ESEnv


if AWSEnv.ACCESS_KEY_ID and AWSEnv.SECRET_ACCESS_KEY:
    session = boto3.Session(
        region_name=AWSEnv.REGION,
        aws_access_key_id=AWSEnv.ACCESS_KEY_ID,
        aws_secret_access_key=AWSEnv.SECRET_ACCESS_KEY
    )
else:
    session = boto3.Session()
    if session.get_credentials() is None:
        raise Exception('No credentials were found for this session.')

s3 = session.client('s3')
aws_lambda = session.client('lambda')
iam = session.client('iam')
firehose = session.client('firehose')

credentials = session.get_credentials()
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
