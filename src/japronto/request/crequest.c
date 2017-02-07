#include <stddef.h>
#include <sys/param.h>
#include <strings.h>
#include <string.h>

#include "crequest.h"

#include "cresponse.h"
#ifdef REQUEST_OPAQUE
#include "picohttpparser.h"
#endif
#include "capsule.h"

static PyObject* PyResponse;
static PyObject* partial;


#ifdef REQUEST_OPAQUE
static PyObject* HTTP10;
static PyObject* HTTP11;
static PyObject* request;
#endif

static Response_CAPI* response_capi;

#ifdef REQUEST_OPAQUE
static PyObject*
Request_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
#else
PyObject*
Request_new(PyTypeObject* type, Request* self)
#endif
{
#ifdef REQUEST_OPAQUE
  Request* self = NULL;

  self = (Request*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;
#else
  ((PyObject*)self)->ob_refcnt = 1;
  ((PyObject*)self)->ob_type = type;
#endif
  self->response_called = false;

  self->matcher_entry = NULL;
  self->exception = NULL;
  self->app = NULL;

  self->transport = NULL;
  self->py_method = NULL;
  self->py_path = NULL;
  self->py_qs = NULL;
  self->py_headers = NULL;
  self->py_match_dict = NULL;
  self->py_body = NULL;
  self->extra = NULL;
  self->done_callbacks = NULL;

  Response_new(response_capi->ResponseType, &self->response);

  self->buffer = self->inline_buffer;
  self->buffer_len = REQUEST_INITIAL_BUFFER_LEN;
#ifdef REQUEST_OPAQUE
  finally:
#endif
  return (PyObject*)self;
}


#ifdef REQUEST_OPAQUE
static void
#else
void
#endif
Request_dealloc(Request* self)
{
  if(self->buffer != self->inline_buffer)
    free(self->buffer);

  Response_dealloc(&self->response);
  Py_XDECREF(self->app);
  Py_XDECREF(self->done_callbacks);
  Py_XDECREF(self->extra);
  Py_XDECREF(self->py_body);
  Py_XDECREF(self->py_match_dict);
  Py_XDECREF(self->py_headers);
  Py_XDECREF(self->py_qs);
  Py_XDECREF(self->py_path);
  Py_XDECREF(self->py_method);
  Py_XDECREF(self->transport);

  Py_XDECREF(self->exception);
#ifdef REQUEST_OPAQUE
  Py_TYPE(self)->tp_free((PyObject*)self);
#endif
}


#ifdef REQUEST_OPAQUE
static int
Request_init(Request* self, PyObject *args, PyObject* kw)
#else
int
Request_init(Request* self)
#endif
{
  return 0;
}


#ifdef REQUEST_OPAQUE

static PyTypeObject RequestType;

static PyObject*
Request_clone(Request* original)
{
  Request* clone = NULL;

  if(!(clone = (Request*)Request_new(&RequestType, NULL, NULL)))
    goto error;

  if(Request_init(clone, NULL, NULL) == -1)
    goto error;

  const size_t offset = offsetof(Request, method);
  const size_t length = offsetof(Request, transport) - offset;

  memcpy((char*)clone + offset, (char*)original + offset, length);

  if(original->buffer == original->inline_buffer) {
    clone->buffer = clone->inline_buffer;

    ptrdiff_t shift = (char*)clone - (char*)original;
    clone->method += shift;
    clone->path += shift;
    clone->headers = (struct phr_header*)((char*)clone->headers + shift);
    for(struct phr_header* header = clone->headers;
        header < clone->headers + clone->num_headers;
        header++) {
      header->name += shift;
      header->value += shift;
    }
    clone->match_dict_entries =
      (MatchDictEntry*)((char*)clone->match_dict_entries + shift);
    for(MatchDictEntry* entry = clone->match_dict_entries;
        entry < clone->match_dict_entries + clone->match_dict_length; entry++) {
      // the keys didnt move, they reference immutable memory from the router
      entry->value += shift;
    }
    if(clone->body)
      // body can be NULL
      clone->body += shift;
  } else {
    // just steal the buffer since the original request will be destroyed anyway
    clone->buffer = original->buffer;
    original->buffer = original->inline_buffer;
  }

  goto finally;

  error:
  Py_XDECREF(clone);
  clone = NULL;

  finally:
  return (PyObject*)clone;
}


static KEEP_ALIVE
_Request_get_keep_alive(Request* self);


static PyObject*
Request_Response(Request* self, PyObject *args, PyObject* kw)
{
  if(self->response_called) {
    PyErr_SetString(
      PyExc_RuntimeError,
      "Request.Response can only be called once per request");
    goto error;
  }

  self->response_called = true;
  Response* result = &self->response;

  if(response_capi->Response_init(result, args, kw) == -1)
    goto error;

  result->minor_version = self->minor_version;
  result->keep_alive = _Request_get_keep_alive(self);

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XINCREF(result);
  return (PyObject*)result;
}


typedef enum {
  REQUEST_HEADERS,
  REQUEST_MATCH_DICT,
  REQUEST_BODY
} RequestCopy;


#define ROUNDTO8(v) (((v) + 7) & ~7)


static inline char*
bfrcpy(Request* self, const RequestCopy what)
{
  size_t len;
  char* dst;
  char* old_buffer = self->buffer;
  size_t headers_len;
  size_t header_entries_len;

  if(self->num_headers) {
    struct phr_header* last_header = &self->headers[self->num_headers - 1];
    headers_len = last_header->value + last_header->value_len - self->method;
    header_entries_len = sizeof(struct phr_header) * self->num_headers;
  } else {
    headers_len = self->path + self->path_len + self->qs_len - self->method;
    header_entries_len = 0;
  }

  switch(what) {
    case REQUEST_HEADERS:
    len = ROUNDTO8(headers_len) + header_entries_len;
    dst = self->buffer;
    break;

    case REQUEST_MATCH_DICT:
    len = sizeof(MatchDictEntry) * self->match_dict_length;
    dst = self->buffer + ROUNDTO8(headers_len + header_entries_len);
    break;

    case REQUEST_BODY:
    len = self->body_length;
    dst = (char*)self->match_dict_entries \
      + sizeof(MatchDictEntry) * self->match_dict_length;
    break;

    default:
    assert(0);
  }

  if(dst + len > self->buffer + self->buffer_len)
  {
    self->buffer_len = MAX(self->buffer_len * 2, self->buffer_len + len);

    if(self->buffer == self->inline_buffer)
    {
      self->buffer = malloc(self->buffer_len);
      if(!self->buffer)
        assert(0);
        // TODO, propagate memory error
      memcpy(self->buffer, self->inline_buffer, REQUEST_INITIAL_BUFFER_LEN);
    } else {
      self->buffer = realloc(self->buffer, self->buffer_len);
      if(!self->buffer)
         assert(0);
         // TODO, propagate memory error
    }
  }

  ptrdiff_t buffer_shift = self->buffer - old_buffer;
  dst += buffer_shift;
  ptrdiff_t shift;

  if(what == REQUEST_HEADERS) {
    shift = dst - self->method;

    memcpy(dst, self->method, headers_len);
    self->method += shift;
    self->path += shift;
    memcpy(dst + ROUNDTO8(headers_len), (char*)self->headers, header_entries_len);
    self->headers = (struct phr_header*)((char*)dst + ROUNDTO8(headers_len));
    for(struct phr_header* header = self->headers;
        header < self->headers + self->num_headers;
        header++) {
      header->name += shift;
      header->value += shift;
    }

    goto finally;
  }

  if(buffer_shift) {
    self->method += buffer_shift;
    self->path += buffer_shift;
    self->headers = (struct phr_header*)((char*)self->headers + buffer_shift);
    for(struct phr_header* header = self->headers;
        header < self->headers + self->num_headers;
        header++) {
      header->name += buffer_shift;
      header->value += buffer_shift;
    }
  }

  if(what == REQUEST_HEADERS)
    goto finally;

  if(what == REQUEST_MATCH_DICT) {
    shift = dst - (char*)self->match_dict_entries;

    memcpy(dst, (char*)self->match_dict_entries, len);
    self->match_dict_entries =
      (MatchDictEntry*)((char*)self->match_dict_entries + shift);
    /* match_dict_entires values don't need moving by shift because the block
     * they reference couldn't move (the previous call)
     */
  }

  if(buffer_shift) {
    if(what != REQUEST_MATCH_DICT)
      self->match_dict_entries =
        (MatchDictEntry*)((char*)self->match_dict_entries + buffer_shift);
    for(MatchDictEntry* entry = self->match_dict_entries;
        entry < self->match_dict_entries + self->match_dict_length; entry++) {
      // the keys didnt move, they reference immutable memory from the router
      entry->value += buffer_shift;
    }
  }

  if(what == REQUEST_MATCH_DICT)
    goto finally;

  if(what == REQUEST_BODY) {
    shift = dst - self->body;

    memcpy(dst, self->body, len);
    self->body += shift;

    goto finally;
  }

  assert(0);

  finally:
  return self->buffer;
}


static void
Request_from_raw(Request* self, char* method, size_t method_len, char* path, size_t path_len,
                 int minor_version,
                 struct phr_header* headers, size_t num_headers)
{
  // fill
  self->method = method;
  self->method_len = method_len;
  self->path = path;
  self->path_decoded = false;
  self->path_len = path_len;
  self->qs_len = 0;
  self->qs_decoded = false;
  self->minor_version = minor_version;
  self->headers = headers;
  self->num_headers = num_headers;
  self->keep_alive = KEEP_ALIVE_UNSET;

  bfrcpy(self, REQUEST_HEADERS);
}


static void
Request_set_match_dict_entries(Request* self, MatchDictEntry* entries,
                               size_t length)
{
  self->match_dict_entries = entries;
  self->match_dict_length = length;
  bfrcpy(self, REQUEST_MATCH_DICT);
}


static void
Request_set_body(Request* self, char* body, size_t body_len)
{
  if(!body) {
    self->body = NULL;
    return;
  }

  self->body = body;
  self->body_length = body_len;
  bfrcpy(self, REQUEST_BODY);
}


#define hex_to_dec(x) \
  ((x <= '9' ? 0 : 9) + (x & 0x0f))
#define is_hex(x) ((x >= '0' && x <= '9') || (x >= 'A' && x <= 'F'))
static inline size_t percent_decode(char* data, ssize_t length, size_t* shifted_bytes, const char* stopchr) {
  if(shifted_bytes)
    *shifted_bytes = 0;

  for(char* end = data + length; data < end; data++) {
    if(stopchr && *data == *stopchr) {
      length -= end - data;
      break;
    }

    if(end - data < 3)
      continue;

    if(*data == '%' && is_hex(*(data + 1)) && is_hex(*(data + 2))) {
      *data = (hex_to_dec(*(data + 1)) << 4) + hex_to_dec(*(data + 2));
      length -= 2;
      if(shifted_bytes)
        *shifted_bytes += 2;
      memmove(data + 1, data + 3, end - (data + 3));
      end -= 2;
    }
  }

  return length;
}
#undef hex_to_dec
#undef is_hex


char*
Request_get_decoded_path(Request* self, size_t* path_len) {
  if(!self->path_decoded) {
    size_t shifted_bytes;
    const char stopchr = '?';
    *path_len = percent_decode(
      self->path, self->path_len, &shifted_bytes, &stopchr);
    self->path_decoded = true;

    self->qs_len = self->path_len - *path_len - shifted_bytes;
    self->path_len = *path_len;
  }

  *path_len = self->path_len;
  return self->path;
}


static char*
Request_get_decoded_qs(Request* self, size_t* qs_len) {
  if(!self->qs_len) {
    *qs_len = 0;
    return NULL;
  }

  char* qs = self->path + self->path_len;

  if(!self->qs_decoded) {
    self->qs_len = percent_decode(qs, self->qs_len, NULL, NULL);
    self->qs_decoded = true;
  }

  *qs_len = self->qs_len;
  return qs;
}


static inline void title_case(char* data, size_t len)
{
  bool prev_alpha = false;
  for(char* c = data; c < data + len; c++) {
    if(*c >= 'A' && *c <= 'Z') {
      if(prev_alpha)
        *c ^= 0x20;
      prev_alpha = true;
    } else if (*c >= 'a' && *c <= 'z') {
      if(!prev_alpha)
        *c ^= 0x20;
      prev_alpha = true;
    } else
      prev_alpha = false;
  }
}


static inline PyObject*
Request_decode_headers(Request* self)
{
  PyObject* result = NULL;
  PyObject* headers = PyDict_New();
  if(!headers)
    goto error;
  result = headers;

  for(struct phr_header* header = self->headers;
      header < self->headers + self->num_headers;
      header++) {

      PyObject* name = NULL;
      PyObject* value = NULL;

      title_case((char*)header->name, header->name_len);
      // TODO by inserting 0 byte we could call PyDict_SetItemString

      // FIXME check ASCII
      name = PyUnicode_FromStringAndSize(header->name, header->name_len);
      if(!name)
        goto loop_error;

      // FIXME this can fail on codec errors
      value = PyUnicode_DecodeLatin1(header->value, header->value_len, NULL);
      if(!value)
        goto loop_error;

      if(PyDict_SetItem(headers, name, value) == -1)
        goto loop_error;

      goto loop_finally;

      loop_error:
      result = NULL;

      loop_finally:
      Py_XDECREF(name);
      Py_XDECREF(value);

      if(!result)
        goto error;
  }

  goto finally;

  error:
  Py_XDECREF(headers);
  result = NULL;

  finally:
  return result;
}


static PyObject*
Request_get_method(Request* self, void* closure)
{
  if(!self->py_method) {
    self->py_method = PyUnicode_DecodeLatin1(
      REQUEST_METHOD(self), self->method_len, NULL);
  }

  Py_XINCREF(self->py_method);
  return self->py_method;
}


static PyObject*
Request_get_path(Request* self, void* closure)
{
  if(!self->py_path) {
    size_t path_len;
    char* path = Request_get_decoded_path(self, &path_len);
    self->py_path = PyUnicode_FromStringAndSize(path, path_len);
  }

  Py_XINCREF(self->py_path);
  return self->py_path;
}


static PyObject*
Request_get_qs(Request* self, void* closure)
{
  if(!self->py_qs) {
    size_t qs_len;
    char* qs = Request_get_decoded_qs(self, &qs_len);
    if(!qs)
      Py_RETURN_NONE;

    // skip the ? char
    self->py_qs = PyUnicode_FromStringAndSize(qs + 1, qs_len - 1);
  }

  Py_XINCREF(self->py_qs);
  return self->py_qs;
}


static PyObject*
Request_get_version(Request* self, void* closure) {
  PyObject* result = self->minor_version ? HTTP11 : HTTP10;

  Py_INCREF(result);
  return result;
}


static PyObject*
Request_get_headers(Request* self, void* closure) {
  if(!self->py_headers)
    self->py_headers = Request_decode_headers(self);

  Py_XINCREF(self->py_headers);
  return self->py_headers;
}


static PyObject*
Request_get_match_dict(Request* self, void* closure)
{
  if(!self->py_match_dict)
    self->py_match_dict = MatchDict_entries_to_dict(
      self->match_dict_entries, self->match_dict_length);

  Py_XINCREF(self->py_match_dict);
  return self->py_match_dict;
}


static PyObject*
Request_get_body(Request* self, void* closure)
{
  if(!self->body)
    Py_RETURN_NONE;

  if(!self->py_body)
      self->py_body = PyBytes_FromStringAndSize(self->body, self->body_length);

  Py_XINCREF(self->py_body);
  return self->py_body;
}


static PyObject*
Request_get_transport(Request* self, void* closure)
{
  Py_INCREF(self->transport);
  return self->transport;
}


static KEEP_ALIVE
_Request_get_keep_alive(Request* self)
{
  if(self->keep_alive == KEEP_ALIVE_UNSET) {
    struct phr_header* Connection = NULL;
    for(struct phr_header* header = self->headers;
        header < self->headers + self->num_headers;
        header++) {
        if(header->name_len == strlen("Connection")
          && strncasecmp(header->name, "Connection", header->name_len) == 0) {
          Connection = header;
          break;
        }
    }

    if(self->minor_version == 0) {
      // FIXME: this should check what's before and after
      if(Connection &&
        memmem(Connection->value, Connection->value_len,
          "keep-alive", strlen("keep-alive")))
        self->keep_alive = KEEP_ALIVE_TRUE;
      else
        self->keep_alive = KEEP_ALIVE_FALSE;
    } else {
      if(Connection &&
        memmem(Connection->value, Connection->value_len,
          "close", strlen("close")))
        self->keep_alive = KEEP_ALIVE_FALSE;
      else
        self->keep_alive = KEEP_ALIVE_TRUE;
    }
  }

  return self->keep_alive;
}


static PyObject*
Request_get_keep_alive(Request* self, void* closure)
{
  if(_Request_get_keep_alive(self) == KEEP_ALIVE_TRUE)
    Py_RETURN_TRUE;
  else
    Py_RETURN_FALSE;
}


static PyObject*
Request_get_route(Request* self, void* closure)
{
  if(!self->matcher_entry)
    Py_RETURN_NONE;

  Py_INCREF(self->matcher_entry->route);
  return self->matcher_entry->route;
}


static PyObject*
Request_get_extra(Request* self, void* closure)
{
  if(!self->extra)
    self->extra = PyDict_New();

  Py_XINCREF(self->extra);
  return self->extra;
}


static PyObject*
Request_get_app(Request* self, void* app)
{
  Py_INCREF(self->app);
  return self->app;
}


static PyObject*
Request_get_proxy(Request* self, char* attr)
{
  PyObject* callable = NULL;
  PyObject* result = NULL;
  if(!(callable = PyObject_GetAttrString(request, attr)))
    goto error;

  if(!(result = PyObject_CallFunctionObjArgs(callable, self, NULL)))
    goto error;

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(callable);

  return result;
}


#define PROXY(attr) \
  {#attr, (getter)Request_get_proxy, NULL, "", #attr}

static PyGetSetDef Request_getset[] = {
  {"method", (getter)Request_get_method, NULL, "", NULL},
  {"path", (getter)Request_get_path, NULL, "", NULL},
  {"query_string", (getter)Request_get_qs, NULL, "", NULL},
  {"version", (getter)Request_get_version, NULL, "", NULL},
  {"headers", (getter)Request_get_headers, NULL, "", NULL},
  {"match_dict", (getter)Request_get_match_dict, NULL, "", NULL},
  {"body", (getter)Request_get_body, NULL, "", NULL},
  {"transport", (getter)Request_get_transport, NULL, "", NULL},
  {"keep_alive", (getter)Request_get_keep_alive, NULL, "", NULL},
  {"route", (getter)Request_get_route, NULL, "", NULL},
  {"extra", (getter)Request_get_extra, NULL, "", NULL},
  {"app", (getter)Request_get_app, NULL, "", NULL},
  PROXY(text),
  PROXY(json),
  PROXY(query),
  PROXY(mime_type),
  PROXY(encoding),
  PROXY(form),
  PROXY(files),
  PROXY(remote_addr),
  PROXY(hostname),
  PROXY(port),
  PROXY(cookies),
  {NULL}
};

#undef PROXY

static PyObject*
Request_getattro(Request* self, PyObject* name)
{
  PyObject* result;

  if((result = PyObject_GenericGetAttr((PyObject*)self, name)))
    return result;

  PyObject* extensions = NULL;
  if(!(extensions = PyObject_GetAttrString(self->app, "_request_extensions")))
    goto error;

  PyObject* entry;
  if(!(entry = PyDict_GetItem(extensions, name)))
    goto error;
  else
    PyErr_Clear();

  PyObject* handler;
  PyObject* property;
  if(!(handler = PyTuple_GetItem(entry, 0)))
    goto error;

  if(!(property = PyTuple_GetItem(entry, 1)))
    goto error;

  if(property == Py_True) {
    if(!(result = PyObject_CallFunctionObjArgs(handler, self, NULL)))
      goto error;
  } else {
    if(!(result = PyObject_CallFunctionObjArgs(partial, handler, self, NULL)))
      goto error;
  }

  error:
  Py_XDECREF(extensions);

  return result;
}


static PyObject*
Request_add_done_callback(Request* self, PyObject* callback)
{
  if(!self->done_callbacks) {
    if(!(self->done_callbacks = PyList_New(0)))
      goto error;
  }

  if(PyList_Append(self->done_callbacks, callback) == -1)
    goto error;

  Py_RETURN_NONE;

  error:
  return NULL;
}


static PyMethodDef Request_methods[] = {
  {"Response", (PyCFunction)Request_Response, METH_VARARGS | METH_KEYWORDS, ""},
  {"add_done_callback", (PyCFunction)Request_add_done_callback, METH_O, ""},
  {NULL}
};


static PyTypeObject RequestType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "crequest.Request",      /* tp_name */
  sizeof(Request),          /* tp_basicsize */
  0,                         /* tp_itemsize */
  (destructor)Request_dealloc, /* tp_dealloc */
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
  (getattrofunc)Request_getattro, /* tp_getattro */
  0,                         /* tp_setattro */
  0,                         /* tp_as_buffer */
  Py_TPFLAGS_DEFAULT,        /* tp_flags */
  "Request",                /* tp_doc */
  0,                         /* tp_traverse */
  0,                         /* tp_clear */
  0,                         /* tp_richcompare */
  0,                         /* tp_weaklistoffset */
  0,                         /* tp_iter */
  0,                         /* tp_iternext */
  Request_methods,           /* tp_methods */
  0,                         /* tp_members */
  Request_getset,            /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)Request_init,    /* tp_init */
  0,                         /* tp_alloc */
  Request_new,              /* tp_new */
};


