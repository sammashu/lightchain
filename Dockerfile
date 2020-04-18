FROM python:3.7-slim

ADD ./ /

RUN pip3 install -r requirements.txt

CMD python3 node.py