#include <Python.h>


static PyObject* Parser;
static PyObject* Response;

static PyObject* feed;
static PyObject* feed_disconnect;


typedef struct {
  PyObject_HEAD

  PyObject* parser;
  PyObject* loop;
  PyObject* handler;
  PyObject* response;
  PyObject* transport;
} Protocol;


static PyObject *
Protocol_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
  Protocol* self = NULL;

  self = (Protocol*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  self->parser = NULL;
  self->loop = NULL;
  self->handler = NULL;
  self->response = NULL;
  self->transport = NULL;

  finally:
  return (PyObject*)self;
}


static void
Protocol_dealloc(Protocol* self)
{
  Py_XDECREF(self->transport);
  Py_XDECREF(self->response);
  Py_XDECREF(self->handler);
  Py_XDECREF(self->loop);
  Py_XDECREF(self->parser);

  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Protocol_init(Protocol* self, PyObject *args, PyObject *kw)
{
  if(!PyArg_ParseTuple(args, "OO", &self->loop, &self->handler))
    goto error;
  Py_INCREF(self->loop);
  Py_INCREF(self->handler);

  PyObject* on_headers = PyObject_GetAttrString((PyObject*)self, "on_headers");
  if(!on_headers)
    goto error;
  PyObject* on_body = PyObject_GetAttrString((PyObject*)self, "on_body");
  if(!on_body)
    goto error;
  PyObject* on_error = PyObject_GetAttrString((PyObject*)self, "on_error");
  if(!on_error)
    goto error;

  self->parser = PyObject_CallFunctionObjArgs(
    Parser, on_headers, on_body, on_error, NULL);
  if(!self->parser)
    goto error;

  self->response = PyObject_CallFunctionObjArgs(Response, NULL);
  if(!self->response)
    goto error;

  goto finally;

  error:
  return -1;
  finally:
  return 0;
}


static PyObject*
Protocol_connection_made(Protocol* self, PyObject* args)
{
  if(!PyArg_ParseTuple(args, "O", &self->transport))
    goto error;
  Py_INCREF(self->transport);

  goto finally;

  error:
  return NULL;
  finally:
  Py_RETURN_NONE;
}


static PyObject*
Protocol_connection_lost(Protocol* self, PyObject* args)
{
  PyObject* result = PyObject_CallMethodObjArgs(
    self->parser, feed_disconnect, NULL);
  if(!result)
    goto error;
  Py_DECREF(result);

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

  PyObject* result = PyObject_CallMethodObjArgs(
    self->parser, feed, data, NULL);
  if(!result)
    goto error;
  Py_DECREF(result);

  goto finally;

  error:
  return NULL;
  finally:
  Py_RETURN_NONE;
}


static PyObject*
Protocol_on_headers(Protocol* self, PyObject *args)
{
  Py_RETURN_NONE;
}


static PyObject*
Protocol_on_body(Protocol* self, PyObject *args)
{
  PyObject* request;
  if(!PyArg_ParseTuple(args, "O", &request))
    goto error;

  PyObject* result = PyObject_CallFunctionObjArgs(
    self->handler, request, self->transport, self->response, NULL);
  if(!result)
    goto error;
  Py_DECREF(result);

  goto finally;

  error:
  return NULL;
  finally:
  Py_RETURN_NONE;
}


static PyObject*
Protocol_on_error(Protocol* self, PyObject *args)
{
  Py_RETURN_NONE;
}


static PyMethodDef Protocol_methods[] = {
  {"connection_made", (PyCFunction)Protocol_connection_made, METH_VARARGS, ""},
  {"connection_lost", (PyCFunction)Protocol_connection_lost, METH_VARARGS, ""},
  {"data_received", (PyCFunction)Protocol_data_received, METH_VARARGS, ""},
  {"on_headers", (PyCFunction)Protocol_on_headers, METH_VARARGS, ""},
  {"on_body", (PyCFunction)Protocol_on_body, METH_VARARGS, ""},
  {"on_error", (PyCFunction)Protocol_on_error, METH_VARARGS, ""},
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
  PyObject* impl_cext = NULL;
  Parser = NULL;
  PyObject* cresponse = NULL;
  Response = NULL;
  feed = NULL;
  feed_disconnect = NULL;

  if (PyType_Ready(&ProtocolType) < 0)
    goto error;

  m = PyModule_Create(&cprotocol);
  if(!m)
    goto error;

  impl_cext = PyImport_ImportModule("impl_cext");
  if(!impl_cext)
    goto error;

  Parser = PyObject_GetAttrString(impl_cext, "HttpRequestParser");
  if(!Parser)
    goto error;

  cresponse = PyImport_ImportModule("responses.cresponse");
  if(!cresponse)
    goto error;

  Response = PyObject_GetAttrString(cresponse, "Response");
  if(!Response)
    goto error;

  Py_INCREF(&ProtocolType);
  PyModule_AddObject(m, "Protocol", (PyObject*)&ProtocolType);

  feed = PyUnicode_FromString("feed");
  if(!feed)
    goto error;

  feed_disconnect = PyUnicode_FromString("feed_disconnect");
  if(!feed_disconnect)
    goto error;

  goto finally;

  error:
  Py_XDECREF(feed_disconnect);
  Py_XDECREF(feed);
  Py_XDECREF(Response);
  Py_XDECREF(Parser);
  finally:
  Py_XDECREF(cresponse);
  Py_XDECREF(impl_cext);
  return m;
}
