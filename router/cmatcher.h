#pragma once

#include <Python.h>

typedef struct _Matcher Matcher;

typedef struct {
  PyObject* (*Matcher_match_request)
    (Matcher* matcher, PyObject* request, PyObject** handler);
} Matcher_CAPI;
