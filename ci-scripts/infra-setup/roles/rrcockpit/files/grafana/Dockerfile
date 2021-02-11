FROM python:3.6

COPY requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY *.json *.py *.sh /
ENTRYPOINT ["./entrypoint.sh"]
CMD [""]
