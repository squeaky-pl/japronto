import os.path
import sqlite3
from functools import partial
import sys
import json

from japronto.app import Application

DB_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'todo.sqlite'))
db_connect = partial(sqlite3.connect, DB_FILE)


def maybe_create_schema():
    db = db_connect()
    db.execute("""
        CREATE TABLE IF NOT EXISTS todos
        (id INTEGER PRIMARY KEY, todo TEXT)""")
    db.close()


def cursor(request):
    def done_cb(request):
        request.extra['conn'].close()

    if not 'conn' in request.extra:
        request.extra['conn'] = db_connect()
        request.add_done_callback(done_cb)

    return request.extra['conn'].cursor()



def add_todo(request):
    cur = request.cursor
    todo = request.json["todo"]
    cur.execute("""INSERT INTO todos (todo) VALUES (?)""", (todo,))
    last_id = cur.lastrowid
    cur.connection.commit()

    return request.Response(json={"id": last_id, "todo": todo})


def list_todos(request):
    cur = request.cursor
    cur.execute("""SELECT id, todo FROM todos""")
    todos = [{"id": id, "todo": todo} for id, todo in cur]

    return request.Response(json={"results": todos})


def show_todo(request):
    cur = request.cursor
    id = int(request.match_dict['id'])
    cur.execute("""SELECT id, todo FROM todos WHERE id = ?""", (id,))
    todo = cur.fetchone()
    if not todo:
        return request.Response(status_code=404, json={})
    todo = {"id": todo[0], "todo": todo[1]}

    return request.Response(json=todo)


def delete_todo(request):
    cur = request.cursor
    id = int(request.match_dict['id'])
    cur.execute("""DELETE FROM todos WHERE id = ?""", (id,))
    if not cur.rowcount:
        return request.Response(status_code=404, json={})
    cur.connection.commit()

    return request.Response(json={})


if __name__ == '__main__':
    maybe_create_schema()
    app = Application()
    app.extend_request(cursor, property=True)
    router = app.router
    router.add_route('/todos', list_todos, method='GET')
    router.add_route('/todos/{id}', show_todo, method='GET')
    router.add_route('/todos/{id}', delete_todo, method='DELETE')
    router.add_route('/todos', add_todo, method='POST')
    app.run()
