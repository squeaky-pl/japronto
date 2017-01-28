#include <Python.h>
#include <sys/param.h>

#include "cresponse.h"
#include "capsule.h"
#include "reasons.h"

#ifdef RESPONSE_OPAQUE
static PyObject* json_dumps;
static const size_t reason_offset = 13;
static const size_t minor_offset = 7;
#endif



static const char header[] = "HTTP/1.1 200 OK\r\n"
  "Content-Length: ";


#ifdef RESPONSE_OPAQUE
static PyObject *
Response_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
#else
PyObject*
Response_new(PyTypeObject* type, Response* self)
#endif
{
#ifdef RESPONSE_OPAQUE
  Response* self = NULL;

  self = (Response*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;
  self->opaque = true;
#else
  ((PyObject*)self)->ob_refcnt = 1;
  ((PyObject*)self)->ob_type = type;
  self->opaque = false;
#endif

  self->code = NULL;
  self->mime_type = NULL;
  self->body = NULL;
  self->encoding = NULL;
  self->headers = NULL;
  self->cookies = NULL;

  self->buffer = self->inline_buffer;
  self->buffer_len = RESPONSE_INITIAL_BUFFER_LEN;
  memcpy(self->buffer, header, strlen(header));

#ifdef RESPONSE_OPAQUE
  finally:
#endif
  return (PyObject*)self;
}


#ifdef RESPONSE_OPAQUE
static void
#else
void
#endif
Response_dealloc(Response* self)
{
  if(self->buffer != self->inline_buffer)
    free(self->buffer);

  Py_XDECREF(self->cookies);
  Py_XDECREF(self->headers);
  Py_XDECREF(self->encoding);
  Py_XDECREF(self->body);
  Py_XDECREF(self->mime_type);
  Py_XDECREF(self->code);

#ifdef RESPONSE_OPAQUE
  if(self->opaque)
    Py_TYPE(self)->tp_free((PyObject*)self);
#endif
}

#ifdef RESPONSE_OPAQUE
static const size_t code_offset = 9;

#define empty(v) (!v || v == Py_None)

static PyObject* application_json;
static PyObject* application_octet;

int
Response_init(Response* self, PyObject *args, PyObject *kw)
{
  static char *kwlist[] = {"text", "code", "body", "json", "mime_type", "encoding", "headers", "cookies", NULL};

  PyObject* code = NULL;
  PyObject* body = NULL;
  PyObject* text = NULL;
  PyObject* json = NULL;
  PyObject* mime_type = NULL;
  PyObject* encoding = NULL;
  PyObject* headers = NULL;
  PyObject* cookies = NULL;

  // FIXME: check argument types
  if (!PyArg_ParseTupleAndKeywords(
      args, kw, "|OOOOOOOO", kwlist,
      &text, &code, &body, &json,
      &mime_type, &encoding, &headers, &cookies))
      goto error;

  if(!empty(code)) {
    self->code = code;
    Py_INCREF(self->code);
  }

  if(!empty(json)) {
    assert(empty(text) && empty(body));

    if(!(text = PyObject_CallFunctionObjArgs(json_dumps, json, NULL)))
      goto error;
  } else if(!empty(text)) {
    Py_INCREF(text);
  }

  if(!empty(text)) {
    assert(empty(body));

    if(!encoding) {
      if(!(self->body = PyUnicode_AsUTF8String(text)))
        goto error;
    } else {
      char* cencoding;
      if(!(cencoding = PyUnicode_AsUTF8(encoding)))
        goto error;

      if(!(self->body = PyUnicode_AsEncodedString(text, cencoding, NULL)))
        goto error;
    }

    Py_DECREF(text);
  }

  if(!empty(body)) {
    self->body = body;
    Py_INCREF(self->body);
  }

  if(!empty(mime_type)) {
    self->mime_type = mime_type;
    Py_INCREF(self->mime_type);
  } else {
    if(!empty(json)) {
      self->mime_type = application_json;
      Py_INCREF(self->mime_type);
    } else if(!empty(body)) {
      self->mime_type = application_octet;
      Py_INCREF(self->mime_type);
    }
  }

  if(!empty(encoding)) {
    self->encoding = encoding;
    Py_INCREF(self->encoding);
  }

  if(!empty(headers)) {
    self->headers = headers;
    Py_INCREF(self->headers);
  }

  if(!empty(cookies)) {
    self->cookies = cookies;
    Py_INCREF(self->cookies);
  }

  goto finally;

  error:
  return -1;
  finally:
  return 0;
}


static const char Content_Type[] = "Content-Type: ";
static const char charset[] = "; charset=";
static const char utf8[] = "utf-8";
static const char text_plain[] = "text/plain";


#define CRLF \
  *(self->buffer + buffer_offset) = '\r'; \
  buffer_offset++; \
  *(self->buffer + buffer_offset) = '\n'; \
  buffer_offset++;


#define bfrcpy(data, len) \
  if(buffer_offset + len > self->buffer_len) \
  { \
    self->buffer_len = MAX(self->buffer_len * 2, self->buffer_len + len); \
    \
    if(self->buffer == self->inline_buffer) \
    { \
      self->buffer = malloc(self->buffer_len); \
      if(!self->buffer) \
        assert(0); \
      memcpy(self->buffer, self->inline_buffer, buffer_offset); \
    } else { \
      self->buffer = realloc(self->buffer, self->buffer_len); \
      if(!self->buffer) \
        assert(0); \
    } \
  } \
  \
  memcpy(self->buffer + buffer_offset, data, len); \
  buffer_offset += len;

#ifdef RESPONSE_CACHE

typedef struct {
  PyObject* body;
  PyObject* response_bytes;
} CacheEntry;

#define CACHE_LEN 10
#define CACHE_CUTOFF 4096

typedef struct {
  size_t end;
  CacheEntry entries[CACHE_LEN];
} Cache;

static Cache cache = {0};

#define Bytes_AS_STRING(op) ((PyBytesObject *)op)->ob_sval

#define Response_cacheable(r, simple) \
  simple && r->body && Py_SIZE(r->body) < CACHE_CUTOFF \
  && !r->code && !r->headers && !r->cookies && !r->mime_type \
  && !r->encoding && r->minor_version == 1 && r->keep_alive == KEEP_ALIVE_TRUE

static inline PyObject*
Response_from_cache(PyObject* body)
{
  CacheEntry* cache_entry;
  for(cache_entry = cache.entries; cache_entry < cache.entries + cache.end;
      cache_entry++) {
    if(Py_SIZE(cache_entry->body) != Py_SIZE(body))
      continue;

    if(memcmp(Bytes_AS_STRING(cache_entry->body), Bytes_AS_STRING(body), Py_SIZE(body)) != 0)
      continue;

    Py_INCREF(cache_entry->response_bytes);
    return cache_entry->response_bytes;
  }

  return NULL;
}


static inline void
Response_cache(PyObject* body, PyObject* response_bytes)
{
  if(cache.end == CACHE_LEN)
    return;

  CacheEntry* entry = cache.entries + cache.end;
  entry->body = body;
  entry->response_bytes = response_bytes;

  Py_INCREF(body);
  Py_INCREF(response_bytes);
  cache.end++;
}

#endif


PyObject*
Response_render(Response* self, bool simple)
{
  PyObject* response_bytes = NULL;
  PyObject* cookies_str = NULL;
  PyObject* cookies_bytes = NULL;

#ifdef RESPONSE_CACHE
  bool cacheable = Response_cacheable(self, simple);
  if(cacheable && (response_bytes = Response_from_cache(self->body)))
    return response_bytes;
#endif

  size_t buffer_offset;
  Py_ssize_t body_len = 0;
  const char* body = NULL;

  *(self->buffer + minor_offset) = '0' + (char)self->minor_version;

  if(self->code) {
    unsigned long code = PyLong_AsUnsignedLong(self->code);

    if(code < 100 || code > 599) {
      PyErr_SetString(PyExc_ValueError, "Invalid status code");
      goto error;
    }

    unsigned int status_category = code / 100 - 1;
    unsigned int status_rest = code % 100;

    const ReasonRange* reason_range = reason_ranges + status_category;
    if(status_rest > reason_range->maximum) {
      PyErr_SetString(PyExc_ValueError, "Invalid status code");
      goto error;
    }

    /* TODO these are always 3 digit, maybe modulus would be faster */
    snprintf(self->buffer + code_offset, 4, "%ld", code);
    *(self->buffer + code_offset + 3) = ' ';

    const char* reason = reason_range->reasons[status_rest];
    size_t reason_len = strlen(reason);


    memcpy(self->buffer + reason_offset, reason, reason_len);
    buffer_offset = reason_offset + reason_len;

    CRLF

    memcpy(self->buffer + buffer_offset, "Content-Length: ", strlen("Content-Length: "));
    buffer_offset += strlen("Content-Length: ");
  } else {
    memcpy(self->buffer + code_offset, "200", 3);
    buffer_offset = strlen(header);
  }

  if(self->body) {
    if(PyBytes_AsStringAndSize(self->body, (char**)&body, &body_len) == -1)
      goto error;

    int result = sprintf(
      self->buffer + buffer_offset, "%ld", (unsigned long)body_len);
    buffer_offset += result;
  } else {
    *(self->buffer + buffer_offset) = '0';
    buffer_offset++;
  }

  CRLF

  if(self->minor_version == 1 && self->keep_alive == KEEP_ALIVE_FALSE) {
    memcpy(
      self->buffer + buffer_offset, "Connection: close\r\n",
      strlen("Connection: close\r\n"));
    buffer_offset += strlen("Connection: close\r\n");
  } else if(self->minor_version == 0 && self->keep_alive == KEEP_ALIVE_TRUE) {
    memcpy(
      self->buffer + buffer_offset, "Connection: keep-alive\r\n",
      strlen("Connection: keep-aplive\r\n"));
    buffer_offset += strlen("Connection: keep-alive\r\n");
  }

  // dont output Content-Type if there is no body
  if(!self->body)
    goto headers;

  memcpy(self->buffer + buffer_offset, Content_Type, strlen(Content_Type));
  buffer_offset += strlen(Content_Type);

  Py_ssize_t mime_type_len = strlen(text_plain);
  const char* mime_type = text_plain;
  if(self->mime_type) {
    mime_type = PyUnicode_AsUTF8AndSize(self->mime_type, &mime_type_len);
    if(!mime_type)
      goto error;

  }
  memcpy(self->buffer + buffer_offset, mime_type, (size_t)mime_type_len);
  buffer_offset += mime_type_len;

  Py_ssize_t encoding_len = strlen(utf8);
  const char* encoding = utf8;
  if(self->encoding) {
    encoding = PyUnicode_AsUTF8AndSize(self->encoding, &encoding_len);
    if(!encoding)
      goto error;
  }

  #define text_or_json \
    (mime_type_len >= 5 \
     && (memcmp(mime_type, "text/", 5) == 0 \
         || memcmp(mime_type + mime_type_len - 5, "/json", 5) == 0))

  if(self->encoding || text_or_json) {
    memcpy(self->buffer + buffer_offset, charset, strlen(charset));
    buffer_offset += strlen(charset);

    memcpy(self->buffer + buffer_offset, encoding, (size_t)encoding_len);
    buffer_offset += (size_t)encoding_len;
  }

  CRLF

  headers:

  if(!self->headers)
    goto empty_headers;

  Py_ssize_t headers_len;
  if((headers_len = PyDict_Size(self->headers)) < 0)
    goto error;

  if(!headers_len)
    goto empty_headers;

  PyObject *name, *value;
  Py_ssize_t pos = 0;

  while (PyDict_Next(self->headers, &pos, &name, &value)) {
    const char* cname;
    Py_ssize_t name_len;
    const char* cvalue;
    Py_ssize_t value_len;

    if(!(cname = PyUnicode_AsUTF8AndSize(name, &name_len)))
      goto error;

    memcpy(self->buffer + buffer_offset, cname, (size_t)name_len);
    buffer_offset += (size_t)name_len;

    *(self->buffer + buffer_offset) = ':';
    buffer_offset++;
    *(self->buffer + buffer_offset) = ' ';
    buffer_offset++;

    if(!(cvalue = PyUnicode_AsUTF8AndSize(value, &value_len)))
      goto error;

    memcpy(self->buffer + buffer_offset, cvalue, (size_t)value_len);
    buffer_offset += (size_t)value_len;

    CRLF
  }

  empty_headers:

  if(!self->cookies)
    goto empty_cookies;

  Py_ssize_t cookies_len;
  if((cookies_len = PyObject_Size(self->cookies)) < 0)
    goto error;

  if(!cookies_len)
    goto empty_cookies;

  if(!(cookies_str = PyObject_Str(self->cookies)))
    goto error;

  if(!(cookies_bytes = PyUnicode_AsASCIIString(cookies_str)))
    goto error;

  char* ccookies;
  Py_ssize_t ccookies_len;
  if(PyBytes_AsStringAndSize(cookies_bytes, &ccookies, &ccookies_len) == -1)
    goto error;

  memcpy(self->buffer + buffer_offset, ccookies, (size_t)ccookies_len);
  buffer_offset += (size_t)ccookies_len;

  CRLF

  empty_cookies:
  CRLF

  if(body) {
    bfrcpy(body, (size_t)body_len)
  }

#undef CRLF

  if(!(response_bytes = PyBytes_FromStringAndSize(self->buffer, buffer_offset)))
    goto error;

#ifdef RESPONSE_CACHE
  if(cacheable)
    Response_cache(self->body, response_bytes);
#endif

  goto finally;

  error:
  Py_XDECREF(response_bytes);
  response_bytes = NULL;

  finally:
  Py_XDECREF(cookies_str);
  Py_XDECREF(cookies_bytes);

  return response_bytes;
}


static PyMethodDef Response_methods[] = {
  //{"render", (PyCFunction)Response_render, METH_NOARGS, "render"},
  {NULL}
};


static PyTypeObject ResponseType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "cresponse.Response",      /* tp_name */
  sizeof(Response),          /* tp_basicsize */
  0,                         /* tp_itemsize */
  (destructor)Response_dealloc, /* tp_dealloc */
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
  "Response",                /* tp_doc */
  0,                         /* tp_traverse */
  0,                         /* tp_clear */
  0,                         /* tp_richcompare */
  0,                         /* tp_weaklistoffset */
  0,                         /* tp_iter */
  0,                         /* tp_iternext */
  Response_methods,          /* tp_methods */
  0,                         /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)Response_init,   /* tp_init */
  0,                         /* tp_alloc */
  Response_new,              /* tp_new */
};


