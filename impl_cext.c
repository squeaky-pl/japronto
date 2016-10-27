#include <Python.h>

typedef struct {
    PyObject_HEAD
    /* Type-specific fields go here. */
} HttpRequestParser;


static PyObject *
HttpRequestParser_feed(HttpRequestParser* self) {
  printf("feed\n");
  Py_RETURN_NONE;
}


static PyObject *
HttpRequestParser_feed_disconnect(HttpRequestParser* self) {
  printf("feed_disconnect\n");
  Py_RETURN_NONE;
}


static PyMethodDef HttpRequestParser_methods[] = {
    {"feed", (PyCFunction)HttpRequestParser_feed, METH_NOARGS,
     "feed"
    },
    {
      "feed_disconnect", (PyCFunction)HttpRequestParser_feed_disconnect,
      METH_NOARGS,
      "feed_disconnect"
    },
    {NULL}  /* Sentinel */
};


static PyTypeObject HttpRequestParserType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "impl_cext.HttpRequestParser",       /* tp_name */
    sizeof(HttpRequestParser), /* tp_basicsize */
    0,                         /* tp_itemsize */
    0,                         /* tp_dealloc */
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
