FROM python:3.10-alpine

ENV DIR_APP /opt/app
ENV DIR_DATA /srv/app

RUN apk add git && \
    apk add openssl

RUN mkdir -p $DIR_APP && mkdir -p $DIR_DATA && \
    addgroup -Sg 991 app && adduser -Su 991 app -G app && \
    chown app $DIR_DATA

WORKDIR $DIR_APP
RUN openssl req -newkey rsa:2048 -x509 -sha256 -days 3650 -nodes -out self.crt -keyout self.key -subj="/CN=http-db" && \
    chgrp app self.crt && \
    chgrp app self.key && \
    chmod 640 self.crt && \
    chmod 640 self.key

RUN python -m venv venv

RUN source $DIR_APP/venv/bin/activate && \
    pip install --no-cache-dir gunicorn

ADD requirements.txt requirements.txt
RUN source $DIR_APP/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

ADD . $DIR_APP/
USER app

EXPOSE 5000
ENTRYPOINT ["/bin/sh"]
CMD ["-c", ". $DIR_APP/venv/bin/activate && export X_PATH_APP_DB=$DIR_DATA/database.sqlite3 && gunicorn -w 1 -b :5000 --threads 100 --certfile=self.crt --keyfile=self.key app:app"]
