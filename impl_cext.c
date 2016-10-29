#include <stdbool.h>
#include <Python.h>

#include "picohttpparser.h"


static PyObject* Request;

static PyObject* malformed_headers;
static PyObject* malformed_body;
static PyObject* empty_body;

enum HttpRequestParser_state {
  HTTP_REQUEST_PARSER_HEADERS,
  HTTP_REQUEST_PARSER_BODY
};

enum HttpRequestParser_transfer {
  HTTP_REQUEST_PARSER_UNSET,
  HTTP_REQUEST_PARSER_IDENTITY,
  HTTP_REQUEST_PARSER_CHUNKED
};

static unsigned long const CONTENT_LENGTH_UNSET = ULONG_MAX;

typedef struct {
    PyObject_HEAD

    enum HttpRequestParser_state state;
    enum HttpRequestParser_transfer transfer;

    unsigned long content_length;
    struct phr_chunked_decoder chunked_decoder;
    size_t chunked_offset;
    bool no_semantics;

    PyObject* buffer;

    PyObject* request;
    PyObject* on_headers;
    PyObject* on_body;
    PyObject* on_error;
} HttpRequestParser;


static void _reset_state(HttpRequestParser* self) {
    Py_XDECREF(self->request);
    self->request = Py_None;
    Py_INCREF(self->request);

    self->state = HTTP_REQUEST_PARSER_HEADERS;
    self->transfer = HTTP_REQUEST_PARSER_UNSET;
    self->content_length = CONTENT_LENGTH_UNSET;
    memset(&self->chunked_decoder, 0, sizeof(struct phr_chunked_decoder));
    self->chunked_decoder.consume_trailer = 1;
    self->chunked_offset = 0;
    self->no_semantics = false;
}


static PyObject *
HttpRequestParser_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    HttpRequestParser *self = NULL;

    self = (HttpRequestParser *)type->tp_alloc(type, 0);
    if (!self)
        goto finally;

    self->on_headers = NULL;
    self->on_body = NULL;
    self->on_error = NULL;
    self->buffer = NULL;
    self->request = NULL;

    finally:
    return (PyObject *)self;
}

static int
HttpRequestParser_init(HttpRequestParser *self, PyObject *args, PyObject *kwds)
{
    printf("__init__\n");
    // FIXME: __init__ can be called many times

    // FIXME: check argument types
    int result = PyArg_ParseTuple(
      args, "OOO", &self->on_headers, &self->on_body, &self->on_error);
    if(!result)
      return -1;
    Py_INCREF(self->on_headers);
    Py_INCREF(self->on_body);
    Py_INCREF(self->on_error);

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

    Py_XDECREF(self->buffer);
    Py_XDECREF(self->on_error);
    Py_XDECREF(self->on_body);
    Py_XDECREF(self->on_headers);
    Py_XDECREF(self->request);
    Py_TYPE(self)->tp_free((PyObject*)self);
}


