#pragma once

#include <Python.h>

typedef struct _Matcher Matcher;


typedef struct {
  char* key;
  size_t key_length;
  char* value;
  size_t value_length;
} MatchDictEntry;


typedef struct {
  PyObject* (*Matcher_match_request)
    (Matcher* matcher, PyObject* request, PyObject** handler,
     MatchDictEntry** match_dict_entries, size_t* match_dict_length);
} Matcher_CAPI;
