#pragma once

#include <Python.h>
#include <stdbool.h>

#include "match_dict.h"

typedef struct {
  PyObject_HEAD

  size_t method_len;
  char* path;
  bool path_decoded;
  size_t path_len;
  int minor_version;
  struct phr_header* headers;
  size_t num_headers;
  MatchDictEntry* match_dict_entries;
  size_t match_dict_length;
  char* body;
  size_t body_length;
  char buffer[1024];
  PyObject* py_method;
  PyObject* py_path;
  PyObject* py_headers;
  PyObject* py_match_dict;
  PyObject* py_body;
  PyObject* py_text;
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

  void (*Request_set_match_dict_entries)
    (Request* self, MatchDictEntry* entries, size_t length);

  void (*Request_set_body)
    (Request* self, char* body, size_t body_len);
} Request_CAPI;
