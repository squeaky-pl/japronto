#include <Python.h>


#include "cprotocol.h"
#include "cmatcher.h"
#include "crequest.h"
#include "cresponse.h"
#include "capsule.h"


#ifdef REAPER_ENABLED
const long CHECK_INTERVAL = 10;
const unsigned long IDLE_TIMEOUT = 60;
#endif

#ifdef PARSER_STANDALONE
static PyObject* Parser;
#endif
static PyObject* PyRequest;

#ifdef REAPER_ENABLED
static PyObject* check_interval;
#endif

static Request_CAPI* request_capi;
static Matcher_CAPI* matcher_capi;
static Response_CAPI* response_capi;


static PyObject *
Protocol_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
  Protocol* self = NULL;

  self = (Protocol*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

#ifdef PARSER_STANDALONE
  self->feed = NULL;
  self->feed_disconnect = NULL;
#else
  Parser_new(&self->parser);
#endif
  self->app = NULL;
  self->matcher = NULL;
  self->error_handler = NULL;
  self->request = NULL;
  self->transport = NULL;
  self->write = NULL;
#ifdef REAPER_ENABLED
  self->call_later = NULL;
  self->check_idle = NULL;
  self->check_idle_task = NULL;
#endif
  self->create_task = NULL;
  self->done_callback = NULL;

  finally:
  return (PyObject*)self;
}


