package main

import (
	"net/http"

	"github.com/labstack/echo"
)

func hello(c echo.Context) error {
	if c.Path() != "/" {
		return c.String(http.StatusNotFound, "Not Found")
	}
	return c.String(http.StatusOK, "Hello world!")
}

func main() {
	e := echo.New()
	e.GET("/", hello)
	http.ListenAndServe("0.0.0.0:8080", e)
}
