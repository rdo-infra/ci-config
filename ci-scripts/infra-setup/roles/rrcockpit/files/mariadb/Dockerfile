FROM python:2.7

COPY requirements.txt /
RUN pip install -r requirements.txt \
    && apt-get update \
    && apt-get install -y mariadb-client vim \

COPY *.json *.py *.sh *.sql /usr/local/bin/
COPY *.yaml *.sql /tmp/
COPY run.sh /tmp/
CMD run.sh
