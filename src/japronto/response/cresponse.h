#pragma once

#include <Python.h>
#include <stdbool.h>
#include "common.h"


#define RESPONSE_INITIAL_BUFFER_LEN 1024

typedef struct {
  PyObject_HEAD

  bool opaque;
  int minor_version;
  KEEP_ALIVE keep_alive;

  PyObject* code;
  PyObject* mime_type;
  PyObject* body;
  PyObject* encoding;
  PyObject* headers;
  PyObject* cookies;

  char* buffer;
  size_t buffer_len;
  char inline_buffer[RESPONSE_INITIAL_BUFFER_LEN];
} Response;


typedef struct {
  PyTypeObject* ResponseType;
  PyObject* (*Response_render)(Response*, bool);
  int (*Response_init)(Response* self, PyObject *args, PyObject *kw);
} Response_CAPI;

#ifndef RESPONSE_OPAQUE
PyObject*
Response_new(PyTypeObject* type, Response* self);

void
Response_dealloc(Response* self);
#endif
