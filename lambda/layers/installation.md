[*Towards Data Science*](https://towardsdatascience.com/how-to-install-python-packages-for-aws-lambda-layer-74e193c76a91): How to Install Python Packages for AWS Lambda Layers

```
docker build -f Dockerfile -t lambdalayer:latest .

# Remove al stopped containers
docker rm $(docker ps -a -q)

docker run -it --name lambdalayer lambdalayer:latest bash

docker cp lambdalayer:python.zip .
```