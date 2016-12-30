#pragma once

static const char* reasons_1xx[] = {
  "Continue", //100
  "Switching Protocols", //101
};

static const char* reasons_2xx[] = {
  "OK", //200
  "Created", //201
  "Accepted", //202
  "Non-Authoritative Information", //203
  "No Content", // 204
  "Reset Content", //205
  "Partial Content", //206
};

static const char* reasons_3xx[] = {
  "Multiple Choices", //300
  "Moved Permanently", //301
  "Found", //302
  "See Other", //303,
  "Not Modified", //304
  "Use Proxy",  //305
  "Proxy Switch", //306
  "Temporary Redirect", //307
};

static const char* reasons_4xx[] = {
  "Bad Request", //400
  "Unauthorized", //401
  "Payment Required", //402
  "Forbidden", //403
  "Not Found", //404
  "Method Not Allowed", //405
  "Not acceptable", //406
  "Proxy Authentication Required", //407
  "Request Timeout", //408
  "Conflict", //409
  "Gone", //410
  "Length Required", //411
  "Precondition Failed", //412
  "Request Entity Too Large", //413
  "Request-URI Too Long", //414
  "Unsupported Media Type", //415
  "Requested Range Not Satisfiable", //416
  "Expectation Failed", //417
};

static const char* reasons_5xx[] = {
  "Internal Server Error", //500
  "Not Implemented", //501
  "Bad Gateway", //502
  "Service Unavailable", //503
  "Gateway Timeout", //504
  "HTTP Version Not Supported", //505
};

typedef struct {
  const char** reasons;
  size_t maximum;
} ReasonRange;

static const ReasonRange reason_ranges[] = {
  {reasons_1xx, 1},
  {reasons_2xx, 6},
  {reasons_3xx, 7},
  {reasons_4xx, 17},
  {reasons_5xx, 5}
};
