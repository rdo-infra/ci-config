FROM python:2.7

COPY requirements.txt /
RUN pip install -r requirements.txt \
    && apt-get update \
    && apt-get install -y mysql-client

COPY *.json *.py *.sh *.sql /tmp/
CMD /tmp/run.sh 
