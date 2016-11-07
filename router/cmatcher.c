#include <Python.h>


typedef struct {
  PyObject_HEAD
} Matcher;


static PyObject *
Matcher_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
  Matcher* self = NULL;

  self = (Matcher*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  finally:
  return (PyObject*)self;
}


static void
Matcher_dealloc(Matcher* self)
{
  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Matcher_init(Matcher* self, PyObject *args, PyObject *kw)
{
  int result = 0;

  return result;
}


static PyObject*
Matcher_method(Matcher* self, PyObject* args)
{
  Py_RETURN_NONE;
}


static PyMethodDef Matcher_methods[] = {
  {"method", (PyCFunction)Matcher_method, METH_VARARGS, ""},
  {NULL}
};


static PyTypeObject MatcherType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "cmatcher.Matcher",      /* tp_name */
  sizeof(Matcher),          /* tp_basicsize */
  0,                         /* tp_itemsize */
  (destructor)Matcher_dealloc, /* tp_dealloc */
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
  "Matcher",                /* tp_doc */
  0,                         /* tp_traverse */
  0,                         /* tp_clear */
  0,                         /* tp_richcompare */
  0,                         /* tp_weaklistoffset */
  0,                         /* tp_iter */
  0,                         /* tp_iternext */
  Matcher_methods,          /* tp_methods */
  0,                         /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)Matcher_init,   /* tp_init */
  0,                         /* tp_alloc */
  Matcher_new,              /* tp_new */
};


static PyModuleDef cmatcher = {
  PyModuleDef_HEAD_INIT,
  "cmatcher",
  "cmatcher",
  -1,
  NULL, NULL, NULL, NULL, NULL
};


PyMODINIT_FUNC
PyInit_cmatcher(void)
{
  PyObject* m = NULL;

  if (PyType_Ready(&MatcherType) < 0)
    goto error;

  m = PyModule_Create(&cmatcher);
  if(!m)
    goto error;

  Py_INCREF(&MatcherType);
  PyModule_AddObject(m, "Matcher", (PyObject*)&MatcherType);

  goto finally;

  error:
  finally:
  return m;
}
