FROM amazonlinux:2
RUN yum install -y python37 && \
    yum install -y python3-pip && \
    yum install -y zip && \
    yum clean all
RUN python3.7 -m pip install --upgrade pip && \
    python3.7 -m pip install virtualenv
COPY requirements.txt /tmp/
RUN python3.7 -m venv lambda && \
    source lambda/bin/activate && \
    pip install -r /tmp/requirements.txt -t python/ && \
    deactivate && \
    zip -r python.zip python/