#include <Python.h>
#include "structmember.h"

#include "cpipeline.h"

static PyTypeObject PipelineType;

#ifdef PIPELINE_OPAQUE
static PyObject*
Pipeline_new(PyTypeObject* type, PyObject* args, PyObject* kw)
#else
PyObject*
Pipeline_new(Pipeline* self)
#endif
{
#ifdef PIPELINE_OPAQUE
  Pipeline* self = NULL;

  self = (Pipeline*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;
#else
  ((PyObject*)self)->ob_refcnt = 1;
  ((PyObject*)self)->ob_type = &PipelineType;
#endif

  self->ready = NULL;
  self->task_done = NULL;

#ifdef PIPELINE_OPAQUE
  finally:
#endif
  return (PyObject*)self;
}

#ifdef PIPELINE_OPAQUE
static void
#else
void
#endif
Pipeline_dealloc(Pipeline* self)
{
#ifdef PIPELINE_OPAQUE
  Py_XDECREF(self->ready);
#endif
  Py_XDECREF(self->task_done);

#ifdef PIPELINE_OPAQUE
  Py_TYPE(self)->tp_free((PyObject*)self);
#endif
}

#ifdef PIPELINE_OPAQUE
static int
Pipeline_init(Pipeline* self, PyObject *args, PyObject* kw)
#else
int
Pipeline_init(Pipeline* self, void* (*ready)(PipelineEntry, PyObject*), PyObject* protocol)
#endif
{
  int result = 0;

#ifdef PIPELINE_OPAQUE
  if(!PyArg_ParseTuple(args, "O", &self->ready))
    goto error;

  Py_INCREF(self->ready);
#else
  self->ready = ready;
  self->protocol = protocol;
#endif

  if(!(self->task_done = PyObject_GetAttrString((PyObject*)self, "_task_done")))
    goto error;

  self->queue_start = 0;
  self->queue_end = 0;

  goto finally;

  error:
  result = -1;

  finally:
  return result;
}


static PyObject*
Pipeline__task_done(Pipeline* self, PyObject* task)
{
  PyObject* result = Py_True;

  PipelineEntry *queue_entry;
  for(queue_entry = self->queue + self->queue_start;
      queue_entry < self->queue + self->queue_end; queue_entry++) {
    PyObject* done = NULL;
    PyObject* done_result = NULL;
    result = Py_True;

    if(PipelineEntry_is_task(*queue_entry)) {
      task = PipelineEntry_get_task(*queue_entry);

      if(!(done = PyObject_GetAttrString(task, "done")))
        goto loop_error;

      if(!(done_result = PyObject_CallFunctionObjArgs(done, NULL)))
        goto loop_error;

      if(done_result == Py_False) {
        result = Py_False;
        goto loop_finally;
      }
    }

#ifdef PIPELINE_OPAQUE
    PyObject* tmp;
    if(!(tmp = PyObject_CallFunctionObjArgs(self->ready, *queue_entry, NULL)))
      goto loop_error;
    Py_DECREF(tmp);
#else
    if(!self->ready(*queue_entry, self->protocol))
      goto loop_error;
#endif

    PipelineEntry_DECREF(*queue_entry);

    goto loop_finally;

    loop_error:
    result = NULL;

    loop_finally:
    Py_XDECREF(done_result);
    Py_XDECREF(done);
    if(!result)
      goto error;
    if(result == Py_False)
      break;
  }

  self->queue_start = queue_entry - self->queue;

#ifndef PIPELINE_OPAQUE
  if(PIPELINE_EMPTY(self))
    // we became empty so release protocol
    Py_DECREF(self->protocol);
#endif

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XINCREF(result);
  return result;
}

#ifdef PIPELINE_OPAQUE
static PyObject*
#else
PyObject*
#endif
Pipeline_queue(Pipeline* self, PipelineEntry entry)
{
  PyObject* result = Py_None;
  PyObject* add_done_callback = NULL;

  if(PIPELINE_EMPTY(self)) {
    self->queue_start = self->queue_end = 0;
#ifndef PIPELINE_OPAQUE
    // we will become non empty so hold a reference to protocol
    Py_INCREF(self->protocol);
#endif
  }

  assert(self->queue_end < sizeof(self->queue) / sizeof(self->queue[0]));

  PipelineEntry* queue_entry = self->queue + self->queue_end;
  *queue_entry = entry;
  PipelineEntry_INCREF(*queue_entry);

  self->queue_end++;

  if(PipelineEntry_is_task(entry)) {
    PyObject* task = PipelineEntry_get_task(entry);
    if(!(add_done_callback = PyObject_GetAttrString(task, "add_done_callback")))
      goto error;

    PyObject* tmp;
    if(!(tmp = PyObject_CallFunctionObjArgs(add_done_callback, self->task_done, NULL)))
      goto error;
    Py_DECREF(tmp);
  }

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(add_done_callback);
#ifdef PIPELINE_OPAQUE
  Py_XINCREF(result);
#endif
  return result;
}


#ifndef PIPELINE_OPAQUE
void*
Pipeline_cancel(Pipeline* self)
{
  void* result = self;

  PipelineEntry *queue_entry;
  for(queue_entry = self->queue + self->queue_start;
      queue_entry < self->queue + self->queue_end; queue_entry++) {
    if(!PipelineEntry_is_task(*queue_entry))
      continue;

    PyObject* task = PipelineEntry_get_task(*queue_entry);
    PyObject* cancel = NULL;

    if(!(cancel = PyObject_GetAttrString(task, "cancel")))
      goto loop_error;

    PyObject* tmp;
    if(!(tmp = PyObject_CallFunctionObjArgs(cancel, NULL)))
      goto loop_error;
    Py_DECREF(tmp);

    goto loop_finally;

    loop_error:
    result = NULL;

    loop_finally:
    Py_XDECREF(cancel);

    if(!result)
      break;
  }

  return result;
}
#endif


#ifdef PIPELINE_OPAQUE
static PyObject*
Pipeline_get_empty(Pipeline* self, void* closure) {
  PyObject* result = PIPELINE_EMPTY(self) ? Py_True : Py_False;

  Py_INCREF(result);
  return result;
}
#endif

static PyMethodDef Pipeline_methods[] = {
#ifdef PIPELINE_OPAQUE
  {"queue", (PyCFunction)Pipeline_queue, METH_O, ""},
#endif
  {"_task_done", (PyCFunction)Pipeline__task_done, METH_O, ""},
  {NULL}
};

#ifdef PIPELINE_OPAQUE
static PyGetSetDef Pipeline_getset[] = {
  {"empty", (getter)Pipeline_get_empty, NULL, "", NULL},
  {NULL}
};
#endif


static PyTypeObject PipelineType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "cpipeline.Pipeline",       /* tp_name */
  sizeof(Pipeline),           /* tp_basicsize */
  0,                         /* tp_itemsize */
#ifdef PIPELINE_OPAQUE
  (destructor)Pipeline_dealloc, /* tp_dealloc */
#else
  0,                         /* tp_dealloc */
#endif
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
#ifdef PIPELINE_OPAQUE
  Pipeline_getset,           /* tp_getset */
#else
  0,                         /* tp_getset */
#endif
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
#ifdef PIPELINE_OPAQUE
  (initproc)Pipeline_init,   /* tp_init */
#else
  0,                         /* tp_init */
#endif
  0,                         /* tp_alloc */
#ifdef PIPELINE_OPAQUE
  Pipeline_new,              /* tp_new */
#else
  0,                         /* tp_new */
#endif
};

#ifdef PIPELINE_OPAQUE
static PyModuleDef cpipeline = {
  PyModuleDef_HEAD_INIT,
  "cpipeline",
  "cpipeline",
  -1,
  NULL, NULL, NULL, NULL, NULL
};
#endif


#ifdef PIPELINE_OPAQUE
PyMODINIT_FUNC
PyInit_cpipeline(void)
#else
void*
cpipeline_init(void)
#endif
{
#ifdef PIPELINE_OPAQUE
  PyObject* m = NULL;
#else
  void* m = &PipelineType;
#endif

  if(PyType_Ready(&PipelineType) < 0)
    goto error;

#ifdef PIPELINE_OPAQUE
  if(!(m = PyModule_Create(&cpipeline)))
    goto error;

  Py_INCREF(&PipelineType);
  PyModule_AddObject(m, "Pipeline", (PyObject*)&PipelineType);
#endif

  goto finally;

  error:
  m = NULL;

  finally:
  return m;
}
