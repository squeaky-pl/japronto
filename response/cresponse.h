#include <Python.h>

struct _Response;

#define RESPONSE struct _Response

typedef struct {
  PyObject* (*Response_render)(RESPONSE*);
  int (*Response_init)(RESPONSE* self, PyObject *args, PyObject *kw);
} Response_CAPI;
