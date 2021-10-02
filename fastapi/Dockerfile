FROM python:3.8.10

RUN mkdir /code

COPY main.py /code

COPY requirements.txt /code

WORKDIR /code

RUN pip3 install -r requirements.txt

EXPOSE 8000