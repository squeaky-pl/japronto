#include <Python.h>

#include "picohttpparser.h"

enum HttpRequestParser_state {
  HTTP_REQUEST_PARSER_HEADERS,
  HTTP_REQUEST_PARSER_BODY
};

enum HttpRequestParser_transfer {
  HTTP_REQUEST_PARSER_UNSET,
  HTTP_REQUEST_PARSER_IDENTITY,
  HTTP_REQUEST_PARSER_CHUNKED
};

static unsigned int const CONTENT_LENGTH_UNSET = UINT_MAX;

typedef struct {
    PyObject_HEAD

    char* method;
    ssize_t method_len;
    char* path;
    ssize_t path_len;
    int minor_version;
    struct phr_header headers[10];
    size_t num_headers;

    enum HttpRequestParser_state state;
    enum HttpRequestParser_transfer transfer;

    unsigned int content_length;
    struct phr_chunked_decoder chunked_decoder;
    size_t chunked_offset;

    PyObject* buffer;
} HttpRequestParser;


static void _reset_state(HttpRequestParser* self) {
    self->state = HTTP_REQUEST_PARSER_HEADERS;
    self->transfer = HTTP_REQUEST_PARSER_UNSET;
    self->content_length = CONTENT_LENGTH_UNSET;
    memset(&self->chunked_decoder, 0, sizeof(struct phr_chunked_decoder));
    self->chunked_decoder.consume_trailer = 1;
    self->chunked_offset = 0;
}


static int
HttpRequestParser_init(HttpRequestParser *self, PyObject *args, PyObject *kwds)
{
    printf("__init__\n");
    // FIXME: __init__ can be called many times

    _reset_state(self);
    self->buffer = PyByteArray_FromStringAndSize("", 0);
    if(!self->buffer)
      return -1;

    return 0;
}


static void
HttpRequestParser_dealloc(HttpRequestParser* self)
{
    printf("__del__\n");
    // FIXME: it might be that __init__ was not called, only __new__
    // in this case buffer will point to some random memory
    // BOOM!
    Py_XDECREF(self->buffer);
    Py_TYPE(self)->tp_free((PyObject*)self);
}


static int _parse_headers(HttpRequestParser* self) {
  return -2;
}

static int _parse_body(HttpRequestParser* self) {
  return -2;
}


static PyObject *
HttpRequestParser_feed(HttpRequestParser* self, PyObject *args) {
  // FIXME: can be called without __init__
  printf("feed\n");

  PyObject* data;
  if (!PyArg_ParseTuple(args, "O", &data))
        return NULL;
  // FIXME check type
  if(!PySequence_InPlaceConcat(self->buffer, data))
        return NULL;
  Py_DECREF(self->buffer);

  int result;

  while(1) {
    if(self->state == HTTP_REQUEST_PARSER_HEADERS) {
      result = _parse_headers(self);
      if(result <= 0) {
        Py_RETURN_NONE;
      }

      self->state = HTTP_REQUEST_PARSER_BODY;
    }

    if(self->state == HTTP_REQUEST_PARSER_BODY) {
      result = _parse_body(self);

      if(result < 0) {
        Py_RETURN_NONE;
      }

      self->state = HTTP_REQUEST_PARSER_HEADERS;
    }
  }

  Py_RETURN_NONE;
}


static PyObject *
HttpRequestParser_feed_disconnect(HttpRequestParser* self) {
  // FIXME: can be called without __init__
  printf("feed_disconnect\n");
  Py_RETURN_NONE;
}

static PyObject *
HttpRequestParser_dump_buffer(HttpRequestParser* self) {
  printf("buffer: "); PyObject_Print(self->buffer, stdout, 0); printf("\n");

  Py_RETURN_NONE;
}


static PyMethodDef HttpRequestParser_methods[] = {
    {"feed", (PyCFunction)HttpRequestParser_feed, METH_VARARGS,
     "feed"
    },
    {
      "feed_disconnect", (PyCFunction)HttpRequestParser_feed_disconnect,
      METH_NOARGS,
      "feed_disconnect"
    },
    {
      "_dump_buffer", (PyCFunction)HttpRequestParser_dump_buffer,
      METH_NOARGS,
      "_dump_buffer"
    },
    {NULL}  /* Sentinel */
};


static PyTypeObject HttpRequestParserType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "impl_cext.HttpRequestParser",       /* tp_name */
    sizeof(HttpRequestParser), /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)HttpRequestParser_dealloc, /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_reserved */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash  */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,        /* tp_flags */
    "HttpRequestParser",       /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    HttpRequestParser_methods, /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)HttpRequestParser_init, /* tp_init */
};

static PyModuleDef impl_cext = {
    PyModuleDef_HEAD_INIT,
    "impl_cext",
    "impl_cext",
    -1,
    NULL, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_impl_cext(void)
{
    PyObject* m;

    HttpRequestParserType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&HttpRequestParserType) < 0)
        return NULL;

    m = PyModule_Create(&impl_cext);
    if (m == NULL)
        return NULL;

    Py_INCREF(&HttpRequestParserType);
    PyModule_AddObject(
      m, "HttpRequestParser", (PyObject *)&HttpRequestParserType);
    return m;
}
