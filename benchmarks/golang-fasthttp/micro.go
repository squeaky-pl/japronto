package main

import "github.com/valyala/fasthttp"

func hello(ctx *fasthttp.RequestCtx) {
	if string(ctx.Path()) != "/" {
		ctx.SetStatusCode(404)
		ctx.WriteString("Not Found")
		return
	}
	ctx.WriteString("Hello world!")
}

func main() {
	fasthttp.ListenAndServe("0.0.0.0:8080", hello)
}
