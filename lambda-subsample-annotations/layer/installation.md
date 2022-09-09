[*Towards Data Science*](https://towardsdatascience.com/how-to-install-python-packages-for-aws-lambda-layer-74e193c76a91): How to Install Python Packages for AWS Lambda Layers

NB: This is an outdated manual method, curently this is handled automatically in `awstools.llambda.create_lambda_layer`.

```
docker build -f Dockerfile -t lambdalayer:latest .

# Remove all stopped containers
docker rm $(docker ps -a -q)

docker run -it --name lambdalayer lambdalayer:latest bash

docker cp lambdalayer:python.zip .
```