FROM python:3.6-alpine
MAINTAINER Sagi Shnaidman "@sshnaidm"
RUN apk update && \
    apk add --no-cache --virtual .build-deps python3-dev build-base libffi-dev openssl-dev linux-headers && \
    rm -rf /tmp/* && \
    rm -rf /var/cache/apk/* \
    rm -rf /root/.cache
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt
COPY . /app
ENTRYPOINT [ "python" ]
CMD [ "api.py" ]
