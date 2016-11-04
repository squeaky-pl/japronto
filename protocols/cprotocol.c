#include <Python.h>


typedef struct {
  PyObject_HEAD
} Protocol;


static PyObject *
Protocol_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
  Protocol* self = NULL;

  self = (Protocol*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  finally:
  return (PyObject*)self;
}


static void
Protocol_dealloc(Protocol* self)
{
  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Protocol_init(Protocol* self, PyObject *args, PyObject *kw)
{
  goto finally;

  error:
  return -1;
  finally:
  return 0;
}


static PyObject*
Protocol_method(Protocol* self)
{
  Py_RETURN_NONE;
}


static PyMethodDef Protocol_methods[] = {
  {"method", (PyCFunction)Protocol_method, METH_NOARGS, "method"},
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

  if (PyType_Ready(&ProtocolType) < 0)
    goto error;

  m = PyModule_Create(&cprotocol);
  if(!m)
    goto error;

  Py_INCREF(&ProtocolType);
  PyModule_AddObject(m, "Protocol", (PyObject*)&ProtocolType);

  error:
  finally:
  return m;
}
