#include <Python.h>

#include "cprotocol.h"
#include "capsule.h"

typedef struct {
  PyObject_HEAD

  PyObject* connections;
  PyObject* call_later;
  PyObject* check_idle;
  PyObject* check_idle_handle;
} Reaper;

static Protocol_CAPI* protocol_capi;

const long CHECK_INTERVAL = 10;
const unsigned long IDLE_TIMEOUT = 60;

static PyObject* check_interval;

static PyObject*
Reaper_new(PyTypeObject* type, PyObject* args, PyObject* kwds)
{
  Reaper* self = NULL;

  self = (Reaper*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  self->connections = NULL;
  self->call_later = NULL;
  self->check_idle = NULL;
  self->check_idle_handle = NULL;

  finally:
  return (PyObject*)self;
}


static void
Reaper_dealloc(Reaper* self)
{
  Py_XDECREF(self->check_idle_handle);
  Py_XDECREF(self->check_idle);
  Py_XDECREF(self->call_later);
  Py_XDECREF(self->connections);

  Py_TYPE(self)->tp_free((PyObject*)self);
}

#ifdef REAPER_ENABLED
static inline void*
Reaper_schedule_check_idle(Reaper* self)
{
  Py_XDECREF(self->check_idle_handle);
  self->check_idle_handle = PyObject_CallFunctionObjArgs(
    self->call_later, check_interval, self->check_idle, NULL);

  return self->check_idle_handle;
}


static inline void*
Reaper_cancel_check_idle(Reaper* self)
{
  void* result = Py_None;
  PyObject* cancel = NULL;

  if(!(cancel = PyObject_GetAttrString(self->check_idle_handle, "cancel")))
    goto error;

  PyObject* tmp;
  if(!(tmp = PyObject_CallFunctionObjArgs(cancel, NULL)))
    goto error;
  Py_DECREF(tmp);

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(cancel);
  return result;
}
#endif


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

  if(!(self->connections = PyObject_GetAttrString(app, "_connections")))
    goto error;

#ifdef REAPER_ENABLED
  if(!(self->check_idle = PyObject_GetAttrString((PyObject*)self, "_check_idle")))
    goto error;

  if(!Reaper_schedule_check_idle(self))
    goto error;
#endif

  goto finally;

  error:
  result = -1;

  finally:
  Py_XDECREF(loop);
  return result;
}


#ifdef REAPER_ENABLED
static PyObject*
Reaper__check_idle(Reaper* self, PyObject* args)
{
  PyObject* result = Py_None;
  PyObject* iterator = NULL;
  Protocol* conn = NULL;

  if(!(iterator = PyObject_GetIter(self->connections)))
    goto error;

  while((conn = (Protocol*)PyIter_Next(iterator))) {
    if(conn->read_ops == conn->last_read_ops) {
      conn->idle_time += CHECK_INTERVAL;

      if(conn->idle_time >= IDLE_TIMEOUT) {
        if(!protocol_capi->Protocol_close(conn))
          goto error;
      }
    } else {
      conn->idle_time = 0;
      conn->last_read_ops = conn->read_ops;
    }

    Py_DECREF(conn);
  }

  if(!Reaper_schedule_check_idle(self))
    goto error;

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(conn);
  Py_XDECREF(iterator);
  Py_XINCREF(result);
  return result;
}


static PyMethodDef Reaper_methods[] = {
  {"_check_idle", (PyCFunction)Reaper__check_idle, METH_NOARGS, ""},
  {NULL}
};
#endif


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
#ifdef REAPER_ENABLED
  Reaper_methods,            /* tp_methods */
#else
  0,                         /* tp_methods */
#endif
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
  check_interval = NULL;

  if (PyType_Ready(&ReaperType) < 0)
    goto error;

  m = PyModule_Create(&creaper);
  if(!m)
    goto error;

  Py_INCREF(&ReaperType);
  PyModule_AddObject(m, "Reaper", (PyObject*)&ReaperType);

  if(!(check_interval = PyLong_FromLong(CHECK_INTERVAL)))
    goto error;

  protocol_capi = import_capi("protocol.cprotocol");
  if(!protocol_capi)
    goto error;

  goto finally;

  error:
  Py_XDECREF(check_interval);
  m = NULL;

  finally:
  return m;
}
