FROM python:3.6

COPY requirements.txt /
RUN pip install --no-cache-dir -r requirements.txt

COPY *.json *.py *.sh /
ENTRYPOINT ["./entrypoint.sh"]
CMD [""]
