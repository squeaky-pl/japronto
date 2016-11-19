#pragma once

#include <time.h>

#ifndef PARSER_STANDALONE
#include "cparser.h"
#endif

typedef struct {
  PyObject_HEAD

#ifdef PARSER_STANDALONE
  PyObject* feed;
  PyObject* feed_disconnect;
#else
  Parser parser;
#endif
  struct timespec last_active;

  PyObject* app;
  PyObject* matcher;
  PyObject* error_handler;
  PyObject* response;
  PyObject* request;
  PyObject* transport;
  PyObject* call_later;
  PyObject* check_idle;
} Protocol;


#ifndef PARSER_STANDALONE
Protocol* Protocol_on_headers(Protocol*, char* method, size_t method_len,
                              char* path, size_t path_len, int minor_version,
                              void* headers, size_t num_headers);
Protocol* Protocol_on_body(Protocol*, char* body, size_t body_len);
Protocol* Protocol_on_error(Protocol*, PyObject*);
#endif
