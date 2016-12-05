#pragma once

#include <Python.h>


typedef struct {
  PyObject_HEAD
#ifdef PIPELINE_OPAQUE
  PyObject* ready;
#else
  void* (*ready)(PyObject*, void*);
  void* ready_closure;
#endif
  PyObject* task_done;
  PyObject* queue[10];
  size_t queue_start;
  size_t queue_end;
} Pipeline;


#define PIPELINE_EMPTY(p) ((p)->queue_start == (p)->queue_end)

#ifndef PIPELINE_OPAQUE
PyObject*
Pipeline_new(Pipeline* self);

void
Pipeline_dealloc(Pipeline* self);

int
Pipeline_init(Pipeline* self, void* (*ready)(PyObject*, void*), void* closure);

PyObject*
Pipeline_queue(Pipeline* self, PyObject* task);

void*
cpipeline_init(void);
#endif
