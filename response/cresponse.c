#include <Python.h>


typedef struct {
  PyObject_HEAD

  PyObject* status_code;
  PyObject* mime_type;
  PyObject* text;
  PyObject* encoding;

  char buffer[1024];
} Response;


static const char header[] = "HTTP/1.1 200 OK\r\n"
  "Connection: keep-alive\r\n"
  "Content-Length: ";

static PyObject *
Response_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
  Response* self = NULL;

  self = (Response*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

  self->status_code = Py_None;
  Py_INCREF(self->status_code);
  self->mime_type = Py_None;
  Py_INCREF(self->mime_type);
  self->text = Py_None;
  Py_INCREF(self->text);
  self->encoding = Py_None;
  Py_INCREF(self->encoding);

  memcpy(self->buffer, header, strlen(header));

  finally:
  return (PyObject*)self;
}


static void
Response_dealloc(Response* self)
{
  Py_XDECREF(self->encoding);
  Py_XDECREF(self->text);
  Py_XDECREF(self->mime_type);
  Py_XDECREF(self->status_code);

  Py_TYPE(self)->tp_free((PyObject*)self);
}

static const size_t code_offset = 9;

static int
Response_init(Response* self, PyObject *args, PyObject *kw)
{
  static char *kwlist[] = {"status_code", "text", "mime_type", "encoding", NULL};

  PyObject* status_code = Py_None;
  PyObject* text = Py_None;
  PyObject* mime_type = Py_None;
  PyObject* encoding = Py_None;

  // FIXME: check argument types
  if (!PyArg_ParseTupleAndKeywords(
      args, kw, "|OOOO", kwlist,
      &status_code, &text, &mime_type, &encoding))
      goto error;


  Py_DECREF(self->status_code);
  self->status_code = status_code;
  Py_INCREF(self->status_code);

  Py_DECREF(self->text);
  self->text = text;
  Py_INCREF(self->text);

  Py_DECREF(self->mime_type);
  self->mime_type = mime_type;
  Py_INCREF(self->mime_type);

  Py_DECREF(self->encoding);
  self->encoding = encoding;
  Py_INCREF(self->encoding);

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

static PyObject*
Response_render(Response* self)
{
  if(self->status_code != Py_None) {
    unsigned long status_code = PyLong_AsUnsignedLong(self->status_code);
    /* FIXME: overflow, check range 100 - 599 */
    /* TODO these are always 3 digit, maybe modulus would be faster */
    snprintf(self->buffer + code_offset, 4, "%ld", status_code);
    *(self->buffer + code_offset + 3) = ' ';
  } else {
    memcpy(self->buffer + code_offset, "200", 3);
  }

  size_t buffer_offset = strlen(header);

  Py_ssize_t body_len = 0;
  const char* body = NULL;
  if(self->text != Py_None) {
    if(self->encoding == Py_None) {
      body = PyUnicode_AsUTF8AndSize(self->text, &body_len);
      if(!body)
        goto error;
    } else {
      /* TODO handle other encodings */
    }

    int result = sprintf(
      self->buffer + buffer_offset, "%ld", (unsigned long)body_len);
    buffer_offset += result;
  } else {
    *(self->buffer + buffer_offset) = '0';
    buffer_offset++;
  }

# define CRLF \
  *(self->buffer + buffer_offset) = '\r'; \
  buffer_offset++; \
  *(self->buffer + buffer_offset) = '\n'; \
  buffer_offset++;

  CRLF

  memcpy(self->buffer + buffer_offset, Content_Type, strlen(Content_Type));
  buffer_offset += strlen(Content_Type);

  Py_ssize_t mime_type_len = strlen(text_plain);
  const char* mime_type = text_plain;
  if(self->mime_type != Py_None) {
    mime_type = PyUnicode_AsUTF8AndSize(self->mime_type, &mime_type_len);
    if(!mime_type)
      goto error;

  }
  memcpy(self->buffer + buffer_offset, mime_type, (size_t)mime_type_len);
  buffer_offset += mime_type_len;
  memcpy(self->buffer + buffer_offset, charset, strlen(charset));
  buffer_offset += strlen(charset);

  Py_ssize_t encoding_len = strlen(utf8);
  const char* encoding = utf8;
  if(self->encoding != Py_None) {
    encoding = PyUnicode_AsUTF8AndSize(self->encoding, &encoding_len);
    if(!encoding)
      goto error;
  }
  memcpy(self->buffer + buffer_offset, encoding, (size_t)encoding_len);
  buffer_offset += (size_t)encoding_len;

  CRLF
  CRLF

  if(body) {
    memcpy(self->buffer + buffer_offset, body, (size_t)body_len);
    buffer_offset += (size_t)body_len;
  }

#undef CRLF

  /* FIXME we should implement buffer protocol instead */
  PyObject* view = PyMemoryView_FromMemory(
    self->buffer, buffer_offset, PyBUF_READ);
  if(!view)
    goto error;

  return view;

  error:
    return NULL;
}


static PyMethodDef Response_methods[] = {
  {"render", (PyCFunction)Response_render, METH_NOARGS, "render"},
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

  if (PyType_Ready(&ResponseType) < 0)
    goto error;

  m = PyModule_Create(&cresponse);
  if(!m)
    goto error;

  Py_INCREF(&ResponseType);
  PyModule_AddObject(m, "Response", (PyObject*)&ResponseType);

  error:
  finally:
  return m;
}
