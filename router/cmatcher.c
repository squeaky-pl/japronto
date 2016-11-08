#include <Python.h>


typedef struct {
  PyObject_HEAD

  char* buffer;
  size_t buffer_len;
} Matcher;


typedef struct {
  PyObject* route;
  size_t pattern_len;
  size_t methods_len;
  char buffer[];
} MatcherEntry;


static PyObject *
Matcher_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
  Matcher* self = NULL;

  self = (Matcher*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  self->buffer = NULL;
  self->buffer_len = 0;

  finally:
  return (PyObject*)self;
}


static void
Matcher_dealloc(Matcher* self)
{
  if(self->buffer)
    free(self->buffer);

  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Matcher_compile(Matcher* self, PyObject* routes)
{
  int result = 0;

  // step 1 calculate memory needed
  if(!PyList_Check(routes))
      goto error;

  Py_ssize_t routes_len = PyList_GET_SIZE(routes);
  for(Py_ssize_t i = 0; i < routes_len; i++) {
      PyObject* pattern = NULL;
      PyObject* methods = NULL;

      self->buffer_len += sizeof(MatcherEntry);

      PyObject* route = PyList_GET_ITEM(routes, i);

      pattern = PyObject_GetAttrString(route, "pattern");
      if(!pattern)
        goto len_loop_error;

      Py_ssize_t pattern_len;
      if(!PyUnicode_AsUTF8AndSize(pattern, &pattern_len))
        goto len_loop_error;
      self->buffer_len += (size_t)pattern_len;

      methods = PyObject_GetAttrString(route, "methods");
      if(!methods)
        goto len_loop_error;

      if(!PyList_Check(methods))
        goto len_loop_error;

      Py_ssize_t methods_len = PyList_GET_SIZE(methods);
      for(Py_ssize_t j = 0; j < methods_len; j++) {
        PyObject* method = PyList_GET_ITEM(methods, j);

        Py_ssize_t method_len;
        if(!PyUnicode_AsUTF8AndSize(method, &method_len))
          goto len_loop_error;

        self->buffer_len += (size_t)method_len + 1;
      }

      goto len_loop_finally;

      len_loop_error:
      result = -1;
      len_loop_finally:
      Py_XDECREF(methods);
      Py_XDECREF(pattern);

      if(result == -1)
        goto finally;
  }

  // step 2: allocate and fill buffer
  self->buffer = malloc(self->buffer_len);
  if(!self->buffer)
    goto error;

  MatcherEntry* entry = (MatcherEntry*)self->buffer;
  for(Py_ssize_t i = 0; i < routes_len; i++) {
    PyObject* pattern = NULL;
    PyObject* methods = NULL;

    PyObject* route = PyList_GET_ITEM(routes, i);
    Py_INCREF(route);

    entry->route = route;

    pattern = PyObject_GetAttrString(route, "pattern");
    if(!pattern)
      goto cpy_loop_error;

    Py_ssize_t pattern_len;
    char* pattern_str = PyUnicode_AsUTF8AndSize(pattern, &pattern_len);
    if(!pattern_str)
      goto cpy_loop_error;

    entry->pattern_len = (size_t)pattern_len;
    memcpy(entry->buffer, pattern_str, (size_t)pattern_len);

    methods = PyObject_GetAttrString(route, "methods");
    if(!methods)
      goto cpy_loop_error;

    entry->methods_len = 0;
    char* methods_pos = entry->buffer + (size_t)pattern_len;
    Py_ssize_t methods_len = PyList_GET_SIZE(methods);
    for(Py_ssize_t j = 0; j < methods_len; j++) {
      PyObject* method = PyList_GET_ITEM(methods, j);

      Py_ssize_t method_len;
      char* method_str = PyUnicode_AsUTF8AndSize(method, &method_len);
      if(!method_str)
        goto cpy_loop_error;

      memcpy(methods_pos, method_str, (size_t)method_len);

      entry->methods_len += method_len;
      methods_pos += method_len;

      *methods_pos = ' ';
      entry->methods_len++;
      methods_pos++;
    }

    entry = (MatcherEntry*)methods_pos;

    goto cpy_loop_finally;

    cpy_loop_error:
    // FIXME: all the copied route objects leak
    result = 1;
    cpy_loop_finally:
    Py_XDECREF(methods);
    Py_XDECREF(pattern);

    if(result == -1)
      goto finally;
  }

  goto finally;

  error:
  result = -1;
  finally:
  return result;
}


static int
Matcher_init(Matcher* self, PyObject *args, PyObject *kw)
{
  int result = 0;

  PyObject* router;
  if(!PyArg_ParseTuple(args, "O", &router))
    goto error;

  PyObject* routes = PyObject_GetAttrString(router, "_routes");
  if(!routes)
    goto error;

  result = Matcher_compile(self, routes);

  goto finally;

  error:
  result = -1;
  finally:
  Py_XDECREF(routes);
  return result;
}


static PyObject*
Matcher_dump_buffer(Matcher* self, PyObject* args)
{
  PyObject* buffer = PyBytes_FromStringAndSize(self->buffer, self->buffer_len);
  if(!buffer)
    goto error;

  return buffer;

  error:
  return NULL;
}


static PyMethodDef Matcher_methods[] = {
  {"dump_buffer", (PyCFunction)Matcher_dump_buffer, METH_VARARGS, ""},
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
