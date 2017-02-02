package main

import "net/http"

var (
	helloResp    = []byte("Hello world!")
	notFoundResp = []byte("Not Found")
)

func hello(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		w.WriteHeader(http.StatusNotFound)
		w.Write(notFoundResp)
		return
	}
	w.Write(helloResp)
}

func main() {
	http.HandleFunc("/", hello)
	http.ListenAndServe("0.0.0.0:8080", nil)
}
