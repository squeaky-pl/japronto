#pragma once

#include <stdbool.h>
#include <Python.h>

#include "picohttpparser.h"


enum Parser_state {
  PARSER_HEADERS,
  PARSER_BODY
};


enum Parser_transfer {
  PARSER_TRANSFER_UNSET,
  PARSER_IDENTITY,
  PARSER_CHUNKED
};


enum Parser_connection {
  PARSER_CONNECTION_UNSET,
  PARSER_CLOSE,
  PARSER_KEEP_ALIVE
};

#define PARSER_INITIAL_BUFFER_SIZE 4096

typedef struct {
#ifdef PARSER_STANDALONE
    PyObject_HEAD
#endif

    enum Parser_state state;
    enum Parser_transfer transfer;
    enum Parser_connection connection;

    unsigned long content_length;
    struct phr_chunked_decoder chunked_decoder;
    size_t chunked_offset;

    char* buffer;
    size_t buffer_start;
    size_t buffer_end;
    size_t buffer_capacity;
    char inline_buffer[PARSER_INITIAL_BUFFER_SIZE];

#ifdef PARSER_STANDALONE
    PyObject* on_headers;
    PyObject* on_body;
    PyObject* on_error;
#else
    void* protocol;
#endif
} Parser;

#ifndef PARSER_STANDALONE
void
Parser_new(Parser* self);

int
Parser_init(Parser* self, void* protocol);

void
Parser_dealloc(Parser* self);

Parser*
Parser_feed(Parser* self, PyObject* py_data);

Parser*
Parser_feed_disconnect(Parser* self);

int
cparser_init(void);
#endif
