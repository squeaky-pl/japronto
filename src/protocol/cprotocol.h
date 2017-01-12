#pragma once

#ifndef PARSER_STANDALONE
#include "cparser.h"
#endif

#include "cpipeline.h"
#include "crequest.h"
#include <stdbool.h>

typedef struct {
  PyObject_HEAD

#ifdef PARSER_STANDALONE
  PyObject* feed;
  PyObject* feed_disconnect;
#else
  Parser parser;
#endif
  Request static_request;
  Pipeline pipeline;
#ifdef REAPER_ENABLED
  unsigned long idle_time;
  unsigned long read_ops;
  unsigned long last_read_ops;
#endif
  PyObject* app;
  PyObject* matcher;
  PyObject* error_handler;
  PyObject* transport;
  PyObject* write;
  PyObject* create_task;
  PyObject* request_logger;
#ifdef PROTOCOL_TRACK_REFCNT
  Py_ssize_t none_cnt;
  Py_ssize_t true_cnt;
  Py_ssize_t false_cnt;
#endif
  bool closed;
} Protocol;


#ifndef PARSER_STANDALONE
Protocol* Protocol_on_headers(Protocol*, char* method, size_t method_len,
                              char* path, size_t path_len, int minor_version,
                              void* headers, size_t num_headers);
Protocol* Protocol_on_body(Protocol*, char* body, size_t body_len);
Protocol* Protocol_on_error(Protocol*, PyObject*);
#endif

typedef struct {
  void* (*Protocol_close)
    (Protocol* self);
} Protocol_CAPI;