static void
Protocol_dealloc(Protocol* self)
{
  Py_XDECREF(self->done_callback);
  Py_XDECREF(self->create_task);
#ifdef REAPER_ENABLED
  Py_XDECREF(self->check_idle_task);
  Py_XDECREF(self->check_idle);
  Py_XDECREF(self->call_later);
#endif
  Py_XDECREF(self->write);
  Py_XDECREF(self->transport);
  Py_XDECREF(self->request);
  Py_XDECREF(self->error_handler);
  Py_XDECREF(self->matcher);
  Py_XDECREF(self->app);
#ifdef PARSER_STANDALONE
  Py_XDECREF(self->feed_disconnect);
  Py_XDECREF(self->feed);
#else
  Parser_dealloc(&self->parser);
#endif

  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Protocol_init(Protocol* self, PyObject *args, PyObject *kw)
{
  int result = 0;
  PyObject* loop = NULL;
#ifdef PARSER_STANDALONE
  PyObject* parser = NULL;

  PyObject* on_headers = PyObject_GetAttrString((PyObject*)self, "on_headers");
  if(!on_headers)
    goto error;
  PyObject* on_body = PyObject_GetAttrString((PyObject*)self, "on_body");
  if(!on_body)
    goto error;
  PyObject* on_error = PyObject_GetAttrString((PyObject*)self, "on_error");
  if(!on_error)
    goto error;

  parser = PyObject_CallFunctionObjArgs(
    Parser, on_headers, on_body, on_error, NULL);
  if(!parser)
    goto error;

  self->feed = PyObject_GetAttrString(parser, "feed");
  if(!self->feed)
    goto error;

  self->feed_disconnect = PyObject_GetAttrString(parser, "feed_disconnect");
  if(!self->feed_disconnect)
    goto error;
#else
  if(Parser_init(&self->parser, self) == -1)
    goto error;
#endif

  if(!PyArg_ParseTuple(args, "O", &self->app))
    goto error;
  Py_INCREF(self->app);

  self->matcher = PyObject_GetAttrString(self->app, "_matcher");
  if(!self->matcher)
    goto error;

  self->error_handler = PyObject_GetAttrString(self->app, "error_handler");
  if(!self->error_handler)
    goto error;

  self->request = Py_None;
  Py_INCREF(self->request);

  loop = PyObject_GetAttrString(self->app, "_loop");
  if(!loop)
    goto error;

#ifdef REAPER_ENABLED
  self->call_later = PyObject_GetAttrString(loop, "call_later");
  if(!self->call_later)
    goto error;

  self->check_idle = PyObject_GetAttrString((PyObject*)self, "_check_idle");
  if(!self->check_idle)
    goto error;
#endif

  self->create_task = PyObject_GetAttrString(loop, "create_task");
  if(!self->create_task)
    goto error;

  self->done_callback = PyObject_GetAttrString((PyObject*)self, "_done_callback");
  if(!self->done_callback)
    goto error;

  goto finally;

  error:
  result = -1;
  finally:
  Py_XDECREF(loop);
#ifdef PARSER_STANDALONE
  Py_XDECREF(parser);
#endif
  return result;
}


#ifdef REAPER_ENABLED
static inline PyObject*
Protocol_schedule_check_idle(Protocol* self)
{
  Py_XDECREF(self->check_idle_task);
  self->check_idle_task = PyObject_CallFunctionObjArgs(
    self->call_later, check_interval, self->check_idle, NULL);

  return self->check_idle_task;
}
#endif


static PyObject*
Protocol_connection_made(Protocol* self, PyObject* args)
{
  if(!PyArg_ParseTuple(args, "O", &self->transport))
    goto error;
  Py_INCREF(self->transport);

  if(!(self->write = PyObject_GetAttrString(self->transport, "write")))
    goto error;

#ifdef REAPER_ENABLED
  self->idle_time = 0;
  self->read_ops = 0;
  self->last_read_ops = 0;

  if(!Protocol_schedule_check_idle(self))
    goto error;
#endif

  goto finally;

  error:
  return NULL;
  finally:
  Py_RETURN_NONE;
}


#ifdef REAPER_ENABLED
static PyObject*
Protocol__check_idle(Protocol* self, PyObject* args)
{
  PyObject* close = NULL;

  if(self->read_ops == self->last_read_ops) {
    self->idle_time += CHECK_INTERVAL;

    if(self->idle_time >= IDLE_TIMEOUT) {
      close = PyObject_GetAttrString(self->transport, "close");
      if(!close)
        goto error;
      PyObject* tmp = PyObject_CallFunctionObjArgs(close, NULL);
      if(!tmp)
        goto error;
      Py_DECREF(tmp);
      goto finally;
    }
  } else {
    self->idle_time = 0;
    self->last_read_ops = self->read_ops;
  }

  if(!Protocol_schedule_check_idle(self))
    goto error;

  goto finally;

  error:
  return NULL;

  finally:
  Py_XDECREF(close);
  Py_RETURN_NONE;
}
#endif


static PyObject*
Protocol_connection_lost(Protocol* self, PyObject* args)
{
#ifdef PARSER_STANDALONE
  PyObject* result = PyObject_CallFunctionObjArgs(
    self->feed_disconnect, NULL);
  if(!result)
    goto error;
  Py_DECREF(result);
#else
  if(!Parser_feed_disconnect(&self->parser))
    goto error;
#endif

  goto finally;

  error:
  return NULL;
  finally:
  Py_RETURN_NONE;
}


static PyObject*
Protocol_data_received(Protocol* self, PyObject* args)
{
  PyObject* data = NULL;
  if(!PyArg_ParseTuple(args, "O", &data))
    goto error;

#ifdef REAPER_ENABLED
  self->read_ops++;
#endif

#ifdef PARSER_STANDALONE
  PyObject* result = PyObject_CallFunctionObjArgs(
    self->feed, data, NULL);
  if(!result)
    goto error;
  Py_DECREF(result);
#else
  if(!Parser_feed(&self->parser, data))
    goto error;
#endif

  goto finally;

  error:
  return NULL;
  finally:
  Py_RETURN_NONE;
}

#ifdef PARSER_STANDALONE
static PyObject*
Protocol_on_headers(Protocol* self, PyObject *args)
{
  Py_RETURN_NONE;
}
#else
Protocol*
Protocol_on_headers(Protocol* self, char* method, size_t method_len,
                    char* path, size_t path_len, int minor_version,
                    void* headers, size_t num_headers)
{
  Protocol* result = self;

  Py_DECREF(self->request);
  self->request = PyObject_CallFunctionObjArgs(PyRequest, NULL);
  if(!self->request)
    goto error;

  request_capi->Request_from_raw(
    (Request*)self->request, method, method_len, path, path_len, minor_version,
    headers, num_headers);

  goto finally;

  error:
  result = NULL;

  finally:
  return result;
}
#endif


static inline Protocol* Protocol_write_response(Protocol* self, RESPONSE* response)
{
    Protocol* result = self;
    PyObject* memory_view = NULL;

    if(!(memory_view = response_capi->Response_render(response)))
      goto error;

    PyObject* tmp;
    if(!(tmp = PyObject_CallFunctionObjArgs(self->write, memory_view, NULL)))
      goto error;
    Py_DECREF(tmp);

    goto finally;

    error:
    result = NULL;

    finally:
    Py_XDECREF(memory_view);
    return result;
}


static PyObject* Protocol__done_callback(Protocol* self, PyObject* args)
{
  PyObject* result = Py_None;
  PyObject* future;
  PyObject* get_result = NULL;
  PyObject* response = NULL;
  if(!PyArg_ParseTuple(args, "O", &future))
    goto error;

  if(!(get_result = PyObject_GetAttrString(future, "result")))
    goto error;

  if(!(response = PyObject_CallFunctionObjArgs(get_result, NULL)))
    goto error;

  if(!Protocol_write_response(self, (RESPONSE*)response))
    goto error;

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(response);
  Py_XDECREF(get_result);
  if(result)
    Py_INCREF(result);
  return result;
}


static Protocol* Protocol_handle_coro(Protocol* self, PyObject* coro)
{
  Protocol* result = self;
  PyObject* task = NULL;
  PyObject* add_done_callback = NULL;

  if(!(task = PyObject_CallFunctionObjArgs(self->create_task, coro, NULL)))
    goto error;

  if(!(add_done_callback = PyObject_GetAttrString(task, "add_done_callback")))
    goto error;

  PyObject* tmp;
  if(!(tmp = PyObject_CallFunctionObjArgs(add_done_callback, self->done_callback, NULL)))
    goto error;
  Py_DECREF(tmp);

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(add_done_callback);
  Py_XDECREF(task);
  return result;
}


#ifdef PARSER_STANDALONE
static PyObject*
Protocol_on_body(Protocol* self, PyObject *args)
#else
Protocol*
Protocol_on_body(Protocol* self, char* body, size_t body_len)
#endif
{
#ifdef PARSER_STANDALONE
  PyObject* result = Py_None;
#else
  Protocol* result = self;
#endif
  PyObject* route = NULL; // stolen
  PyObject* handler = NULL; // stolen
  PyObject* handler_result = NULL;
#ifdef PARSER_STANDALONE
/*  PyObject* request;
  if(!PyArg_ParseTuple(args, "O", &request))
    goto error;
*/ // FIXME implement body setting
#endif

  route = matcher_capi->Matcher_match_request(
    (Matcher*)self->matcher, self->request, &handler);
  if(!route)
    goto error;

  if(route == Py_None)
    goto handle_error;

  handler_result = PyObject_CallFunctionObjArgs(handler, self->request, NULL);
  if(!handler_result)
    goto error;

  if(PyCoro_CheckExact(handler_result)) {
    if(!Protocol_handle_coro(self, handler_result))
      goto error;
  } else {
    if(!Protocol_write_response(self, (RESPONSE*)handler_result))
      goto error;
  }

  goto finally;

  handle_error:
  handler_result = PyObject_CallFunctionObjArgs(
    self->error_handler, self->request, NULL);
  if(!handler_result)
    goto error;

  if(!Protocol_write_response(self, (RESPONSE*)handler_result))
    goto error;

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(handler_result);
#ifdef PARSER_STANDALONE
  if(result)
    Py_INCREF(result);
#endif
  return result;
}

#ifdef PARSER_STANDALONE
static PyObject*
Protocol_on_error(Protocol* self, PyObject *args)
{
  Py_RETURN_NONE;
}
#else
Protocol*
Protocol_on_error(Protocol* self, PyObject* error)
{
  return self;
}
#endif


static PyMethodDef Protocol_methods[] = {
  {"connection_made", (PyCFunction)Protocol_connection_made, METH_VARARGS, ""},
  {"connection_lost", (PyCFunction)Protocol_connection_lost, METH_VARARGS, ""},
  {"data_received", (PyCFunction)Protocol_data_received, METH_VARARGS, ""},
#ifdef REAPER_ENABLED
  {"_check_idle", (PyCFunction)Protocol__check_idle, METH_NOARGS, ""},
#endif
  {"_done_callback", (PyCFunction)Protocol__done_callback, METH_VARARGS, ""},
#ifdef PARSER_STANDALONE
  {"on_headers", (PyCFunction)Protocol_on_headers, METH_VARARGS, ""},
  {"on_body", (PyCFunction)Protocol_on_body, METH_VARARGS, ""},
  {"on_error", (PyCFunction)Protocol_on_error, METH_VARARGS, ""},
#endif
  {NULL}
};


static PyTypeObject ProtocolType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "cprotocol.Protocol",      /* tp_name */
  sizeof(Protocol),          /* tp_basicsize */
  0,                         /* tp_itemsize */
  (destructor)Protocol_dealloc, /* tp_dealloc */
  0,                         /* tp_print */
  0,                         /* tp_getattr */
  0,                         /* tp_setattr */
  0,                         /* tp_reserved */
  0,                         /* tp_repr */
  0,                         /* tp_as_number */
  0,                         /* tp_as_sequence */
  0,                         /* tp_as_mapping */
  0,                         /* tp_hash  */
  0,                         /* tp_call */
  0,                         /* tp_str */
  0,                         /* tp_getattro */
  0,                         /* tp_setattro */
  0,                         /* tp_as_buffer */
  Py_TPFLAGS_DEFAULT,        /* tp_flags */
  "Protocol",                /* tp_doc */
  0,                         /* tp_traverse */
  0,                         /* tp_clear */
  0,                         /* tp_richcompare */
  0,                         /* tp_weaklistoffset */
  0,                         /* tp_iter */
  0,                         /* tp_iternext */
  Protocol_methods,          /* tp_methods */
  0,                         /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)Protocol_init,   /* tp_init */
  0,                         /* tp_alloc */
  Protocol_new,              /* tp_new */
};