static PyModuleDef crequest = {
  PyModuleDef_HEAD_INIT,
  "crequest",
  "crequest",
  -1,
  NULL, NULL, NULL, NULL, NULL
};
#endif

#ifdef REQUEST_OPAQUE
PyMODINIT_FUNC
PyInit_crequest(void)
#else
void*
crequest_init(void)
#endif
{
#ifdef REQUEST_OPAQUE
  PyObject* m = NULL;
  PyObject* api_capsule = NULL;

  HTTP10 = NULL;
  HTTP11 = NULL;
#else
  void* m = (void*)1;
#endif
  PyObject* cresponse = NULL;
  PyObject* functools = NULL;
  PyResponse = NULL;

#ifdef REQUEST_OPAQUE
  if (PyType_Ready(&RequestType) < 0)
    goto error;

#define alloc_static2(name, val) \
    name = PyUnicode_FromString(val); \
    if(!name) \
      goto error;

  alloc_static2(HTTP10, "1.0")
  alloc_static2(HTTP11, "1.1")

  m = PyModule_Create(&crequest);
  if(!m)
    goto error;
#endif

  cresponse = PyImport_ImportModule("japronto.response.cresponse");
  if(!cresponse)
    goto error;

  if(!(functools = PyImport_ImportModule("functools")))
    goto error;

  if(!(partial = PyObject_GetAttrString(functools, "partial")))
    goto error;

  PyResponse = PyObject_GetAttrString(cresponse, "Response");
  if(!PyResponse)
    goto error;

#ifdef REQUEST_OPAQUE
  request = PyImport_ImportModule("japronto.request");
  if(!request)
    goto error;

  Py_INCREF(&RequestType);
  PyModule_AddObject(m, "Request", (PyObject*)&RequestType);

  static Request_CAPI capi = {
    &RequestType,
    Request_clone,
    Request_from_raw,
    Request_get_decoded_path,
    Request_set_match_dict_entries,
    Request_set_body
  };
  api_capsule = export_capi(m, "japronto.request.crequest", &capi);
  if(!api_capsule)
    goto error;

#endif
  response_capi = import_capi("japronto.response.cresponse");
  if(!response_capi)
    goto error;

  goto finally;

  error:
  Py_XDECREF(PyResponse);
#ifdef REQUEST_OPAQUE
  Py_XDECREF(HTTP10);
  Py_XDECREF(HTTP11);
#endif
  m = NULL;

  finally:
  Py_XDECREF(functools);
  Py_XDECREF(cresponse);
#ifdef REQUEST_OPAQUE
  Py_XDECREF(api_capsule);
#endif
  return m;
}
