# https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
FROM python:3.8

RUN apt-get update \
    && apt-get install -y zip

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies:
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt -t python/ \
    && zip -r python.zip python/