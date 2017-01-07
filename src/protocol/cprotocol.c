#include <Python.h>


#include "cprotocol.h"
#include "cmatcher.h"
#include "crequest.h"
#include "cresponse.h"
#include "capsule.h"
#include "match_dict.h"

#ifdef PARSER_STANDALONE
static PyObject* Parser;
#endif
static PyObject* PyRequest;

static PyObject* socket_str;
static PyObject* one;
static PyObject* IPPROTO_TCP;
static PyObject* TCP_NODELAY;

static Request_CAPI* request_capi;
static Matcher_CAPI* matcher_capi;
static Response_CAPI* response_capi;


static PyObject *
Protocol_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
  Protocol* self = NULL;

  self = (Protocol*)type->tp_alloc(type, 0);
  if(!self)
    goto finally;

#ifdef PARSER_STANDALONE
  self->feed = NULL;
  self->feed_disconnect = NULL;
#else
  Parser_new(&self->parser);
#endif
  Pipeline_new(&self->pipeline);
  Request_new(request_capi->RequestType, &self->static_request);
  self->app = NULL;
  self->matcher = NULL;
  self->error_handler = NULL;
  self->transport = NULL;
  self->write = NULL;
  self->create_task = NULL;

  finally:
  return (PyObject*)self;
}


static void
Protocol_dealloc(Protocol* self)
{
  Py_XDECREF(self->create_task);
  Py_XDECREF(self->write);
  Py_XDECREF(self->transport);
  Py_XDECREF(self->error_handler);
  Py_XDECREF(self->matcher);
  Py_XDECREF(self->app);
  Request_dealloc(&self->static_request);
  Pipeline_dealloc(&self->pipeline);
#ifdef PARSER_STANDALONE
  Py_XDECREF(self->feed_disconnect);
  Py_XDECREF(self->feed);
#else
  Parser_dealloc(&self->parser);
#endif

  Py_TYPE(self)->tp_free((PyObject*)self);
}


static void* Protocol_pipeline_ready(PipelineEntry entry, void* closure);


static int
Protocol_init(Protocol* self, PyObject *args, PyObject *kw)
{
  int result = 0;
  PyObject* loop = NULL;
#ifdef PARSER_STANDALONE
  PyObject* parser = NULL;

  PyObject* on_headers = PyObject_GetAttrString((PyObject*)self, "on_headers");
  if(!on_headers) // FIXME leak
    goto error;
  PyObject* on_body = PyObject_GetAttrString((PyObject*)self, "on_body");
  if(!on_body) // FIXME leak
    goto error;
  PyObject* on_error = PyObject_GetAttrString((PyObject*)self, "on_error");
  if(!on_error) // FIXME leak
    goto error;

  parser = PyObject_CallFunctionObjArgs(
    Parser, on_headers, on_body, on_error, NULL);
  if(!parser)
    goto error;

  self->feed = PyObject_GetAttrString(parser, "feed");
  if(!self->feed)
    goto error;

  self->feed_disconnect = PyObject_GetAttrString(parser, "feed_disconnect");
  if(!self->feed_disconnect)
    goto error;
#else
  if(Parser_init(&self->parser, self) == -1)
    goto error;
#endif

  if(Pipeline_init(&self->pipeline, Protocol_pipeline_ready, self) == -1)
    goto error;

  if(Request_init(&self->static_request) == -1)
    goto error;

  if(!PyArg_ParseTuple(args, "O", &self->app))
    goto error;
  Py_INCREF(self->app);

  self->matcher = PyObject_GetAttrString(self->app, "_matcher");
  if(!self->matcher)
    goto error;

  self->error_handler = PyObject_GetAttrString(self->app, "error_handler");
  if(!self->error_handler)
    goto error;

  loop = PyObject_GetAttrString(self->app, "_loop");
  if(!loop)
    goto error;

  self->create_task = PyObject_GetAttrString(loop, "create_task");
  if(!self->create_task)
    goto error;

  goto finally;

  error:
  result = -1;
  finally:
  Py_XDECREF(loop);
#ifdef PARSER_STANDALONE
  Py_XDECREF(parser);
#endif
  return result;
}


