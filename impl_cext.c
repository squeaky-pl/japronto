#include <stdbool.h>
#include <Python.h>
#include <sys/param.h>

#include "picohttpparser.h"


static PyObject* Request;

static PyObject* malformed_headers;
static PyObject* malformed_body;
static PyObject* incomplete_headers;
static PyObject* invalid_headers;
static PyObject* incomplete_body;
static PyObject* empty_body;

static PyObject* GET;
static PyObject* POST;
static PyObject* DELETE;
static PyObject* HEAD;
static PyObject* HTTP10;
static PyObject* HTTP11;
static PyObject* Host;
static PyObject* User_Agent;
static PyObject* Accept;
static PyObject* Accept_Language;
static PyObject* Accept_Encoding;
static PyObject* Accept_Charset;
static PyObject* Connection;
static PyObject* Cookie;
static PyObject* Content_Length;
static PyObject* Transfer_Encoding;
/*static PyObject* Gzip_Deflate;*/
static PyObject* val_close;
static PyObject* keep_alive;

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

    char* buffer;
    size_t buffer_start;
    size_t buffer_end;
    size_t buffer_capacity;

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
    self->request = NULL;

    finally:
    return (PyObject *)self;
}

static int
HttpRequestParser_init(HttpRequestParser *self, PyObject *args, PyObject *kwds)
{
#ifdef DEBUG_PRINT
    printf("__init__\n");
#endif
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

    self->buffer_start = 0;
    self->buffer_end = 0;
    self->buffer_capacity = 2048;
    self->buffer = malloc(self->buffer_capacity);
    if(!self->buffer)
      return -1;

    return 0;
}


static void
HttpRequestParser_dealloc(HttpRequestParser* self)
{
#ifdef DEBUG_PRINT
    printf("__del__\n");
#endif

    if(self->buffer)
      free(self->buffer);

    Py_XDECREF(self->on_error);
    Py_XDECREF(self->on_body);
    Py_XDECREF(self->on_headers);
    Py_XDECREF(self->request);
    Py_TYPE(self)->tp_free((PyObject*)self);
}


