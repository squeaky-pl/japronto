#pragma once

typedef enum {
  KEEP_ALIVE_UNSET,
  KEEP_ALIVE_TRUE,
  KEEP_ALIVE_FALSE
} KEEP_ALIVE;

#ifdef _MSC_VER
#define strncasecmp _strnicmp
#define strcasecmp _stricmp
#define MAX(a, b)  (((a) > (b)) ? (a) : (b))
void *memmem(const void *haystack, size_t haystack_len, const void * const needle, const size_t needle_len);

#endif
