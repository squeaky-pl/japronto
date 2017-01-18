#pragma once

#include <Python.h>
#include <stdbool.h>

#include "match_dict.h"

typedef struct {
  PyObject* route;
  PyObject* handler;
  bool coro_func;
  bool simple;
  size_t pattern_len;
  size_t methods_len;
  size_t placeholder_cnt;
  char buffer[];
} MatcherEntry;


typedef struct _Matcher Matcher;


typedef struct {
  MatcherEntry* (*Matcher_match_request)
    (Matcher* matcher, PyObject* request,
     MatchDictEntry** match_dict_entries, size_t* match_dict_length);
} Matcher_CAPI;
