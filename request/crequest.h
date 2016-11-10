#pragma once

#include <Python.h>


typedef struct {
  PyObject_HEAD

  size_t method_len;
  size_t path_len;
  char buffer[512];
  PyObject* method;
  PyObject* path;
  PyObject* version;
  PyObject* headers;
  PyObject* body;
} Request;

#define REQUEST_METHOD(r) \
  r->buffer

#define REQUEST_PATH(r) \
  r->buffer + r->method_len
