#include <Python.h>

typedef struct {
  PyObject_HEAD
  PyObject* tail;
  PyObject* results;
} Pipeline;


static PyObject*
Pipeline_new(PyTypeObject * type, PyObject* args, PyObject* kw)
{
  Pipeline* self = NULL;

  self = (Pipeline*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  self->tail = NULL;
  self->results = NULL;

  finally:
  return (PyObject*)self;
}


static void
Pipeline_dealloc(Pipeline* self)
{
  Py_XDECREF(self->results);
  Py_XDECREF(self->tail);

  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Pipeline_init(Pipeline* self, PyObject *args, PyObject* kw)
{
  int result = 0;

  self->tail = Py_None;
  Py_INCREF(self->tail);

  if(!(self->results = PyList_New(0)))
    goto error;

  goto finally;

  error:
  result = -1;

  finally:
  return result;
}


static inline Pipeline*
Pipeline_write(Pipeline* self, PyObject* task)
{
  Pipeline* result = self;

  PyObject* result_func = NULL;
  if(!(result_func = PyObject_GetAttrString(task, "result")))
    goto error;

  PyObject* result_val = NULL;
  if(!(result_val = PyObject_CallFunctionObjArgs(result_func, NULL)))
    goto error;

  if(PyList_Append(self->results, result_val) == -1)
    goto error;

  if(PyObject_SetAttrString(task, "_written", Py_True) == -1)
    goto error;

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(result_func);
  Py_XDECREF(result_val);
  return result;
}


static inline void*
Pipeline_resolve_dependency(Pipeline* self, PyObject* task)
{
  void* result = Py_None;
  PyObject* current = NULL;

  if(!(current = PyObject_GetAttrString(task, "_depends_on")))
    goto error;

  while(current != Py_None) {
    PyObject* done = NULL;

    if(!(done = PyObject_GetAttrString(current, "done")))
      goto loop_error;

    PyObject* done_result = NULL;
    if(!(done_result = PyObject_CallFunctionObjArgs(done, NULL)))
      goto loop_error;

    if(done_result != Py_True) {
      result = Py_True;
      goto loop_finally;
    }

    Py_DECREF(current);
    if(!(current = PyObject_GetAttrString(current, "_depends_on")))
      goto loop_error;

    goto loop_finally;

    loop_error:
    result = NULL;

    loop_finally:
    Py_XDECREF(done_result);
    Py_XDECREF(done);
    if(!result)
      goto error;
    if(result == Py_True)
      break;
  }

  if(PyObject_SetAttrString(task, "_depends_on", current) == -1)
    goto error;

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(current);
  return result;
}


static inline void*
Pipeline_gc(Pipeline* self)
{
  void* result = Py_None;

  while(self->tail != Py_None) {
    PyObject* written = NULL;
    if(!(written = PyObject_GetAttrString(self->tail, "_written")))
      goto loop_error;

    if(written == Py_False) {
      result = Py_True;
      goto loop_finally;
    }

    Py_DECREF(self->tail);
    if(!(self->tail = PyObject_GetAttrString(self->tail, "_depends_on")))
      goto loop_error;

    goto loop_finally;

    loop_error:
    result = NULL;

    loop_finally:
    Py_XDECREF(written);
    if(!result)
      goto error;
    if(result == Py_True)
      break;
  }

  goto finally;

  error:
  result = NULL;

  finally:
  return result;
}


static inline PyObject*
Pipeline_task_done(Pipeline* self, PyObject* this_task, PyObject* task)
{
    PyObject* result = Py_False;
    if(this_task) {
      PyObject* depends_on = NULL;
      if(!(depends_on = PyObject_GetAttrString(task, "_depends_on")))
        goto write_error;
      if(depends_on == Py_None)
        goto write;

      PyObject* written = NULL;
      if(!(written = PyObject_GetAttrString(depends_on, "_written")))
        goto write_error;
      if(written != Py_True)
        goto write_finally;

      write:
      if(!Pipeline_write(self, task))
        goto write_error;

      result = Py_True;
      goto write_finally;

      write_error:
      result = NULL;

      write_finally:
      Py_XDECREF(written);
      Py_XDECREF(depends_on);

      if(!result)
        goto error;
      if(result == Py_True)
        goto finally;
    }

    if(!Pipeline_resolve_dependency(self, task))
      goto error;

    if(!Pipeline_gc(self))
      goto error;

    goto finally;

    error:
    result = NULL;

    finally:
    return result;
}


static PyObject*
Pipeline_queue(Pipeline* self, PyObject* task)
{
  PyObject* result = Py_None;

  if(PyObject_SetAttrString(task, "_depends_on", self->tail) == -1)
    goto error;

  if(PyObject_SetAttrString(task, "_written", Py_False) == -1)
    goto error;

  self->tail = task;
  Py_INCREF(self->tail);

  if(!Pipeline_task_done(self, NULL, task))
    goto error;

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XINCREF(result);
  return result;
}


static PyMethodDef Pipeline_methods[] = {
  {"queue", (PyCFunction)Pipeline_queue, METH_O, ""},
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