static int _parse_headers(HttpRequestParser* self) {
  PyObject* py_method = NULL;
  PyObject* py_path = NULL;
  PyObject* py_headers = NULL;
  PyObject* error;

  int result;

  const char* method;
  size_t method_len;
  const char* path;
  size_t path_len;
  int minor_version;
  struct phr_header headers[10];
  size_t num_headers = 10;

  result = phr_parse_request(
    self->buffer + self->buffer_start, self->buffer_end - self->buffer_start,
    &method, &method_len,
    &path, &path_len,
    &minor_version, headers, &num_headers, 0);

  // FIXME: More than 10 headers
#ifdef DEBUG_PRINT
  printf("result: %d\n", result);
#endif

  if(result == -2)
    goto finally;

  if(result == -1) {
    error = malformed_headers;
    goto on_error;
  }

#define if_method_equal(m) \
if(method_len == strlen(#m) && strncmp(method, #m, method_len) == 0) \
{ \
  py_method = m; \
  Py_INCREF(m); \
}
  if_method_equal(GET)
  else if_method_equal(POST)
  else if_method_equal(DELETE)
  else if_method_equal(HEAD)
  else {
    py_method = PyUnicode_FromStringAndSize(method, method_len);
    if(!py_method) {
      result = -3;
      goto finally;
    }
  }
#undef if_method_equal

  if(py_method == GET || py_method == DELETE || py_method == HEAD)
    self->no_semantics = true;

#ifdef DEBUG_PRINT
  printf("method: "); PyObject_Print(py_method, stdout, 0); printf("\n");
#endif
  // TODO: probably static for "/", maybe "/index.html"
  py_path = PyUnicode_FromStringAndSize(path, path_len);
  if(!py_path) {
    result = -3;
    goto finally;
  }
#ifdef DEBUG_PRINT
  printf("path: "); PyObject_Print(py_path, stdout, 0); printf("\n");
#endif
  PyObject* py_version;
  if(minor_version == 0)
    py_version = HTTP10;
  else
    py_version = HTTP11;

#ifdef DEBUG_PRINT
  printf("version: "); PyObject_Print(py_version, stdout, 0); printf("\n");
#endif


  if(minor_version == 0)
    self->transfer = HTTP_REQUEST_PARSER_IDENTITY;
  else
    self->transfer = HTTP_REQUEST_PARSER_CHUNKED;

  py_headers = PyDict_New();
  if(!py_headers) {
    result = -3;
    goto finally;
  }

#define header_name_equal(val) \
  header.name_len == strlen(val) && strncasecmp(header.name, val, header.name_len) == 0
#define header_value_equal(val) \
  header.value_len == strlen(val) && strncasecmp(header.value, val, header.value_len) == 0
#define cmp_and_set_header_name(name, val) \
  if(header_name_equal(val)) { \
      py_header_name = name; \
      Py_INCREF(name); \
  }
#define cmp_and_set_header_value(name, val) \
  if(header_value_equal(val)) { \
      py_header_value = name; \
      Py_INCREF(name); \
  }

  for(size_t i = 0; i < num_headers; i++) {
    struct phr_header header = headers[i];

    // TODO: common names and values static
    PyObject* py_header_name = NULL;
    PyObject* py_header_value = NULL;

    if(header_name_equal("Transfer-Encoding")) {
      if(header_value_equal("chunked"))
        self->transfer = HTTP_REQUEST_PARSER_CHUNKED;
      else if(header_value_equal("identity"))
        self->transfer = HTTP_REQUEST_PARSER_IDENTITY;
      else
        /*TODO: handle incorrept values for protocol version, also comma sep*/;

      py_header_name = Transfer_Encoding;
      Py_INCREF(Transfer_Encoding);
    } else if(header_name_equal("Content-Length")) {
      if(!header.value_len) {
        error = invalid_headers;
        goto on_error;
      }

      if(*header.value == '+' || *header.value == '-') {
        error = invalid_headers;
        goto on_error;
      }

      char * endptr = (char *)header.value + header.value_len;
      self->content_length = strtol(header.value, &endptr, 10);
      // FIXME: overflow?

      if(endptr != (char*)header.value + header.value_len) {
        error = invalid_headers;
        goto on_error;
      }

      py_header_name = Content_Length;
      Py_INCREF(Content_Length);
    }
    else cmp_and_set_header_name(Host, "Host")
    else cmp_and_set_header_name(User_Agent, "User-Agent")
    else cmp_and_set_header_name(Accept, "Accept")
    else cmp_and_set_header_name(Accept_Language, "Accept-Language")
    else cmp_and_set_header_name(Accept_Encoding, "Accept-Encoding")
    else cmp_and_set_header_name(Accept_Charset, "Accept-Charset")
    else cmp_and_set_header_name(Connection, "Connection")
    else cmp_and_set_header_name(Cookie, "Cookie")
    else {
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

      py_header_name = PyUnicode_FromStringAndSize(
        header.name, header.name_len);
      if(!py_header_name) {
        result = -3;
        goto finally_loop;
      }
    }

    if(py_header_name == Connection) {
      cmp_and_set_header_value(keep_alive, "keep-alive")
      else cmp_and_set_header_value(val_close, "close")
      else /*FIXME: invalid Connection value*/;
    } else {
      // FIXME: this can return NULL on codec error
      py_header_value = PyUnicode_DecodeLatin1(
        header.value, header.value_len, NULL);
      if(!py_header_value) {
        result = -3;
        goto finally_loop;
      }
    }

    if(PyDict_SetItem(py_headers, py_header_name, py_header_value) == -1)
      result = -3;

#ifdef DEBUG_PRINT
    PyObject_Print(py_header_name, stdout, 0); printf(": ");
    PyObject_Print(py_header_value, stdout, 0); printf("\n");
#endif

    finally_loop:
    Py_XDECREF(py_header_value);
    Py_XDECREF(py_header_name);

    if(result == -3)
      goto finally;
  }

#ifdef DEBUG_PRINT
  if(self->content_length != CONTENT_LENGTH_UNSET)
    printf("self->content_length: %ld\n", self->content_length);
  if(self->transfer == HTTP_REQUEST_PARSER_IDENTITY)
    printf("self->transfer: identity\n");
  else if(self->transfer == HTTP_REQUEST_PARSER_CHUNKED)
    printf("self->transfer: chunked\n");
#endif

  self->buffer_start += (size_t)result;

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

  goto finally;

  PyObject* on_error_result;
  on_error:
  on_error_result = PyObject_CallFunctionObjArgs(
    self->on_error, error, NULL);
  if(!on_error_result) {
    result = -3;
    goto finally;
  }
  Py_DECREF(on_error_result);

  _reset_state(self);
  self->buffer_start = 0;
  self->buffer_end = 0;

  finally:
  Py_XDECREF(py_headers);
  Py_XDECREF(py_path);
  Py_XDECREF(py_method);

  return result;
}

static int _parse_body(HttpRequestParser* self) {
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

  if(self->content_length != CONTENT_LENGTH_UNSET) {
    if(self->content_length > self->buffer_end - self->buffer_start) {
      result = -2;
      goto finally;
    }

    body = PyBytes_FromStringAndSize(self->buffer + self->buffer_start, self->content_length);
    if(!body) {
      result = -3;
      goto finally;
    }

    self->buffer_start += self->content_length;

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
    self->chunked_offset = self->buffer_end - self->buffer_start - self->chunked_offset;
    result = phr_decode_chunked(
      &self->chunked_decoder,
      self->buffer + self->buffer_start + chunked_offset_start,
      &self->chunked_offset);
    self->chunked_offset = self->chunked_offset + chunked_offset_start;

    if(result == -2) {
      self->buffer_end = self->buffer_start + self->chunked_offset;
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
      self->buffer_start = 0;
      self->buffer_end = 0;

      goto finally;
    }

    body = PyBytes_FromStringAndSize(self->buffer + self->buffer_start, self->chunked_offset);
    if(!body) {
      result = -3;
      goto finally;
    }

    self->buffer_start += self->chunked_offset;
    self->buffer_end = self->buffer_start + (size_t)result;

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

#ifdef DEBUG_PRINT
    printf("body: "); PyObject_Print(body, stdout, 0); printf("\n");
#endif
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
  return result;
}


static PyObject *
HttpRequestParser_feed(HttpRequestParser* self, PyObject *args) {
  // FIXME: can be called without __init__
#ifdef DEBUG_PRINT
  printf("feed\n");
#endif

  const char* data;
  int data_len;
  if(!PyArg_ParseTuple(args, "y#", &data, &data_len))
    return NULL;

  if(self->buffer_start == self->buffer_end) {
    self->buffer_start = 0;
    self->buffer_end = 0;
  }

  if((size_t)data_len > self->buffer_capacity - self->buffer_end) {
    memmove(self->buffer, self->buffer + self->buffer_start, self->buffer_end - self->buffer_start);
    self->buffer_end -= self->buffer_start;
    self->buffer_start = 0;
  }

  if((size_t)data_len > self->buffer_capacity - (self->buffer_end - self->buffer_start)) {
    self->buffer_capacity = MAX(
      self->buffer_capacity * 2,
      self->buffer_end - self->buffer_start + data_len);
    self->buffer = realloc(self->buffer, self->buffer_capacity);
    if(!self->buffer)
      /* FIXME: alloc error */;
  }

  memcpy(self->buffer + self->buffer_end, data, (size_t)data_len);
  self->buffer_end += (size_t)data_len;

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
#ifdef DEBUG_PRINT
  printf("feed_disconnect\n");
#endif

  PyObject* error;

  PyObject* body = NULL;

  if(self->buffer_start == self->buffer_end) {
      goto finally;
  }


  if(self->transfer == HTTP_REQUEST_PARSER_UNSET) {
    error = incomplete_headers;
    goto on_error;
  }

  if(self->transfer == HTTP_REQUEST_PARSER_IDENTITY) {
    PyObject * body = PyBytes_FromStringAndSize(self->buffer + self->buffer_start, self->buffer_end - self->buffer_start);
    if(!body)
      return NULL;

    if(PyObject_SetAttrString(self->request, "body", body) == -1)
      return NULL;

    PyObject* on_body_result = PyObject_CallFunctionObjArgs(
      self->on_body, self->request, NULL);
    if(!on_body_result)
      return NULL;
    Py_DECREF(on_body_result);

    goto finally;
  }

  if(self->transfer == HTTP_REQUEST_PARSER_CHUNKED) {
    error = incomplete_body;
    goto on_error;
  }

  goto finally;

  PyObject* on_error_result;
  on_error:
  on_error_result = PyObject_CallFunctionObjArgs(
    self->on_error, error, NULL);
  if(!on_error_result)
    return NULL;
  Py_DECREF(on_error_result);

  finally:
  Py_XDECREF(body);
  _reset_state(self);
  self->buffer_start = 0;
  self->buffer_end = 0;

  Py_RETURN_NONE;
}

static PyObject *
HttpRequestParser_dump_buffer(HttpRequestParser* self) {
  // printf("buffer: "); PyObject_Print(self->buffer, stdout, 0); printf("\n");

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
    invalid_headers = NULL;
    malformed_body = NULL;
    incomplete_headers = NULL;
    incomplete_body = NULL;
    empty_body = NULL;
    GET = NULL;
    POST = NULL;
    DELETE = NULL;
    HEAD = NULL;
    HTTP10 = NULL;
    HTTP11 = NULL;
    Host = NULL;
    User_Agent = NULL;
    Accept = NULL;
    Accept_Language = NULL;
    Accept_Encoding = NULL;
    Accept_Charset = NULL;
    Connection = NULL;
    Cookie = NULL;
    Content_Length = NULL;
    Transfer_Encoding = NULL;
    val_close = NULL;
    keep_alive = NULL;
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

#define alloc_static(name) \
    name = PyUnicode_FromString(#name); \
    if(!name) \
      goto error;
#define alloc_static2(name, val) \
    name = PyUnicode_FromString(val); \
    if(!name) \
      goto error;

    alloc_static(malformed_headers)
    alloc_static(malformed_body)
    alloc_static(incomplete_headers)
    alloc_static(invalid_headers)
    alloc_static(incomplete_body)

    empty_body = PyBytes_FromString("");
    if(!empty_body)
      goto error;

    alloc_static(GET)
    alloc_static(POST)
    alloc_static(DELETE)
    alloc_static(HEAD)

    alloc_static2(HTTP10, "1.0")
    alloc_static2(HTTP11, "1.1")

    alloc_static(Host)
    alloc_static2(User_Agent, "User-Agent")
    alloc_static(Accept)
    alloc_static2(Accept_Language, "Accept-Language")
    alloc_static2(Accept_Encoding, "Accept-Encoding")
    alloc_static2(Accept_Charset, "Accept-Charset")
    alloc_static(Connection)
    alloc_static(Cookie)
    alloc_static2(Content_Length, "Content-Length")
    alloc_static2(Transfer_Encoding, "Transfer-Encoding")

    alloc_static2(val_close, "close")
    alloc_static2(keep_alive, "keep-alive")

#undef alloc_static
#undef alloc_static2

    Py_INCREF(&HttpRequestParserType);
    PyModule_AddObject(
      m, "HttpRequestParser", (PyObject *)&HttpRequestParserType);

    goto finally;

    error:
    Py_XDECREF(keep_alive);
    Py_XDECREF(val_close);

    Py_XDECREF(Transfer_Encoding);
    Py_XDECREF(Content_Length);
    Py_XDECREF(Cookie);
    Py_XDECREF(Connection);
    Py_XDECREF(Accept_Charset);
    Py_XDECREF(Accept_Encoding);
    Py_XDECREF(Accept_Language);
    Py_XDECREF(Accept);
    Py_XDECREF(User_Agent);
    Py_XDECREF(Host);

    Py_XDECREF(HEAD);
    Py_XDECREF(DELETE);
    Py_XDECREF(POST);
    Py_XDECREF(GET);

    Py_XDECREF(HTTP10);
    Py_XDECREF(HTTP11);

    Py_XDECREF(empty_body);
    Py_XDECREF(incomplete_body);
    Py_XDECREF(invalid_headers);
    Py_XDECREF(incomplete_headers);
    Py_XDECREF(malformed_body);
    Py_XDECREF(malformed_headers);

    Py_XDECREF(Request);
    finally:
    Py_XDECREF(impl_cffi);
    return m;
}
