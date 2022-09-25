# https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
FROM python:3.8

RUN apt-get update

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip \
    && pip install 'git+https://github.com/digitalepidemiologylab/crowdbreaks-streamer.git@24#egg=moob&subdirectory=moob'

ENTRYPOINT ["train-moob"]