static int _parse_headers(HttpRequestParser* self) {
  PyObject* py_method = NULL;
  PyObject* py_path = NULL;
  PyObject* py_version = NULL;
  PyObject* py_headers = NULL;

  Py_buffer view;
  int result;

  if(PyObject_GetBuffer(self->buffer, &view, PyBUF_WRITABLE) == -1) {
    result = -3;
    goto finally;
  }

  const char* method;
  size_t method_len;
  const char* path;
  size_t path_len;
  int minor_version;
  struct phr_header headers[10];
  size_t num_headers = 10;

  result = phr_parse_request(
    view.buf, view.len,
    &method, &method_len,
    &path, &path_len,
    &minor_version, headers, &num_headers, 0);

  // FIXME: More than 10 headers

  printf("result: %d\n", result);

  if(result == -2)
    goto finally;

  if(result == -1) {
    PyObject* on_error_result = PyObject_CallFunctionObjArgs(
      self->on_error, malformed_headers, NULL);
    if(!on_error_result) {
      result = -3;
      goto finally;
    }
    Py_DECREF(on_error_result);

    _reset_state(self);
    PyBuffer_Release(&view);
    view.buf = NULL;
    PyByteArray_Resize(self->buffer, 0);
    goto finally;
  }

  // TODO: is it faster to compare length first?
  if(strncasecmp(method, "GET ", 4) == 0 ||
     strncasecmp(method, "HEAD ", 5) == 0 ||
     strncasecmp(method, "DELETE ", 7) == 0)
    self->no_semantics = true;

  // TODO: probably use static for common methods
  py_method = PyUnicode_FromStringAndSize(method, method_len);
  if(!py_method) {
    result = -3;
    goto finally;
  }
  printf("method: "); PyObject_Print(py_method, stdout, 0); printf("\n");
  // TODO: probably static for "/", maybe "/index.html"
  py_path = PyUnicode_FromStringAndSize(path, path_len);
  if(!py_path) {
    result = -3;
    goto finally;
  }
  printf("path: "); PyObject_Print(py_path, stdout, 0); printf("\n");
  // TODO: probably use static unicode
  char version[3] = "1.1";
  if(!minor_version)
    version[2] = '0';
  py_version = PyUnicode_FromStringAndSize(version, 3);
  if(!py_version) {
    result = -3;
    goto finally;
  }
  printf("version: "); PyObject_Print(py_version, stdout, 0); printf("\n");


  if(minor_version == 0)
    self->transfer = HTTP_REQUEST_PARSER_IDENTITY;
  else
    self->transfer = HTTP_REQUEST_PARSER_CHUNKED;

  py_headers = PyDict_New();
  if(!py_headers) {
    result = -3;
    goto finally;
  }
  for(size_t i = 0; i < num_headers; i++) {
    struct phr_header header = headers[i];

    if(strncasecmp(header.name, "Transfer-Encoding", header.name_len) == 0) {
      if(strncasecmp(header.value, "chunked", header.value_len) == 0)
        self->transfer = HTTP_REQUEST_PARSER_CHUNKED;
      else if(strncasecmp(header.value, "identity", header.value_len) == 0)
        self->transfer = HTTP_REQUEST_PARSER_IDENTITY;
      else
        /*TODO: handle incorrept values for protocol version, also comma sep*/;
    }

    if(strncasecmp(header.name, "Content-Length", header.name_len) == 0) {
      char * endptr = (char *)header.value + header.name_len;
      self->content_length = strtol(header.value, &endptr, 10);

      // FIXME: endptr != NULL, zero length, invlid chars
      // FIXME: negative values
    }

    bool prev_alpha = false;
    for(char* c = (char*)header.name; c < header.name + header.name_len; c++) {
      if(*c >= 'A' && *c <= 'Z') {
        if(prev_alpha)
          *c |= 0x20;
        prev_alpha = true;
      } else if (*c >= 'a' && *c <= 'z')
        prev_alpha = true;
      else
        prev_alpha = false;
    }

    // TODO: common names and values static
    // TODO: normalize to title case
    PyObject* py_header_name = NULL;
    PyObject* py_header_value = NULL;

    py_header_name = PyUnicode_FromStringAndSize(
      header.name, header.name_len);
    if(!py_header_name) {
      result = -3;
      goto finally_loop;
    }

    // FIXME: this can return NULL on codec error
    py_header_value = PyUnicode_DecodeLatin1(
      header.value, header.value_len, NULL);
    if(!py_header_value) {
      result = -3;
      goto finally_loop;
    }

    if(PyDict_SetItem(py_headers, py_header_name, py_header_value) == -1)
      result = -3;

    PyObject_Print(py_header_name, stdout, 0); printf(": ");
    PyObject_Print(py_header_value, stdout, 0); printf("\n");

    finally_loop:
    Py_XDECREF(py_header_value);
    Py_XDECREF(py_header_name);

    if(result == -3)
      goto finally;
  }

  if(self->content_length != CONTENT_LENGTH_UNSET)
    printf("self->content_length: %ld\n", self->content_length);
  if(self->transfer == HTTP_REQUEST_PARSER_IDENTITY)
    printf("self->transfer: identity\n");
  else if(self->transfer == HTTP_REQUEST_PARSER_CHUNKED)
    printf("self->transfer: chunked\n");

  PyObject* trimmed_buffer = PySequence_GetSlice(
    self->buffer, result, view.len);
  if(!trimmed_buffer) {
    result = -3;
    goto finally;
  }
  Py_DECREF(self->buffer);
  self->buffer = trimmed_buffer;

  PyObject* request = PyObject_CallFunctionObjArgs(
    Request, py_method, py_path, py_version, py_headers, NULL);
  if(!request) {
    result = -3;
    goto finally;
  }
  Py_DECREF(self->request);
  self->request = request;

  PyObject* on_headers_result = PyObject_CallFunctionObjArgs(
    self->on_headers, request, NULL);
  if(!on_headers_result) {
    result = -3;
    goto finally;
  }
  Py_DECREF(on_headers_result);

  finally:
  Py_XDECREF(py_headers);
  Py_XDECREF(py_version);
  Py_XDECREF(py_path);
  Py_XDECREF(py_method);
  if(view.buf)
    PyBuffer_Release(&view);

  return result;
}

