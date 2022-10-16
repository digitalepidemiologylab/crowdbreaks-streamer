import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
# from requests_aws4auth import AWS4Auth

from .env import AWSEnv, ESEnv

# https://forums.aws.amazon.com/thread.jspa?threadID=197439
if AWSEnv.SESSION_TOKEN == '':
    # Launched from a server, no need for a session token
    session = boto3.Session(
        region_name=AWSEnv.REGION,
        aws_access_key_id=AWSEnv.ACCESS_KEY_ID,
        aws_secret_access_key=AWSEnv.SECRET_ACCESS_KEY
    )
else:
    # Launched from a lambda, a session token is in the env
    session = boto3.Session(
        # region_name=AWSEnv.REGION,
        # aws_access_key_id=AWSEnv.ACCESS_KEY_ID,
        # aws_secret_access_key=AWSEnv.SECRET_ACCESS_KEY,
        # aws_session_token=AWSEnv.SESSION_TOKEN
    )

s3 = session.client('s3')
aws_lambda = session.client('lambda')
iam = session.client('iam')
firehose = session.client('firehose')
ecs = session.client('ecs')
ecr = session.client('ecr')

credentials = session.get_credentials()

# Login to AWS Elasticsearch, outdated
# awsauth = AWS4Auth(
#     ESEnv.ACCESS_KEY_ID, ESEnv.SECRET_ACCESS_KEY,
#     ESEnv.REGION, "es",
#     session_token=credentials.token
# )

# es = Elasticsearch(
#     hosts=[{'host': ESEnv.HOST, 'port': ESEnv.PORT}],
#     http_auth=awsauth,
#     use_ssl=True,
#     verify_certs=True,
#     connection_class=RequestsHttpConnection,
#     request_timeout=120
# )

# Login to Elastic CLoud Elasticsearch
es = Elasticsearch(
    cloud_id=ESEnv.CLOUD_ID,
    api_key=ESEnv.API_KEY,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    request_timeout=120
)