static PyModuleDef cprotocol = {
  PyModuleDef_HEAD_INIT,
  "cprotocol",
  "cprotocol",
  -1,
  NULL, NULL, NULL, NULL, NULL
};


PyMODINIT_FUNC
PyInit_cprotocol(void)
{
  PyObject* m = NULL;
#ifdef PARSER_STANDALONE
  PyObject* cparser = NULL;
  Parser = NULL;
#endif
  PyObject* crequest = NULL;
#ifdef REAPER_ENABLED
  check_interval = NULL;
#endif

  if (PyType_Ready(&ProtocolType) < 0)
    goto error;

  m = PyModule_Create(&cprotocol);
  if(!m)
    goto error;

#ifdef PARSER_STANDALONE
  cparser = PyImport_ImportModule("parser.cparser");
  if(!cparser)
    goto error;

  Parser = PyObject_GetAttrString(cparser, "HttpRequestParser");
  if(!Parser)
    goto error;
#else
  if(cparser_init() == -1)
    goto error;
#endif

  crequest = PyImport_ImportModule("request.crequest");
  if(!crequest)
    goto error;

  PyRequest = PyObject_GetAttrString(crequest, "Request");
  if(!PyRequest)
    goto error;

  request_capi = import_capi("request.crequest");
  if(!request_capi)
    goto error;

  matcher_capi = import_capi("router.cmatcher");
  if(!matcher_capi)
    goto error;

  response_capi = import_capi("response.cresponse");
  if(!response_capi)
    goto error;

#ifdef REAPER_ENABLED
  check_interval = PyLong_FromLong(CHECK_INTERVAL);
  if(!check_interval)
    goto error;
#endif

  Py_INCREF(&ProtocolType);
  PyModule_AddObject(m, "Protocol", (PyObject*)&ProtocolType);

  goto finally;

  error:
#ifdef REAPER_ENABLED
  Py_XDECREF(check_interval);
#endif
  Py_XDECREF(PyRequest);
#ifdef PARSER_STANDALONE
  Py_XDECREF(Parser);
#endif
  m = NULL;
  finally:
  Py_XDECREF(crequest);
#ifdef PARSER_STANDALONE
  Py_XDECREF(cparser);
#endif
  return m;
}
