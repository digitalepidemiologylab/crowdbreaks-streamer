# https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
FROM python:3.8

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies:
RUN mkdir /home/crowdbreaks-streamer-2
COPY . /home/crowdbreaks-streamer-2
RUN cd /home/crowdbreaks-streamer-2 \
    && pip install --upgrade pip \
    && pip install -e .

WORKDIR /home/crowdbreaks-streamer-2
CMD run-stream