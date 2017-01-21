#pragma once

#include <Python.h>
#include <stdbool.h>

#include "cmatcher.h"
#include "cresponse.h"
#include "common.h"

#define REQUEST_INITIAL_BUFFER_LEN 1024

typedef struct {
  PyObject_HEAD

  char* method;
  size_t method_len;
  char* path;
  bool path_decoded;
  size_t path_len;
  bool qs_decoded;
  size_t qs_len;
  int minor_version;
  struct phr_header* headers;
  size_t num_headers;
  MatchDictEntry* match_dict_entries;
  size_t match_dict_length;
  char* body;
  size_t body_length;
  char* buffer;
  size_t buffer_len;
  char inline_buffer[REQUEST_INITIAL_BUFFER_LEN];
  KEEP_ALIVE keep_alive;
  bool simple;
  bool response_called;
  MatcherEntry* matcher_entry;
  PyObject* exception;

  PyObject* transport;
  PyObject* app;
  PyObject* py_method;
  PyObject* py_path;
  PyObject* py_qs;
  PyObject* py_headers;
  PyObject* py_match_dict;
  PyObject* py_body;
  PyObject* extra;
  PyObject* done_callbacks;
  Response response;
} Request;

#define REQUEST(r) \
  ((Request*)r)

#define REQUEST_METHOD(r) \
  REQUEST(r)->buffer

#define REQUEST_PATH(r) \
  REQUEST(r)->path


typedef struct {
  PyTypeObject* RequestType;

  PyObject* (*Request_clone)
    (Request* original);

  void (*Request_from_raw)
    (Request* self, char* method, size_t method_len,
     char* path, size_t path_len,
     int minor_version,
     struct phr_header* headers, size_t num_headers);

  char* (*Request_get_decoded_path)
    (Request* self, size_t* path_len);

  void (*Request_set_match_dict_entries)
    (Request* self, MatchDictEntry* entries, size_t length);

  void (*Request_set_body)
    (Request* self, char* body, size_t body_len);
} Request_CAPI;


#ifndef REQUEST_OPAQUE
PyObject*
Request_new(PyTypeObject* type, Request* self);

void
Request_dealloc(Request* self);

int
Request_init(Request* self);

void*
crequest_init(void);
#endif
