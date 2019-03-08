FROM python:3-alpine
COPY . /app
WORKDIR /app
RUN apk update \
  && apk add postgresql-libs \
  && apk add --virtual build-deps gcc musl-dev postgresql-dev libffi-dev \
  && pip3 install -r requirements.txt --no-cache-dir && \
  apk --purge del build-deps

CMD gunicorn wsgi:application -b 0.0.0.0:8080
EXPOSE 8080
