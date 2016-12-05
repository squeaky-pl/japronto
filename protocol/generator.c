#include <Python.h>


typedef struct {
  PyObject_HEAD

  PyObject* object;
} Generator;


static PyObject*
Generator_new(PyTypeObject* type, PyObject* args, PyObject* kw)
{
  Generator* self = NULL;

  self = (Generator*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  self->object = NULL;

  finally:
  return (PyObject*)self;
}


static void
Generator_dealloc(Generator* self)
{
  Py_XDECREF(self->object);

  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Generator_init(Generator* self, PyObject *args, PyObject *kw)
{
  int result = 0;

  if(!PyArg_ParseTuple(args, "O", &self->object))
    goto error;

  Py_INCREF(self->object);

  goto finally;

  error:
  result = -1;
  finally:
  return result;
}


static PyObject*
Generator_next(Generator* self)
{
  PyErr_SetObject(PyExc_StopIteration, self->object);

  return NULL;
}


static PyTypeObject GeneratorType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "protocol.Generator",      /* tp_name */
  sizeof(Generator),          /* tp_basicsize */
  0,                         /* tp_itemsize */
  (destructor)Generator_dealloc, /* tp_dealloc */
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
  "Generator",                /* tp_doc */
  0,                         /* tp_traverse */
  0,                         /* tp_clear */
  0,                         /* tp_richcompare */
  0,                         /* tp_weaklistoffset */
  PyObject_SelfIter,         /* tp_iter */
  (iternextfunc)Generator_next, /* tp_iternext */
  0,                         /* tp_methods */
  0,                         /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)Generator_init,  /* tp_init */
  0,                         /* tp_alloc */
  Generator_new,             /* tp_new */
};


static PyModuleDef generator = {
  PyModuleDef_HEAD_INIT,
  "generator",
  "generator",
  -1,
  NULL, NULL, NULL, NULL, NULL
};


PyMODINIT_FUNC
PyInit_generator(void)
{
  PyObject* m = NULL;

  if(PyType_Ready(&GeneratorType) < 0)
    goto error;

  m = PyModule_Create(&generator);
  if(!m)
    goto error;

  Py_INCREF(&GeneratorType);
  PyModule_AddObject(m, "Generator", (PyObject*)&GeneratorType);


  goto finally;

  error:
  m = NULL;

  finally:
  return m;
}
