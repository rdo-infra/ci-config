FROM quay.io/centos/centos:stream8

RUN dnf install -y \
                        python3 \
                        python3-pip \
                        python3-setuptools \
                        python3-wheel \
                        python3-hawkey
                        #python3-flask \
                        #python3-flask-wtf \
                        #python3-requests \
                        #python3-beautifulsoup4

ENV VIRT_ENV=/app/venv
RUN python3 -m venv --system-site-packages $VIRT_ENV
ENV PATH="$VIRT_ENV/bin:$PATH"

RUN pip3 install --upgrade pip
COPY requirements.txt /
RUN pip3 install -r /requirements.txt

COPY . /app
WORKDIR /app

ENTRYPOINT ["python3"]
CMD [ "web_diff_builds.py" ]
