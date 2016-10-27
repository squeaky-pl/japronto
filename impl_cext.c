#include <Python.h>

typedef struct {
    PyObject_HEAD
    /* Type-specific fields go here. */
} impl_cext_HttpRequestParser;

static PyTypeObject impl_cext_HttpRequestParserType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "impl_cext.HttpRequestParser",       /* tp_name */
    sizeof(impl_cext_HttpRequestParser), /* tp_basicsize */
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

    impl_cext_HttpRequestParserType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&impl_cext_HttpRequestParserType) < 0)
        return NULL;

    m = PyModule_Create(&impl_cext);
    if (m == NULL)
        return NULL;

    Py_INCREF(&impl_cext_HttpRequestParserType);
    PyModule_AddObject(
      m, "HttpRequestParser", (PyObject *)&impl_cext_HttpRequestParserType);
    return m;
}
