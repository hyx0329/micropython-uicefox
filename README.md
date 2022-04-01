# uicefox

This is an async client for http connections on MicroPython. It is basically a
mixture of `urequests` and `uaiohttpclient`.

## What it can do

- http requests
- https requests
- payload, headers, etc. (not tested)
- handle chunked http packages (not tested)
- correctly handle `Content-Length`
- expose a `Stream` object to make process-on-receive possible

## How to use

The code tells everything. Docs are not planned for the moment.

## Notes

Better to "close" the response object (call `await resp.close()`), I don't know what will happen if not.

## TODO

- [ ] chunked request

## About the name

I use Firefox's UA, so I call it `icefox`, but add `u` as prefix following the conventions. It looks like `nicefox`, isn't it?
