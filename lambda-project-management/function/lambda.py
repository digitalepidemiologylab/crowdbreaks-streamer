from awstools.session import s3
from awstools.session import AWSEnv


response = s3.list_object_versions(
    Prefix=AWSEnv.STREAM_CONFIG_S3_KEY, Bucket=AWSEnv.BUCKET_NAME)

for obj in [*response['Versions'], *response.get('DeleteMarkers', [])]:
    print(f"Key: {obj['Key']}")
    print(f"VersionId: {obj['VersionId']}")
    print(f"LastModified: {obj['LastModified']}")
    print(f"IsLatest: {obj['IsLatest']}")
    print(f"Size: {obj.get('Size', 0) / 1e6}")
