FROM python:2.7

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY *.json *.py *.sh /
ENTRYPOINT ["./entrypoint.sh"]
CMD [""]
