package main

import "github.com/valyala/fasthttp"

func hello(ctx *fasthttp.RequestCtx) {
	if len(ctx.Path()) != 1 {
		ctx.Error("Not Found", fasthttp.StatusNotFound)
		return
	}
	ctx.WriteString("Hello world!")
}

func main() {
	fasthttp.ListenAndServe("0.0.0.0:8080", hello)
}