static PyObject*
Protocol_connection_made(Protocol* self, PyObject* transport)
{
#ifdef PROTOCOL_TRACK_REFCNT
  printf("made: %ld, %ld, %ld, ",
    (size_t)Py_REFCNT(Py_None), (size_t)Py_REFCNT(Py_True), (size_t)Py_REFCNT(Py_False));
  self->none_cnt = Py_REFCNT(Py_None);
  self->true_cnt = Py_REFCNT(Py_True);
  self->false_cnt = Py_REFCNT(Py_False);
#endif

  PyObject* get_extra_info = NULL;
  PyObject* socket = NULL;
  PyObject* setsockopt = NULL;
  PyObject* connections = NULL;
  self->transport = transport;
  Py_INCREF(self->transport);

  if(!(get_extra_info = PyObject_GetAttrString(transport, "get_extra_info")))
    goto error;

  if(!(socket = PyObject_CallFunctionObjArgs(get_extra_info, socket_str, NULL)))
    goto error;

  if(!(setsockopt = PyObject_GetAttrString(socket, "setsockopt")))
    goto error;

  PyObject* tmp;
  if(!(tmp = PyObject_CallFunctionObjArgs(setsockopt, IPPROTO_TCP, TCP_NODELAY, one, NULL)))
    goto error;
  Py_DECREF(tmp);

  if(!(self->write = PyObject_GetAttrString(transport, "write")))
    goto error;

  if(!(connections = PyObject_GetAttrString(self->app, "_connections")))
    goto error;

#ifdef REAPER_ENABLED
  self->idle_time = 0;
  self->read_ops = 0;
  self->last_read_ops = 0;
#endif

  if(PySet_Add(connections, (PyObject*)self) == -1)
    goto error;

  goto finally;

  error:
  return NULL;

  finally:
  Py_XDECREF(connections);
  Py_XDECREF(setsockopt);
  Py_XDECREF(socket);
  Py_XDECREF(get_extra_info);
  Py_RETURN_NONE;
}


static void*
Protocol_close(Protocol* self)
{
  void* result = self;

  PyObject* close = NULL;
  close = PyObject_GetAttrString(self->transport, "close");
  if(!close)
    goto error;
  PyObject* tmp = PyObject_CallFunctionObjArgs(close, NULL);
  if(!tmp)
    goto error;
  Py_DECREF(tmp);

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(close);
  return result;
}


static PyObject*
Protocol_connection_lost(Protocol* self, PyObject* args)
{
  PyObject* connections = NULL;
  PyObject* result = Py_None;
#ifdef PARSER_STANDALONE
  PyObject* result = PyObject_CallFunctionObjArgs(
    self->feed_disconnect, NULL);
  if(!result)
    goto error;
  Py_DECREF(result); // FIXME: result can leak
#else
  if(!Parser_feed_disconnect(&self->parser))
    goto error;
#endif

  if(!(connections = PyObject_GetAttrString(self->app, "_connections")))
    goto error;

  if(PySet_Discard(connections, (PyObject*)self) == -1)
    goto error;

#ifdef PROTOCOL_TRACK_REFCNT
printf("lost: %ld, %ld, %ld\n",
  (size_t)Py_REFCNT(Py_None), (size_t)Py_REFCNT(Py_True), (size_t)Py_REFCNT(Py_False));
  assert(Py_REFCNT(Py_None) == self->none_cnt);
  assert(Py_REFCNT(Py_True) == self->true_cnt);
  assert(Py_REFCNT(Py_False) >= self->false_cnt);
#endif

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(connections);
  Py_XINCREF(result);
  return result;
}


static PyObject*
Protocol_data_received(Protocol* self, PyObject* data)
{
#ifdef REAPER_ENABLED
  self->read_ops++;
#endif

#ifdef PARSER_STANDALONE
  PyObject* result = PyObject_CallFunctionObjArgs(
    self->feed, data, NULL);
  if(!result)
    goto error;
  Py_DECREF(result);
#else
  if(!Parser_feed(&self->parser, data))
    goto error;
#endif

  goto finally;

  error:
  return NULL;
  finally:
  Py_RETURN_NONE;
}

