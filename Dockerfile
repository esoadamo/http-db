FROM python:alpine

ENV DIR_APP /opt/app
ENV DIR_DATA /srv/app

RUN apk add git

RUN mkdir -p $DIR_APP && mkdir -p $DIR_DATA
RUN addgroup -S app && adduser -S app -G app
RUN chown app $DIR_DATA

WORKDIR $DIR_APP

RUN python3 -m venv venv
RUN venv/bin/pip install --no-cache-dir gunicorn

ADD requirements.txt requirements.txt
RUN venv/bin/pip install --no-cache-dir -r requirements.txt

ADD . $DIR_APP/
USER app

EXPOSE 5000
ENTRYPOINT ["/bin/sh"]
CMD ["-c", ". $DIR_APP/venv/bin/activate && export X_PATH_APP_DB=$DIR_DATA/database.sqlite3 && gunicorn -w 1 -b :5000 --threads 100 app:app"]
