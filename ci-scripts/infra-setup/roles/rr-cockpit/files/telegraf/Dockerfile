FROM telegraf


RUN apt-get update && apt-get install -y --no-install-recommends \
                        python-pip \
                        python-setuptools \
                        python-pandas \
                        python-wheel \
                        python-yaml \
                   && rm -rf /var/lib/apt/lists/*

COPY *.py requirements.txt /
RUN pip install -r requirements.txt

COPY telegraf.conf /etc/telegraf/telegraf.conf
COPY *.py /usr/local/bin/

ENTRYPOINT ["/entrypoint.sh"]
CMD ["telegraf", "--debug"]
