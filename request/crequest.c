#include <stddef.h>

#include "crequest.h"

#include "cresponse.h"
#ifdef REQUEST_OPAQUE
#include "picohttpparser.h"
#endif
#include "capsule.h"

static PyObject* PyResponse;

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

  self->py_method = NULL;
  self->py_path = NULL;
  self->py_qs = NULL;
  self->py_headers = NULL;
  self->py_match_dict = NULL;
  self->py_body = NULL;
  Response_new(response_capi->ResponseType, &self->response);

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
  Response_dealloc(&self->response);
  Py_XDECREF(self->py_body);
  Py_XDECREF(self->py_match_dict);
  Py_XDECREF(self->py_headers);
  Py_XDECREF(self->py_qs);
  Py_XDECREF(self->py_path);
  Py_XDECREF(self->py_method);
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

  const size_t offset = offsetof(Request, method_len);
  const size_t length = offsetof(Request, py_method) - offset;

  memcpy((char*)clone + offset, (char*)original + offset, length);

  goto finally;

  error:
  Py_XDECREF(clone);
  clone = NULL;

  finally:
  return (PyObject*)clone;
}


static PyObject*
Request_Response(Request* self, PyObject *args, PyObject* kw)
{
  Response* result = &self->response;

  if(response_capi->Response_init(result, args, kw) == -1)
    goto error;

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XINCREF(result);
  return (PyObject*)result;
}


static void
Request_from_raw(Request* self, char* method, size_t method_len, char* path, size_t path_len,
                 int minor_version,
                 struct phr_header* headers, size_t num_headers)
{
  // copy the whole block;
  struct phr_header* last_header = &headers[num_headers - 1];
  size_t span = last_header->value + last_header->value_len - method;
  memcpy(self->buffer, method, span);
  memcpy(self->buffer + span, headers, sizeof(struct phr_header) * num_headers);
  headers = (struct phr_header*)(self->buffer + span);

  // correct offsets
  ptrdiff_t shift = self->buffer - method;
  path += shift;
  for(struct phr_header* header = headers; header < headers + num_headers;
      header++) {
    header->name += shift;
    header->value += shift;
  }

  // fill
  self->method_len = method_len;
  self->path = path;
  self->path_decoded = false;
  self->path_len = path_len;
  self->qs_decoded = false;
  self->minor_version = minor_version;
  self->headers = headers;
  self->num_headers = num_headers;
}


static void
Request_set_match_dict_entries(Request* self, MatchDictEntry* entries,
                               size_t length)
{
  self->match_dict_entries =
    (MatchDictEntry*)(&self->headers[self->num_headers]);
  self->match_dict_length = length;
  assert(
    (char*)self->match_dict_entries + sizeof(MatchDictEntry) * length <=
    self->buffer + sizeof(self->buffer));
  memcpy(self->match_dict_entries, entries, sizeof(MatchDictEntry) * length);
}


static void
Request_set_body(Request* self, char* body, size_t body_len)
{
  if(!body) {
    self->body = NULL;
    return;
  }

  self->body = (char*)self->match_dict_entries + sizeof(MatchDictEntry)
    * self->match_dict_length;
  self->body_length = body_len;
  assert(self->body + self->body_length <= self->buffer + sizeof(self->buffer));
  memcpy(self->body, body, body_len);
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
      end -= 2;
      length -= 2;
      if(shifted_bytes)
        *shifted_bytes += 2;
      memmove(data + 1, data + 3, length - 1);
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
    if(self->qs_len)
      self->qs_len--;

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

  char* qs = self->path + self->path_len + 1;

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
  if(!self->py_method)
    self->py_method = PyUnicode_FromStringAndSize(
      REQUEST_METHOD(self), self->method_len);

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
      self->py_qs = Py_None;
    else
      self->py_qs = PyUnicode_FromStringAndSize(qs, qs_len);
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
  if(!self->py_body) {
    if(self->body)
      self->py_body = PyBytes_FromStringAndSize(self->body, self->body_length);
    else
      self->py_body = Py_None;
  }

  Py_XINCREF(self->py_body);
  return self->py_body;
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
  PROXY(text),
  PROXY(json),
  PROXY(query),
  PROXY(mime_type),
  PROXY(encoding),
  PROXY(form),
  {NULL}
};

#undef PROXY


static PyMethodDef Request_methods[] = {
  {"Response", (PyCFunction)Request_Response, METH_VARARGS | METH_KEYWORDS, ""},
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
  0,                         /* tp_getattro */
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

  cresponse = PyImport_ImportModule("response.cresponse");
  if(!cresponse)
    goto error;

  PyResponse = PyObject_GetAttrString(cresponse, "Response");
  if(!PyResponse)
    goto error;

#ifdef REQUEST_OPAQUE
  request = PyImport_ImportModule("request");
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
  api_capsule = export_capi(m, "request.crequest", &capi);
  if(!api_capsule)
    goto error;

#endif
  response_capi = import_capi("response.cresponse");
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
  Py_XDECREF(cresponse);
#ifdef REQUEST_OPAQUE
  Py_XDECREF(api_capsule);
#endif
  return m;
}
