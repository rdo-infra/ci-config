FROM python:3.6

COPY requirements.txt /
RUN pip install -r requirements.txt \
    && apt-get update \
    && apt-get install -y mariadb-client

COPY *.py *.sh *.sql /usr/local/bin/
COPY *.yaml *.sql /tmp/
COPY skiplist /usr/local/bin
COPY run.sh /tmp/
CMD run.sh
