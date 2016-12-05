#pragma once

#ifndef GENERATOR_OPAQUE
struct _Generator;

#define GENERATOR struct _Generator

PyObject*
Generator_new(void);

void
Generator_dealloc(struct _Generator* self);

int
Generator_init(struct _Generator* self, PyObject* object);

void*
generator_init(void);
#endif