#ifdef PARSER_STANDALONE
static PyObject*
Protocol_on_headers(Protocol* self, PyObject *args)
{
  Py_RETURN_NONE;
}
#else
Protocol*
Protocol_on_headers(Protocol* self, char* method, size_t method_len,
                    char* path, size_t path_len, int minor_version,
                    void* headers, size_t num_headers)
{
  Protocol* result = self;

  Request_dealloc(&self->static_request);
  Request_new(request_capi->RequestType, &self->static_request);
  Request_init(&self->static_request);

  request_capi->Request_from_raw(
    &self->static_request, method, method_len, path, path_len, minor_version,
    headers, num_headers);

  goto finally;

  finally:
  return result;
}
#endif


static inline Protocol*
Protocol_write_response_or_err(Protocol* self, PyObject* request, Response* response)
{
    Protocol* result = self;
    PyObject* response_bytes = NULL;
    PyObject* error_result = NULL;

    if(!response) {
      error_result = PyObject_CallFunctionObjArgs(
        self->error_handler, request, ((Request*)request)->exception, NULL);
      if(!error_result)
        goto error;

      ((Request*)request)->simple = false;
      if(!Protocol_write_response_or_err(self, request, (Response*)error_result))
        goto error;

      goto finally;
    }

    if(!(response_bytes =
         response_capi->Response_render(response, ((Request*)request)->simple)))
      goto error;

    PyObject* tmp;
    if(!(tmp = PyObject_CallFunctionObjArgs(self->write, response_bytes, NULL)))
      goto error;
    Py_DECREF(tmp);

    if(response->keep_alive == KEEP_ALIVE_FALSE) {
      if(!Protocol_close(self))
        goto error;
    }

    goto finally;

    error:
    result = NULL;

    finally:
    Py_XDECREF(error_result);
    Py_XDECREF(response_bytes);
    return result;
}

#define Protocol_catch_exception(request) \
{ \
  PyObject* etype; \
  PyObject* evalue; \
  PyObject* etraceback; \
  \
  PyErr_Fetch(&etype, &evalue, &etraceback); \
  PyErr_NormalizeException(&etype, &evalue, &etraceback); \
  if(etraceback) { \
    PyException_SetTraceback(evalue, etraceback); \
    Py_DECREF(etraceback); \
  } \
  Py_DECREF(etype); \
  \
  ((Request*)request)->exception = evalue; \
}


static void* Protocol_pipeline_ready(PipelineEntry entry, void* closure)
{
  Protocol* self = (Protocol*)closure;
  PyObject* get_result = NULL;
  PyObject* response = NULL;
  PyObject* request = entry.request;
  PyObject* task = entry.task;

  if(PipelineEntry_is_task(entry)) {
    if(!(get_result = PyObject_GetAttrString(task, "result")))
      goto error;

    if(!(response = PyObject_CallFunctionObjArgs(get_result, NULL)))
      Protocol_catch_exception(request);
  } else {
    response = task;
  }

  if(!Protocol_write_response_or_err(self, request, (Response*)response))
    goto error;

  goto finally;

  error:
  self = NULL;

  finally:
  if(PipelineEntry_is_task(entry))
    Py_XDECREF(response);
  Py_XDECREF(get_result);
  return self;
}


static inline Protocol*
Protocol_handle_coro(Protocol* self, PyObject* request, PyObject* coro)
{
  Protocol* result = self;
  PyObject* task = NULL;

  if(!(task = PyObject_CallFunctionObjArgs(self->create_task, coro, NULL)))
    goto error;

  if(!Pipeline_queue(&self->pipeline, (PipelineEntry){true, request, task}))
    goto error;

  goto finally;

  error:
  result = NULL;

  finally:
  Py_XDECREF(task);
  return result;
}


