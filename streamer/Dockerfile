# https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
FROM python:3.8

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies:
RUN mkdir /home/streamer
COPY ./streamer /home/streamer
RUN cd /home/streamer \
    && pip install --upgrade pip \
    && pip install -e .

WORKDIR /home/streamer
CMD run-stream