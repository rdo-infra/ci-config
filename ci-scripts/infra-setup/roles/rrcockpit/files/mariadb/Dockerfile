FROM python:3.6

COPY requirements.txt /
RUN pip install -r requirements.txt \
    && apt-get update \
    && apt-get install -y mariadb-client \
    golang
RUN go get github.com/jedib0t/go-pretty/table
RUN go get gopkg.in/yaml.v2
COPY *.py *.sh *.sql /usr/local/bin/
COPY *.yaml *.sql /tmp/
COPY skiplist.go /tmp/
RUN go build /tmp/skiplist.go
COPY skiplist /usr/local/bin
COPY run.sh /tmp/
CMD run.sh
