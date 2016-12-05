#include <Python.h>

#include "generator.h"


typedef struct _Generator {
  PyObject_HEAD

  PyObject* object;
} Generator;


static PyTypeObject GeneratorType;


#ifdef GENERATOR_OPAQUE
static PyObject*
Generator_new(PyTypeObject* type, PyObject* args, PyObject* kw)
#else
PyObject*
Generator_new(void)
#endif
{
  Generator* self = NULL;

#ifdef GENERATOR_OPAQUE
  self = (Generator*)type->tp_alloc(type, 0);
#else
  self = (Generator*)GeneratorType.tp_alloc(&GeneratorType, 0);
#endif
  if(!self)
    goto finally;

  self->object = NULL;

  finally:
  return (PyObject*)self;
}


#ifdef GENERATOR_OPAQUE
static void
#else
void
#endif
Generator_dealloc(Generator* self)
{
  Py_XDECREF(self->object);

  Py_TYPE(self)->tp_free((PyObject*)self);
}


#ifdef GENERATOR_OPAQUE
static int
Generator_init(Generator* self, PyObject *args, PyObject *kw)
#else
int
Generator_init(Generator* self, PyObject* object)
#endif
{
  int result = 0;

#ifdef GENERATOR_OPAQUE
  if(!PyArg_ParseTuple(args, "O", &self->object))
    goto error;
#else
  self->object = object;
#endif

  Py_INCREF(self->object);

  goto finally;

#ifdef GENERATOR_OPAQUE
  error:
  result = -1;
#endif
  finally:
  return result;
}


static PyObject*
Generator_next(Generator* self)
{
  PyErr_SetObject(PyExc_StopIteration, self->object);

  return NULL;
}


static PyObject*
Generator_send(Generator* self, PyObject* arg)
{
  return Generator_next(self);
}


static PyMethodDef Generator_methods[] = {
  {"send", (PyCFunction)Generator_send, METH_O, ""},
  {NULL}
};


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
  Generator_methods,         /* tp_methods */
#ifdef GENERATOR_OPAQUE
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
#endif
};


#ifdef GENERATOR_OPAQUE
static PyModuleDef generator = {
  PyModuleDef_HEAD_INIT,
  "generator",
  "generator",
  -1,
  NULL, NULL, NULL, NULL, NULL
};
#endif


#ifdef GENERATOR_OPAQUE
PyMODINIT_FUNC
PyInit_generator(void)
#else
void*
generator_init(void)
#endif
{
#ifdef GENERATOR_OPAQUE
  PyObject* m = NULL;
#else
  void* m = &GeneratorType;
#endif

  if(PyType_Ready(&GeneratorType) < 0)
    goto error;

#ifdef GENERATOR_OPAQUE
  m = PyModule_Create(&generator);
  if(!m)
    goto error;

  Py_INCREF(&GeneratorType);
  PyModule_AddObject(m, "Generator", (PyObject*)&GeneratorType);
#endif

  goto finally;

  error:
  m = NULL;

  finally:
  return m;
}
