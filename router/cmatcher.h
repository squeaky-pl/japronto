#pragma once

#include <Python.h>

#include "match_dict.h"

typedef struct _Matcher Matcher;


typedef struct {
  PyObject* (*Matcher_match_request)
    (Matcher* matcher, PyObject* request, PyObject** handler,
     MatchDictEntry** match_dict_entries, size_t* match_dict_length);
} Matcher_CAPI;
