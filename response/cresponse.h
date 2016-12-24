#pragma once

#include <Python.h>
#include "common.h"


#define RESPONSE_INITIAL_BUFFER_LEN 1024

typedef struct {
  PyObject_HEAD

  int minor_version;
  KEEP_ALIVE keep_alive;

  PyObject* status_code;
  PyObject* mime_type;
  PyObject* body;
  PyObject* encoding;
  PyObject* headers;

  char* buffer;
  size_t buffer_len;
  char inline_buffer[RESPONSE_INITIAL_BUFFER_LEN];
} Response;


typedef struct {
  PyTypeObject* ResponseType;
  char* (*Response_render)(Response*, size_t*);
  int (*Response_init)(Response* self, PyObject *args, PyObject *kw);
} Response_CAPI;

#ifndef RESPONSE_OPAQUE
PyObject*
Response_new(PyTypeObject* type, Response* self);

void
Response_dealloc(Response* self);
#endif
