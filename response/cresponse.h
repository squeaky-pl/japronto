#pragma once

#include <Python.h>

typedef struct {
  PyObject_HEAD

  PyObject* status_code;
  PyObject* mime_type;
  PyObject* text;
  PyObject* encoding;

  char buffer[1024];
} Response;


typedef struct {
  PyTypeObject* ResponseType;
  PyObject* (*Response_render)(Response*);
  int (*Response_init)(Response* self, PyObject *args, PyObject *kw);
} Response_CAPI;

#ifndef RESPONSE_OPAQUE
PyObject*
Response_new(PyTypeObject* type, Response* self);

void
Response_dealloc(Response* self);
#endif
