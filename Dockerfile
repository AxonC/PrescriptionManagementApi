ARG PYTHON_IMAGE_TAG
FROM python:$PYTHON_IMAGE_TAG AS app-base

RUN apt-get update && apt-get install curl -y

WORKDIR /usr/src/app
COPY ./app/requirements.txt /usr/src/app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

FROM app-base AS app
WORKDIR /usr/src/app
COPY ./app/ /usr/src/app

RUN coverage run -m unittest discover unittests && coverage report --show-missing

EXPOSE 8000
CMD uvicorn main:app --reload --host 0.0.0.0

HEALTHCHECK --interval=30s --timeout=3s --retries=6 --start-period=6m \
  CMD curl -I -X GET "http://localhost:8000/" | grep "HTTP/1.1 200 OK"
