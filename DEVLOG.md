# DEVLOG

## TODO

 - [X] Serve images as files, consider separate json for use with `claude`.
 - [X] Revisit parser, consider using `ast` (and implement dependency tracking)
 - [ ] Add SSE Updates. Server sent events with live updating
 - [ ] Documentation.
 - [X] Package Setup.
 - [ ] Enhanced pandas and plotting support (from marimo?)
 - [ ] Add other mime types (pdf, video)


## 2025-07-16

Created an ast based parser that should be more robust and dependency tracking
which is enabled by default. Initially this was breaking on doc strings for
functions but now should just be top level. For some reason the execution
counts don't seem to start at zero, not sure what the deal is there.

Next enhancement to add would probably be to add some kind of api, which would
let an agent like claude query or get the results of individual cells, that way
they could see what is happening in a more fine grained way.  The api should
probably just serve json of the Cell objects on some path like /cells/ or
something, not sure the right format there, and not sure if we can return
proper python objects or maybe pickle serializations of them, but that seems a
bit dangerous. 

## 2025-07-15

Published on PyPI. `uv publish`. Also tried to fix the double formatting of the LaTeX.

## 2025-07-08

Picking this back up. I think I should start by writing some tests for the
parser.  Got a test harness written.  Got a simple HTML Formatter and rich
display support.

One thing to remember is to add a simple download button or something, to
recover the raw file.

Fixed the watcher module.
Enhanced the HTML formatter.  Create proper HTML templates with CSS styling.
Added Rich Display support. implement hooks for matplotlib, dataframes, etc.
Improved error handling.  Add capture for errors
Updated CLI interface, --serve, --port
Implemented live server, HTTP server with autoreload
Added basic dependency tracking, caching and execution counters.

## 2025-05-16

I figured out that the `code.InteractiveInterpreter` really wasn't doing much,
so I made my own environment with its own globals and locals. Now I think I am
properly generating outputs, though I should catch and handle syntax errors and
other errors and forward them.

Seems like next step is generating a proper html template and some styling, 
then at least I'll already having a thing that can generate nice outputs, after
I add in the rich display hooks, that sort of thing.

Then I need to add support for the hashing and only selective running of code.

And I need the server that can stream the updates.
