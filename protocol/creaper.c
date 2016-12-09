#include <Python.h>


typedef struct {
  PyObject_HEAD

  PyObject* connections;
  PyObject* call_later;
} Reaper;


static PyObject*
Reaper_new(PyTypeObject* type, PyObject* args, PyObject* kwds)
{
  Reaper* self = NULL;

  self = (Reaper*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  self->connections = NULL;
  self->call_later = NULL;

  finally:
  return (PyObject*)self;
}


static void
Reaper_dealloc(Reaper* self)
{
  Py_XDECREF(self->call_later);
  Py_XDECREF(self->connections);

  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Reaper_init(Reaper* self, PyObject* args, PyObject* kwds)
{
  PyObject* loop = NULL;
  int result = 0;

  PyObject* app;
  if(!PyArg_ParseTuple(args, "O", &app))
    goto error;

  if(!(loop = PyObject_GetAttrString(app, "_loop")))
    goto error;

  if(!(self->call_later = PyObject_GetAttrString(loop, "call_later")))
    goto error;
  Py_INCREF(self->call_later);

  if(!(self->connections = PyObject_GetAttrString(app, "_connections")))
    goto error;
  Py_INCREF(self->connections);

  goto finally;

  error:
  result = -1;

  finally:
  Py_XDECREF(loop);
  return result;
}


static PyTypeObject ReaperType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "creaper.Reaper",          /* tp_name */
  sizeof(Reaper),            /* tp_basicsize */
  0,                         /* tp_itemsize */
  (destructor)Reaper_dealloc, /* tp_dealloc */
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
  "Reaper",                  /* tp_doc */
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
  (initproc)Reaper_init,     /* tp_init */
  0,                         /* tp_alloc */
  Reaper_new,                /* tp_new */
};


static PyModuleDef creaper = {
  PyModuleDef_HEAD_INIT,
  "creaper",
  "creaper",
  -1,
  NULL, NULL, NULL, NULL, NULL
};


PyMODINIT_FUNC
PyInit_creaper(void)
{
  PyObject* m = NULL;

  if (PyType_Ready(&ReaperType) < 0)
    goto error;

  m = PyModule_Create(&creaper);
  if(!m)
    goto error;

  Py_INCREF(&ReaperType);
  PyModule_AddObject(m, "Reaper", (PyObject*)&ReaperType);

  goto finally;

  error:
  m = NULL;

  finally:
  return m;
}
