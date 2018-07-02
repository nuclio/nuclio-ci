ARG NUCLIO_TAG=unstable
ARG NUCLIO_ARCH=amd64
ARG NUCLIO_BASE_IMAGE=python:3.6-jessie

# Supplies processor uhttpc, used for healthcheck
FROM nuclio/uhttpc:0.0.1-amd64 as uhttpc

# Supplies processor binary, wrapper
FROM nuclio/handler-builder-python-onbuild:${NUCLIO_TAG}-${NUCLIO_ARCH} as processor

# From the base image
FROM ${NUCLIO_BASE_IMAGE}

# Copy required objects from the suppliers
COPY --from=processor /home/nuclio/bin/processor /usr/local/bin/processor
COPY --from=processor /home/nuclio/bin/py /opt/nuclio/
COPY --from=uhttpc /home/nuclio/bin/uhttpc /usr/local/bin/uhttpc

# Copy the handler directory to /opt/nuclio
COPY . /opt/nuclio

RUN sh && export PATH=$PATH:/usr/local/go/bin\
    && apt-get update && apt-get install -y git &&\
    apt-get install -y build-essential &&\
     curl -O https://download.docker.com/linux/static/stable/x86_64/docker-18.03.0-ce.tgz &&\
    tar xzvf docker-18.03.0-ce.tgz &&\
    cp docker/* /usr/bin/ &&\
    curl -O https://dl.google.com/go/go1.9.5.linux-amd64.tar.gz &&\
    tar -C /usr/local -xzf go1.9.5.linux-amd64.tar.gz && export PATH=$PATH:/usr/local/go/bin && \
    mkdir -p /root/go/src/github.com/nuclio/nuclio && cd /root/go/src/github.com/nuclio/nuclio &&\
    go get github.com/v3io/v3io-go-http/... &&\
    go get github.com/nuclio/logger/... && go get github.com/nuclio/nuclio-sdk-go/... &&\
    go get github.com/nuclio/amqp/...

# Readiness probe
HEALTHCHECK --interval=1s --timeout=3s CMD /usr/local/bin/uhttpc --url http://localhost:8082/ready || exit 1

# Run processor with configuration and platform configuration
CMD [ "processor", "--config", "/etc/nuclio/config/processor/processor.yaml", "--platform-config", "/etc/nuclio/config/platform/platform.yaml" ]

# Install packages
RUN pip install pydocumentdb sparkpost delegator.py slackclient parse psycopg2