#ifdef PARSER_STANDALONE
static PyObject*
Protocol_on_body(Protocol* self, PyObject *args)
#else
Protocol*
Protocol_on_body(Protocol* self, char* body, size_t body_len)
#endif
{
#ifdef PARSER_STANDALONE
  PyObject* result = Py_None;
#else
  Protocol* result = self;
#endif
  PyObject* request = NULL;
  PyObject* handler_result = NULL;
  MatchDictEntry* entries;
  MatcherEntry* matcher_entry;
  size_t entries_length;
#ifdef PARSER_STANDALONE
/*  PyObject* request;
  if(!PyArg_ParseTuple(args, "O", &request))
    goto error;
*/ // FIXME implement body setting
#endif

  matcher_entry = matcher_capi->Matcher_match_request(
    (Matcher*)self->matcher, (PyObject*)&self->static_request,
    &entries, &entries_length);

  request_capi->Request_set_match_dict_entries(
    &self->static_request, entries, entries_length);

  request_capi->Request_set_body(
    &self->static_request, body, body_len);

  self->static_request.simple = matcher_entry && matcher_entry->simple;

  request = (PyObject*)&self->static_request;
  if((matcher_entry && matcher_entry->coro_func) || !PIPELINE_EMPTY(&self->pipeline)) {
    if(!(request = request_capi->Request_clone(&self->static_request)))
      goto error;
  }

  ((Request*)request)->transport = self->transport;
  Py_INCREF(self->transport);

  ((Request*)request)->matcher_entry = matcher_entry;

  if(!matcher_entry) {
    PyErr_SetString(PyExc_KeyError, "Route not found");
    Protocol_catch_exception(request);
    goto queue_or_write;
  }

  if(!(handler_result = PyObject_CallFunctionObjArgs(
       matcher_entry->handler, request, NULL))) {
    Protocol_catch_exception(request);
    goto queue_or_write;
  }

  if(matcher_entry->coro_func) {
    if(!Protocol_handle_coro(self, request, handler_result))
      goto error;

    goto finally;
  }

  queue_or_write:

  if(!PIPELINE_EMPTY(&self->pipeline))
  {
    if(!Pipeline_queue(&self->pipeline, (PipelineEntry){false, request, handler_result}))
      goto error;

    goto finally;
  }

  if(!Protocol_write_response_or_err(
      self, (PyObject*)&self->static_request, (Response*)handler_result))
    goto error;

  goto finally;

  error:
  result = NULL;

  finally:
  if(request != (PyObject*)&self->static_request)
    Py_XDECREF(request);
  Py_XDECREF(handler_result);
#ifdef PARSER_STANDALONE
  if(result)
    Py_INCREF(result);
#endif
  return result;
}

#ifdef PARSER_STANDALONE
static PyObject*
Protocol_on_error(Protocol* self, PyObject *args)
{
  Py_RETURN_NONE;
}
#else
Protocol*
Protocol_on_error(Protocol* self, PyObject* error)
{
  PyObject* protocol_error_handler = NULL;
  PyObject* response = NULL;

  if(!(protocol_error_handler =
       PyObject_GetAttrString(self->app, "protocol_error_handler")))
    goto error;

  if(!(response =
       PyObject_CallFunctionObjArgs(protocol_error_handler, error, NULL)))
    goto error;

  PyObject* tmp;
  if(!(tmp = PyObject_CallFunctionObjArgs(self->write, response, NULL)))
    goto error;
  Py_DECREF(tmp);

  if(!Protocol_close(self))
    goto error;

  goto finally;

  error:
  self = NULL;

  finally:
  Py_XDECREF(response);
  Py_XDECREF(protocol_error_handler);
  return self;
}
#endif


static PyMethodDef Protocol_methods[] = {
  {"connection_made", (PyCFunction)Protocol_connection_made, METH_O, ""},
  {"connection_lost", (PyCFunction)Protocol_connection_lost, METH_VARARGS, ""},
  {"data_received", (PyCFunction)Protocol_data_received, METH_O, ""},
#ifdef PARSER_STANDALONE
  {"on_headers", (PyCFunction)Protocol_on_headers, METH_VARARGS, ""},
  {"on_body", (PyCFunction)Protocol_on_body, METH_VARARGS, ""},
  {"on_error", (PyCFunction)Protocol_on_error, METH_VARARGS, ""},
#endif
  {NULL}
};


