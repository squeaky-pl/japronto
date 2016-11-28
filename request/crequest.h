#pragma once

#include <Python.h>
#include <stdbool.h>


typedef struct {
  PyObject_HEAD

  size_t method_len;
  char* path;
  bool path_decoded;
  size_t path_len;
  int minor_version;
  struct phr_header* headers;
  size_t num_headers;
  char buffer[1024];
  PyObject* py_method;
  PyObject* py_path;
  PyObject* py_headers;
  PyObject* py_body;
  PyObject* response;
} Request;

#define REQUEST(r) \
  ((Request*)r)

#define REQUEST_METHOD(r) \
  REQUEST(r)->buffer

#define REQUEST_PATH(r) \
  REQUEST(r)->path


typedef struct {
  PyTypeObject* RequestType;
  void (*Request_from_raw)
    (Request* self, char* method, size_t method_len,
     char* path, size_t path_len,
     int minor_version,
     struct phr_header* headers, size_t num_headers);

  char* (*Request_get_decoded_path)
    (Request* self, size_t* path_len);
} Request_CAPI;
