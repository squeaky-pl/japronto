#include <stdbool.h>
#include <Python.h>

#include "picohttpparser.h"

enum Parser_state {
  PARSER_HEADERS,
  PARSER_BODY
};


enum Parser_transfer {
  PARSER_UNSET,
  PARSER_IDENTITY,
  PARSER_CHUNKED
};


typedef struct {
#ifdef PARSER_STANDALONE
    PyObject_HEAD
#endif

    enum Parser_state state;
    enum Parser_transfer transfer;

    unsigned long content_length;
    struct phr_chunked_decoder chunked_decoder;
    size_t chunked_offset;
    bool no_semantics;

    char* buffer;
    size_t buffer_start;
    size_t buffer_end;
    size_t buffer_capacity;

    PyObject* request;
#ifdef PARSER_STANDALONE
    PyObject* on_headers;
    PyObject* on_body;
    PyObject* on_error;
#else
    void* protocol;
    void* (*on_headers)(void*, PyObject*);
    void* (*on_body)(void*, PyObject*);
    void* (*on_error)(void*, PyObject*);
#endif
} Parser;

#ifndef PARSER_STANDALONE
void
Parser_new(Parser* self);

int
Parser_init(Parser* self, void* protocol,
            void* (*on_headers)(void*, PyObject*),
            void* (*on_body)(void*, PyObject*),
            void* (*on_error)(void*, PyObject*));

void
Parser_dealloc(Parser* self);

Parser*
Parser_feed(Parser* self, PyObject* py_data);

Parser*
Parser_feed_disconnect(Parser* self);

int
cparser_init(void);
#endif
