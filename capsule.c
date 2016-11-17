#include <Python.h>


void* get_ptr_from_mod(const char* module_name, const char* attr_name,
                       const char* capsule_name)
{
  void* ptr;
  PyObject* module = NULL;
  PyObject* capsule = NULL;

  module = PyImport_ImportModule(module_name);
  if(!module)
    goto error;

  capsule = PyObject_GetAttrString(module, attr_name);
  if(!capsule)
    goto error;

  ptr = PyCapsule_GetPointer(capsule, capsule_name);
  if(!ptr)
    goto error;

  goto finally;

  error:
  ptr = NULL;

  finally:
  Py_XDECREF(capsule);
  Py_XDECREF(module);
  return ptr;
}


PyObject* put_ptr_in_mod(PyObject* m, void* ptr, const char* attr_name,
                         const char* capsule_name)
{
  PyObject* capsule = NULL;

  capsule = PyCapsule_New(ptr, capsule_name, NULL);
  if(!capsule)
    goto error;

  if(PyModule_AddObject(m, attr_name, capsule) == -1)
    goto error;

  Py_INCREF(capsule);
  goto finally;

  error:
  Py_XDECREF(capsule);
  capsule = NULL;

  finally:
  return capsule;
}