static int _parse_body(HttpRequestParser* self) {
  Py_buffer view;
  view.buf = NULL;
  PyObject* body = NULL;
  int result = -2;
  if(self->content_length == CONTENT_LENGTH_UNSET && self->no_semantics) {
    result = 0;
    goto on_body;
  }

  if(self->content_length == 0) {
    Py_INCREF(empty_body);
    body = empty_body;
    result = 0;
    goto on_body;
  }

  if(PyObject_GetBuffer(self->buffer, &view, PyBUF_WRITABLE) == -1) {
    result = -3;
    goto finally;
  }

  if(self->content_length != CONTENT_LENGTH_UNSET) {
    if(self->content_length > (unsigned long)view.len) {
      result = -2;
      goto finally;
    }

    body = PyBytes_FromStringAndSize(view.buf, self->content_length);
    if(!body) {
      result = -3;
      goto finally;
    }

    PyObject* trimmed_buffer = PySequence_GetSlice(
      self->buffer, self->content_length, view.len);
    if(!trimmed_buffer) {
      result = -3;
      goto finally;
    }
    Py_DECREF(self->buffer);
    self->buffer = trimmed_buffer;

    // TODO result = self->content_length (long)
    result = 1;

    goto on_body;
  }

  if(self->transfer == HTTP_REQUEST_PARSER_IDENTITY) {
    result = -2;
    goto finally;
  }

  if(self->transfer == HTTP_REQUEST_PARSER_CHUNKED) {
    size_t chunked_offset_start = self->chunked_offset;
    self->chunked_offset = (size_t)view.len - self->chunked_offset;
    result = phr_decode_chunked(
      &self->chunked_decoder,
      (char *)view.buf + chunked_offset_start,
      &self->chunked_offset);
    self->chunked_offset = self->chunked_offset + chunked_offset_start;

    if(result == -2) {
      PyBuffer_Release(&view);
      view.buf = NULL;
      PyByteArray_Resize(self->buffer, self->chunked_offset);
      goto finally;
    }

    if(result == -1) {
      PyObject* on_error_result = PyObject_CallFunctionObjArgs(
        self->on_error, malformed_body, NULL);
      if(!on_error_result) {
        result = -3;
        goto finally;
      }
      Py_DECREF(on_error_result);

      _reset_state(self);
      PyBuffer_Release(&view);
      view.buf = NULL;
      PyByteArray_Resize(self->buffer, 0);
      goto finally;
    }

    body = PyBytes_FromStringAndSize(view.buf, self->chunked_offset);
    if(!body) {
      result = -3;
      goto finally;
    }

    PyObject* trimmed_buffer = PySequence_GetSlice(
      self->buffer, self->chunked_offset, self->chunked_offset + result);
    if(!trimmed_buffer) {
      result = -3;
      goto finally;
    }
    Py_DECREF(self->buffer);
    self->buffer = trimmed_buffer;

    goto on_body;
  }

  goto finally;

  PyObject* on_body_result;
  on_body:

  if(body) {
    if(PyObject_SetAttrString(self->request, "body", body) == -1) {
      result = -3;
      goto finally;
    }

    printf("body: "); PyObject_Print(body, stdout, 0); printf("\n");
  }

  on_body_result = PyObject_CallFunctionObjArgs(
    self->on_body, self->request, NULL);
  if(!on_body_result) {
    result = -3;
    goto finally;
  }
  Py_DECREF(on_body_result);
  Py_XDECREF(body);

  _reset_state(self);

  finally:
  if(view.buf)
    PyBuffer_Release(&view);
  return result;
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
    0,                         /* tp_alloc */
    HttpRequestParser_new,     /* tp_new */
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
    Request = NULL;
    malformed_headers = NULL;
    malformed_body = NULL;
    empty_body = NULL;
    PyObject* m = NULL;
    PyObject* impl_cffi = NULL;

    HttpRequestParserType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&HttpRequestParserType) < 0)
        goto error;

    m = PyModule_Create(&impl_cext);
    if (!m)
      goto error;

    impl_cffi = PyImport_ImportModule("impl_cffi");
    if(!impl_cffi)
      goto error;

    Request = PyObject_GetAttrString(impl_cffi, "HttpRequest");
    if(!Request)
      goto error;

    malformed_headers = PyUnicode_FromString("malformed_headers");
    if(!malformed_headers)
      goto error;

    malformed_body = PyUnicode_FromString("malformed_body");
    if(!malformed_body)
      goto error;

    empty_body = PyBytes_FromString("");
    if(!empty_body)
      goto error;

    Py_INCREF(&HttpRequestParserType);
    PyModule_AddObject(
      m, "HttpRequestParser", (PyObject *)&HttpRequestParserType);


    goto finally;

    error:
    Py_XDECREF(empty_body);
    Py_XDECREF(malformed_body);
    Py_XDECREF(malformed_headers);
    Py_XDECREF(Request);
    finally:
    Py_XDECREF(impl_cffi);
    return m;
}
