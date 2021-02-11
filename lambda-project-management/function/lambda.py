from awstools.session import s3, AWSEnv
from awstools.config import ConfigManager
# from awstools.env import ECSEnv

# TODO
# - [ ] Add cluster and service names to awstools.env


def handler(event, context):
    response = s3.list_object_versions(
        Prefix=AWSEnv.STREAM_CONFIG_S3_KEY, Bucket=AWSEnv.BUCKET_NAME)
        
    # 1. Order by last modified
    # 2. Take two latest versions
    # 3. Create config_manager objects off of them
    # 4. Compare
    # 5. Take action based on changes
    #     - Stop streaming
    #     - Restart streaming
    
    versions = sorted(response['Versions'], key=lambda k: k['LastModified'])
    print(versions)
    
    for obj in versions[-2:]:
        print(f"Key: {obj['Key']}")
        print(f"VersionId: {obj['VersionId']}")
        print(f"LastModified: {obj['LastModified']}")
        print(f"IsLatest: {obj['IsLatest']}")
        print(f"Size: {obj.get('Size', 0) / 1e6}")
        
        # Get 2 last versions
        response = 
    
    # # To stop streaming, set desired count to 0 and wait until tasks are stopped
    # # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.update_service
    # response = client.update_service(
    #     cluster=ECSEnv.CLUSTER,
    #     service=ECSEnv.SERVICE,
    #     desiredCount=0)

    # def check_desired_count(cluster, service, count, time_step=30, time_limit=300):
    #     updated = False
    #     time_slept = 0
    #     while not updated:
    #         # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.describe_services
    #         response = client.describe_services(
    #             cluster=cluster,
    #             services=[service]
    #         )
            
    #         for service in response['services']:
    #             if service['serviceName'] == service:
    #                 if time_slept < time_limit:
    #                     if service['runningCount'] != count:
    #                         time_slept += time_step
    #                         time.sleep(time_step)
    #                     else:
    #                         updated = True
    #                 else:
    #                     raise Exception('Waiting more than %d s.', time_limit)
    #             else:
    #                 raise Exception('No inquired service name in the response.')
