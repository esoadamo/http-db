from enum import Enum
from json import loads, dumps, JSONDecodeError
from typing import Optional, Tuple, Set
from os import environ

from flask import Flask, request, Response
from datetime import datetime
from flask_sock import Sock
from flask_cors import CORS
from sqlitedb import IndexedDBManager

app = Flask(__name__)
CORS(app)
app.config['SOCK_SERVER_OPTIONS'] = {'ping_interval': 25}
messages = []
sock = Sock(app)


class Operation(Enum):
    READ = 1
    WRITE = 2
    APPEND = 3
    CLEAR = 4


WATCHES = {}


@sock.route('/instant/db/')
def echo(ws):
    opened_items: Set[str] = set()


    def error(message: str) -> None:
        ws.send(dumps({'error': message}))


    def send_item(item: str) -> None:
        try:
            content = DB_TABLE_VALUES[item]
            exists = True
        except KeyError:
            content = None
            exists = False
        ws.send(dumps({'item': item, 'content': content, 'exists': exists}))


    while True:
        try:
            data = loads(ws.receive())
        except JSONDecodeError:
            error('invalid JSON')
            continue

        try:
            command = data['command']
            item = data['item']
        except KeyError:
            error('missing command or item')
            continue

        data = data.get('data', {})

        if command == 'open':
            secret = data.get('secret')
            if not verify_set_secret(item, secret):
                error('unauthorized')
                continue
            if item not in WATCHES:
                WATCHES[item] = set()
            WATCHES[item].add(ws)
            opened_items.add(ws)
            send_item(item)
            continue
        if command == 'get':
            if item not in opened_items:
                error('unauthorized')
                continue
            send_item(item)
            continue

        error('unkown command')

    print('connection closed')



DB = IndexedDBManager(environ.get('X_PATH_APP_DB', 'db-proxy.sqlite3'))
DB_TABLE_VALUES = DB['values']
DB_TABLE_SECRETS = DB['secrets']


@app.route('/', methods=['GET', 'POST'])
def hello_world():
    if request.method == "POST":
        messages.append((datetime.now(), request.form['msg']))
    return respond_plain_text('\n'.join(["%s: %s" % (str(time), msg) for time, msg in messages]))


@app.route('/clear')
def clear():
    messages.clear()
    return respond_plain_text('ok')


@app.route('/log/<string:msg>')
def new_message(msg):
    messages.append((datetime.now(), msg))
    return respond_plain_text('ok')


@app.route('/db/', methods=['GET', 'POST'])
def db():
    return db_key()


@app.route('/db/<string:item>', methods=['GET', 'POST', 'DELETE', 'PUT'])
def db_key(item: Optional[str] = None):
    req = get_request_dict()

    if item is None:
        try:
            item = req[item]
        except KeyError:
            return respond_plain_text('missing item'), 400

    password = req.get('password')
    value = None
    operation: Operation = Operation.READ

    if request.method == 'DELETE':
        operation = Operation.CLEAR
    elif 'value' in req:
        operation = Operation.WRITE
        value = req['value']
        if 'append' in req:
            operation = Operation.APPEND

    status, message = perform_db_operation(
        item=item,
        operation=operation,
        secret=password,
        value=value
    )
    return respond_plain_text(message), status



def verify_set_secret(item: str, secret: Optional[str] = None) -> bool:
    expected_secret = DB_TABLE_SECRETS.get(item)
    if expected_secret != secret:
        if expected_secret is None:
            DB_TABLE_SECRETS[item] = secret
        else:
            return False
    return True



def notify_watches(item: str, content: any, exists: bool = True) -> None:
    for ws in WATCHES.get(item, set()):
        try:
            ws.send(dumps({'item': item, 'content': content, 'exists': exists}))
        except Exception:
            pass



def perform_db_operation(item: str, operation: Operation, secret: Optional[str] = None, value: Optional[any] = None) \
        -> Tuple[int, Optional[any]]:
    if not verify_set_secret(item, secret):
        return 401, 'unauthorized'

    if operation in (Operation.READ, Operation.CLEAR):
        try:
            current_value = DB_TABLE_VALUES[item]
        except KeyError:
            return 404, ''

        if operation == Operation.CLEAR:
            del DB_TABLE_VALUES[item]

        return 200, current_value
    if operation in (Operation.WRITE, Operation.APPEND):
        current_value = DB_TABLE_VALUES.get(item, '')
        if operation == Operation.APPEND:
            new_value = current_value + str(value)
        else:
            new_value = value

        notify_watches(item, new_value)
        DB_TABLE_VALUES[item] = new_value
        return 200, 'ok'


# noinspection DuplicatedCode
def get_request_dict():  # type: () -> dict
    d = {}
    d.update(request.args)
    d.update(request.get_data())
    # noinspection PyBroadException
    try:
        d.update(request.get_json())
    except Exception:
        pass
    return d


def respond_plain_text(s):  # type: (str) -> Response
    return Response(s, mimetype='text/plain')
