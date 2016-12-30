#pragma once


void* get_ptr_from_mod(const char* module_name, const char* attr_name,
                       const char* capsule_name);

PyObject* put_ptr_in_mod(PyObject* m, void* ptr, const char* attr_name,
                         const char* capsule_name);

#define import_capi(module_name) \
  get_ptr_from_mod(module_name, "_capi", module_name "._capi")

#define export_capi(m, module_name, capi) \
  put_ptr_in_mod(m, capi, "_capi", module_name "._capi")
