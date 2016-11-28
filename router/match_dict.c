#include <Python.h>

#include "match_dict.h"


PyObject*
MatchDict_entries_to_dict(MatchDictEntry* entries, size_t length)
{
  PyObject* match_dict = NULL;
  if(!(match_dict = PyDict_New()))
    goto error;

  for(MatchDictEntry* entry = entries; entry < entries + length; entry++) {
    PyObject* key = NULL;
    PyObject* value = NULL;

    if(!(key = PyUnicode_FromStringAndSize(entry->key, entry->key_length)))
      goto loop_error;

    if(!(value = PyUnicode_FromStringAndSize(entry->value, entry->value_length)))
      goto loop_error;

    if(PyDict_SetItem(match_dict, key, value) == -1)
      goto loop_error;

    goto loop_finally;

    loop_error:
    Py_XDECREF(match_dict);
    match_dict = NULL;

    loop_finally:
    Py_XDECREF(key);
    Py_XDECREF(value);
    if(!match_dict)
      goto error;
  }

  goto finally;

  error:
  Py_XDECREF(match_dict);
  match_dict = NULL;

  finally:
  return match_dict;
}
