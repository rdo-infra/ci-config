FROM python:3.6

COPY requirements.txt /
RUN pip install -r requirements.txt \
    && apt-get update \
    && apt-get install -y mariadb-client \
    golang
COPY *.py *.sh *.sql /usr/local/bin/
COPY *.yaml *.sql /tmp/
COPY skiplist.go ./
RUN go build -o /usr/local/bin/skiplist skiplist.go
COPY run.sh /tmp/
CMD run.sh
