#pragma once

#ifndef PARSER_STANDALONE
#include "impl_cext.h"
#endif

typedef struct {
  PyObject_HEAD

#ifdef PARSER_STANDALONE
  PyObject* feed;
  PyObject* feed_disconnect;
#else
  Parser parser;
#endif
  PyObject* app;
  PyObject* matcher;
  PyObject* error_handler;
  PyObject* response;
  PyObject* transport;
} Protocol;


#ifndef PARSER_STANDALONE
Protocol* Protocol_on_headers(Protocol*, PyObject*);
Protocol* Protocol_on_body(Protocol*, PyObject*);
Protocol* Protocol_on_error(Protocol*, PyObject*);
#endif
