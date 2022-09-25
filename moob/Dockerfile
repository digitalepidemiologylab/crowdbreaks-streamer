# https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
FROM python:3.8

RUN apt-get update

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN mkdir /home/moob
COPY . /home/moob
RUN cd /home/moob \
    && ls . \
    && pip install --upgrade pip \
    && pip install -e .

WORKDIR /home

ENTRYPOINT ["train-moob"]