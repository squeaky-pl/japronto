#include "crequest.h"


static PyObject*
Request_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
  Request* self = NULL;

  self = (Request*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  self->method_len = 0;
  self->path_len = 0;
  self->method = NULL;
  self->path = NULL;
  self->version = NULL;
  self->headers = NULL;
  self->body = NULL;

  finally:
  return (PyObject*)self;
}


static void
Request_dealloc(Request* self)
{
  Py_XDECREF(self->body);
  Py_XDECREF(self->headers);
  Py_XDECREF(self->version);
  Py_XDECREF(self->path);
  Py_XDECREF(self->method);
  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Request_init(Request* self, PyObject *args, PyObject* kw)
{
  return 0;
}

static PyObject*
Request_getattr(Request* self, char* name)
{
  PyObject* result;
  if(strcmp(name, "method") == 0) {
    if(!self->method) {
      self->method = PyUnicode_FromStringAndSize(
        REQUEST_METHOD(self), self->method_len);
      if(!self->method)
        goto error;
    }

    result = self->method;
    goto finally;
  }

  if(strcmp(name, "path") == 0) {
    if(!self->path) {
      self->path = PyUnicode_FromStringAndSize(
        REQUEST_PATH(self), self->path_len);
      if(!self->path)
        goto error;
    }

    result = self->path;
    goto finally;
  }

  if(strcmp(name, "version") == 0) {
    result = self->version;
    goto finally;
  }

  if(strcmp(name, "headers") == 0) {
    result = self->headers;
    goto finally;
  }

  if(strcmp(name, "body") == 0) {
    result = self->body;
    goto finally;
  }

  error:
  result = NULL;
  finally:
  if(result)
    Py_INCREF(result);
  return result;
}


static PyTypeObject RequestType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "crequest.Request",      /* tp_name */
  sizeof(Request),          /* tp_basicsize */
  0,                         /* tp_itemsize */
  (destructor)Request_dealloc, /* tp_dealloc */
  0,                         /* tp_print */
  (getattrfunc)Request_getattr, /* tp_getattr */
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
  "Request",                /* tp_doc */
  0,                         /* tp_traverse */
  0,                         /* tp_clear */
  0,                         /* tp_richcompare */
  0,                         /* tp_weaklistoffset */
  0,                         /* tp_iter */
  0,                         /* tp_iternext */
  0,                         /* tp_methods */
  0,                         /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)Request_init,    /* tp_init */
  0,                         /* tp_alloc */
  Request_new,              /* tp_new */
};


static PyModuleDef crequest = {
  PyModuleDef_HEAD_INIT,
  "crequest",
  "crequest",
  -1,
  NULL, NULL, NULL, NULL, NULL
};


PyMODINIT_FUNC
PyInit_crequest(void)
{
  PyObject* m = NULL;

  if (PyType_Ready(&RequestType) < 0)
    goto error;

  m = PyModule_Create(&crequest);
  if(!m)
    goto error;

  Py_INCREF(&RequestType);
  PyModule_AddObject(m, "Request", (PyObject*)&RequestType);

  goto finally;

  error:
  finally:
  return m;
}
