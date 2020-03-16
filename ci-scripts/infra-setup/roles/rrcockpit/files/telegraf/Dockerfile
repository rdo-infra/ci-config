FROM telegraf:1.8.3

RUN apt-get update && apt-get install -y --no-install-recommends \
                        python-pandas \
                        python-wheel \
                        libyaml-dev \
                        less \
                        vim \
                        && rm -rf /var/lib/apt/lists/* \
                        && wget https://bootstrap.pypa.io/get-pip.py \
                        && python get-pip.py \
                        && pip install -U pip setuptools

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY telegraf.conf /etc/telegraf/telegraf.conf
COPY telegraf.d/* /etc/telegraf/telegraf.d/
COPY *.py /usr/local/bin/

ENTRYPOINT ["/entrypoint.sh"]
CMD ["telegraf", "--debug", "--config-directory","/etc/telegraf/telegraf.d/","--input-filter", "exec"]
