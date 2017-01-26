package main

import (
  "io"
  "net/http"
)

func hello(response http.ResponseWriter, request *http.Request) {
    header := response.Header()
    header["Date"] = nil

    var text string
    var status int
    if request.URL.Path == "/" {
	status = 200
	text = "Hello world!"
    } else {
	status = 404
	text = "Not Found"
    }
    response.WriteHeader(status)
    io.WriteString(response, text)
}

func main() {
    http.HandleFunc("/", hello)
    http.ListenAndServe("0.0.0.0:8080", nil)
}
