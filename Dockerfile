# https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
FROM python:3.8

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies:
RUN mkdir crowdbreaks-streamer-2 \
    && cd crowdbreaks-streamer-2
COPY . .
RUN pip install -e .

CMD run-stream