static PyModuleDef cresponse = {
  PyModuleDef_HEAD_INIT,
  "cresponse",
  "cresponse",
  -1,
  NULL, NULL, NULL, NULL, NULL
};


PyMODINIT_FUNC
PyInit_cresponse(void)
{
  PyObject* m = NULL;
  PyObject* api_capsule = NULL;
  PyObject* json = NULL;

  if (PyType_Ready(&ResponseType) < 0)
    goto error;

  m = PyModule_Create(&cresponse);
  if(!m)
    goto error;

  Py_INCREF(&ResponseType);
  PyModule_AddObject(m, "Response", (PyObject*)&ResponseType);

  if(!(json = PyImport_ImportModule("json")))
    goto error;

  if(!(json_dumps = PyObject_GetAttrString(json, "dumps")))
    goto error;

  if(!(application_json = PyUnicode_FromString("application/json")))
    goto error;

  if(!(application_octet = PyUnicode_FromString("application/octet-stream")))
    goto error;

  static Response_CAPI capi = {
    &ResponseType,
    Response_render,
    Response_init
  };
  api_capsule = export_capi(m, "japronto.response.cresponse", &capi);
  if(!api_capsule)
    goto error;

  goto finally;

  error:
  m = NULL;
  finally:
  Py_XDECREF(json);
  Py_XDECREF(api_capsule);
  return m;
}
#endif
