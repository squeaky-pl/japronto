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

#define REQUEST(r) \
  ((Request*)r)

#define REQUEST_METHOD(r) \
  REQUEST(r)->buffer

#define REQUEST_PATH(r) \
  REQUEST(r)->buffer + REQUEST(r)->method_len
