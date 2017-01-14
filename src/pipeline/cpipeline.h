#pragma once

#include <stdbool.h>

#include <Python.h>

#ifdef PIPELINE_PAIR

typedef struct {
  bool is_task;
  PyObject* request;
  PyObject* task;
} PipelineEntry;

static inline bool
PipelineEntry_is_task(PipelineEntry entry)
{
  return entry.is_task;
}

static inline void
PipelineEntry_DECREF(PipelineEntry entry)
{
    Py_DECREF(entry.request);
    // if not real task this was response,
    // that was inside request that was already freed above
    if(entry.is_task)
      Py_XDECREF(entry.task);
}

static inline void
PipelineEntry_INCREF(PipelineEntry entry)
{
    Py_INCREF(entry.request);
    Py_XINCREF(entry.task);
}

static inline PyObject*
PipelineEntry_get_task(PipelineEntry entry)
{
  return entry.task;
}
#else
typedef PyObject* PipelineEntry;

static inline bool
PipelineEntry_is_task(PipelineEntry entry)
{
  return true;
}

static inline void
PipelineEntry_DECREF(PipelineEntry entry)
{
    Py_DECREF(entry);
}

static inline void
PipelineEntry_INCREF(PipelineEntry entry)
{
    Py_INCREF(entry);
}

static inline PyObject*
PipelineEntry_get_task(PipelineEntry entry)
{
  return entry;
}
#endif


typedef struct {
  PyObject_HEAD
#ifdef PIPELINE_OPAQUE
  PyObject* ready;
#else
  void* (*ready)(PipelineEntry, PyObject*);
  PyObject* protocol;
#endif
  PyObject* task_done;
  PipelineEntry queue[10];
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
Pipeline_init(Pipeline* self, void* (*ready)(PipelineEntry, PyObject*), PyObject* protocol);

PyObject*
Pipeline_queue(Pipeline* self, PipelineEntry entry);

void*
Pipeline_cancel(Pipeline* self);

void*
cpipeline_init(void);
#endif
