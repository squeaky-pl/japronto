#include <Python.h>

#include "cmatcher.h"
#include "crequest.h"
#include "capsule.h"


struct _Matcher {
  PyObject_HEAD

  size_t buffer_len;
  char* buffer;
};


typedef struct {
  PyObject* route;
  PyObject* handler;
  size_t pattern_len;
  size_t methods_len;
  char buffer[];
} MatcherEntry;


typedef enum {
  SEGMENT_EXACT,
  SEGMENT_PLACEHOLDER
} SegmentType;


typedef struct {
  size_t data_length;
  char data[];
} ExactSegment;


typedef struct {
  size_t name_length;
  char name[];
} PlaceholderSegment;


typedef struct {
  SegmentType type;

  union {
    ExactSegment exact;
    PlaceholderSegment placeholder;
  };
} Segment;

static Request_CAPI* request_capi;
static PyObject* compile_all;

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


#define ENTRY_LOOP \
char* entry_end = self->buffer + self->buffer_len; \
for(MatcherEntry* entry = (MatcherEntry*)self->buffer; \
    (char*)entry < entry_end; \
    entry = (MatcherEntry*)((char*)entry + sizeof(MatcherEntry) + \
      entry->pattern_len + entry->methods_len))

#define SEGMENT_LOOP \
char* segments_end = entry->buffer + entry->pattern_len; \
for(Segment* segment = (Segment*)entry->buffer; \
    (char*)segment < segments_end; \
    segment = (Segment*)((char*)segment + sizeof(Segment) + \
      (segment->type == SEGMENT_EXACT ? \
        segment->exact.data_length : segment->placeholder.name_length)))


static void
Matcher_dealloc(Matcher* self)
{
  if(self->buffer) {
    ENTRY_LOOP {
      Py_DECREF(entry->handler);
      Py_DECREF(entry->route);
    }
    free(self->buffer);
  }

  Py_TYPE(self)->tp_free((PyObject*)self);
}


static int
Matcher_init(Matcher* self, PyObject *args, PyObject *kw)
{
  int result = 0;
  PyObject* compiled = NULL;

  PyObject* routes;
  if(!PyArg_ParseTuple(args, "O", &routes))
    goto error;

  if(!(compiled = PyObject_CallFunctionObjArgs(compile_all, routes, NULL)))
    goto error;

  char* compiled_buffer;
  if(PyBytes_AsStringAndSize(compiled, &compiled_buffer, (Py_ssize_t*)&self->buffer_len) == -1)
    goto error;

  if(!(self->buffer = malloc(self->buffer_len)))
    goto error;

  memcpy(self->buffer, compiled_buffer, self->buffer_len);

  ENTRY_LOOP {
    Py_INCREF(entry->handler);
    Py_INCREF(entry->route);
  }

  goto finally;

  error:
  result = -1;
  finally:
  Py_XDECREF(compiled);
  return result;
}

// borrows route and handler
PyObject* Matcher_match_request(Matcher* self, PyObject* request, PyObject** handler)
{
  PyObject* route = Py_None;
#if 0
  PyObject* path = NULL;
  PyObject* method = NULL;

  path = PyObject_GetAttrString(request, "path");
  if(!path)
    goto error;

  Py_ssize_t path_len;
  char* path_str = PyUnicode_AsUTF8AndSize(path, &path_len);
  if(!path_str)
    goto error;

  method = PyObject_GetAttrString(request, "method");
  if(!method)
    goto error;

  Py_ssize_t method_len;
  char* method_str = PyUnicode_AsUTF8AndSize(method, &method_len);
  if(!method_str)
    goto error;
#else
  size_t method_len = REQUEST(request)->method_len;
  char* method_str = REQUEST_METHOD(request);
  size_t path_len;
  char* path_str = request_capi->Request_get_decoded_path(
    REQUEST(request), &path_len);
#endif

  ENTRY_LOOP {
    char* rest = path_str;
    size_t rest_len = path_len;

    SEGMENT_LOOP {
      if(segment->type == SEGMENT_EXACT) {
        if(rest_len < segment->exact.data_length)
          break;

        if(memcmp(rest, segment->exact.data, segment->exact.data_length) != 0)
          break;

        rest += segment->exact.data_length;
        rest_len -= segment->exact.data_length;
      } else if(segment->type == SEGMENT_PLACEHOLDER) {
        char* slash = memchr(rest, '/', rest_len);
        if(slash) {
          rest_len -= slash - rest;
          rest = slash;
        } else {
          rest_len = 0;
        }
      } else {
        assert(0);
      }
    }

    if(rest_len)
      continue;

    if(!entry->methods_len)
      goto loop_finally;

    char* method_found = memmem(
      entry->buffer + entry->pattern_len, entry->methods_len,
      method_str, (size_t)method_len);
    if(!method_found)
      continue;

    if(*(method_found + (size_t)method_len) != ' ')
      continue;

    loop_finally:
    route = entry->route;
    if(handler)
      *handler = entry->handler;
    goto finally;
  }

  goto finally;

#if 0
  error:
  route = NULL;
#endif
  finally:
#if 0
  Py_XDECREF(method);
  Py_XDECREF(path);
#endif
  return route;
}


static PyObject*
_Matcher_match_request(Matcher* self, PyObject* args)
{
  PyObject* route;
  PyObject* request;

  if(!PyArg_ParseTuple(args, "O", &request))
    goto error;

  route = Matcher_match_request(self, request, NULL);

  goto finally;

  error:
  route = NULL;
  finally:
  if(route)
    Py_INCREF(route);
  return route;
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
  {"match_request", (PyCFunction)_Matcher_match_request, METH_VARARGS, ""},
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
  PyObject* api_capsule = NULL;
  PyObject* router_route = NULL;

  if (PyType_Ready(&MatcherType) < 0)
    goto error;

  m = PyModule_Create(&cmatcher);
  if(!m)
    goto error;

  request_capi = import_capi("request.crequest");
  if(!request_capi)
    goto error;

  if(!(router_route = PyImport_ImportModule("router.route")))
    goto error;

  if(!(compile_all = PyObject_GetAttrString(router_route, "compile_all")))
    goto error;

  Py_INCREF(&MatcherType);
  PyModule_AddObject(m, "Matcher", (PyObject*)&MatcherType);

  static Matcher_CAPI capi = { Matcher_match_request };
  api_capsule = export_capi(m, "router.cmatcher", &capi);
  if(!api_capsule)
    goto error;

  goto finally;

  error:
  m = NULL;

  finally:
  Py_XDECREF(router_route);
  Py_XDECREF(api_capsule);
  return m;
}