static PyTypeObject ProtocolType = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "cprotocol.Protocol",      /* tp_name */
  sizeof(Protocol),          /* tp_basicsize */
  0,                         /* tp_itemsize */
  (destructor)Protocol_dealloc, /* tp_dealloc */
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
  "Protocol",                /* tp_doc */
  0,                         /* tp_traverse */
  0,                         /* tp_clear */
  0,                         /* tp_richcompare */
  0,                         /* tp_weaklistoffset */
  0,                         /* tp_iter */
  0,                         /* tp_iternext */
  Protocol_methods,          /* tp_methods */
  0,                         /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)Protocol_init,   /* tp_init */
  0,                         /* tp_alloc */
  Protocol_new,              /* tp_new */
};


static PyModuleDef cprotocol = {
  PyModuleDef_HEAD_INIT,
  "cprotocol",
  "cprotocol",
  -1,
  NULL, NULL, NULL, NULL, NULL
};


PyMODINIT_FUNC
PyInit_cprotocol(void)
{
  PyObject* m = NULL;
#ifdef PARSER_STANDALONE
  PyObject* cparser = NULL;
  Parser = NULL;
#endif
  PyObject* api_capsule = NULL;
  PyObject* crequest = NULL;
  PyObject* socket = NULL;
  socket_str = NULL;
  one = NULL;
  IPPROTO_TCP = NULL;
  TCP_NODELAY = NULL;

  if (PyType_Ready(&ProtocolType) < 0)
    goto error;

  m = PyModule_Create(&cprotocol);
  if(!m)
    goto error;

#ifdef PARSER_STANDALONE
  cparser = PyImport_ImportModule("parser.cparser");
  if(!cparser)
    goto error;

  Parser = PyObject_GetAttrString(cparser, "HttpRequestParser");
  if(!Parser)
    goto error;
#else
  if(cparser_init() == -1)
    goto error;
#endif

  if(!cpipeline_init())
    goto error;

  if(!crequest_init())
    goto error;

  crequest = PyImport_ImportModule("request.crequest");
  if(!crequest)
    goto error;

  PyRequest = PyObject_GetAttrString(crequest, "Request");
  if(!PyRequest)
    goto error;

  request_capi = import_capi("request.crequest");
  if(!request_capi)
    goto error;

  matcher_capi = import_capi("router.cmatcher");
  if(!matcher_capi)
    goto error;

  response_capi = import_capi("response.cresponse");
  if(!response_capi)
    goto error;

  if(!(socket_str = PyUnicode_FromString("socket")))
    goto error;

  if(!(one = PyLong_FromLong(1)))
    goto error;

  if(!(socket = PyImport_ImportModule("socket")))
    goto error;

  if(!(IPPROTO_TCP = PyObject_GetAttrString(socket, "IPPROTO_TCP")))
    goto error;

  if(!(TCP_NODELAY = PyObject_GetAttrString(socket, "TCP_NODELAY")))
    goto error;

  Py_INCREF(&ProtocolType);
  PyModule_AddObject(m, "Protocol", (PyObject*)&ProtocolType);

  static Protocol_CAPI capi = {
    Protocol_close
  };
  api_capsule = export_capi(m, "protocol.cprotocol", &capi);
  if(!api_capsule)
    goto error;

  goto finally;

  error:
  Py_XDECREF(PyRequest);
#ifdef PARSER_STANDALONE
  Py_XDECREF(Parser);
#endif
  m = NULL;
  finally:
  Py_XDECREF(api_capsule);
  Py_XDECREF(socket);
  Py_XDECREF(crequest);
#ifdef PARSER_STANDALONE
  Py_XDECREF(cparser);
#endif
  return m;
}
