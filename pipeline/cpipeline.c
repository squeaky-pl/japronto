#include <Python.h>

typedef struct {
  PyObject_HEAD
} Pipeline;


static PyObject*
Pipeline_new(PyTypeObject * type, PyObject* args, PyObject* kw)
{
  Pipeline* self = NULL;

  self = (Pipeline*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  finally:
  return (PyObject*)self;
}


static void
Pipeline_dealloc(Pipeline* self)
{
  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Pipeline_init(Pipeline* self, PyObject *args, PyObject* kw)
{
  int result = 0;

  goto finally;

  error:
  result = -1;

  finally:
  return result;
}


static PyMethodDef Pipeline_methods[] = {
  {NULL}
};


static PyTypeObject PipelineType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "cpipeline.Pipeline",       /* tp_name */
  sizeof(Pipeline),           /* tp_basicsize */
  0,                         /* tp_itemsize */
  (destructor)Pipeline_dealloc, /* tp_dealloc */
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
  "Pipeline",                /* tp_doc */
  0,                         /* tp_traverse */
  0,                         /* tp_clear */
  0,                         /* tp_richcompare */
  0,                         /* tp_weaklistoffset */
  0,                         /* tp_iter */
  0,                         /* tp_iternext */
  Pipeline_methods,          /* tp_methods */
  0,                         /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)Pipeline_init,    /* tp_init */
  0,                         /* tp_alloc */
  Pipeline_new,              /* tp_new */
};


static PyModuleDef cpipeline = {
  PyModuleDef_HEAD_INIT,
  "cpipeline",
  "cpipeline",
  -1,
  NULL, NULL, NULL, NULL, NULL
};


PyMODINIT_FUNC
PyInit_cpipeline(void)
{
  PyObject* m = NULL;

  if(PyType_Ready(&PipelineType) < 0)
    goto error;

  if(!(m = PyModule_Create(&cpipeline)))
    goto error;

  Py_INCREF(&PipelineType);
  PyModule_AddObject(m, "Pipeline", (PyObject*)&PipelineType);

  goto finally;

  error:
  m = NULL;

  finally:
  return m;
}
