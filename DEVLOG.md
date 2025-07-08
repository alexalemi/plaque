# DEVLOG

## TODO


* Core
 - [X] Fix the watcher module.
 - [X] Enhance HTML formatter.  Create proper HTML templates with CSS styling.
 - [X] Add Rich Display support. implement hooks for matplotlib, dataframes, etc.
 - [ ] Improve error handling.  Add capture for errors
* CLI and Server
 - [ ] Update CLI interface, --serve, --port
 - [ ] Implement live server, HTTP server with autoreload
 - [ ] Add SSE Updates. Server sent events with live updating
* Advanced Features
 - [ ] Add dependency tracking, smart re-execution.
 - [ ] Enhance markdown Rendering, LaTeX, code, etc.
 - [ ] Add More Tests.
* Polish
 - [ ] Documentation.
 - [ ] Package Setup.
 

## 2025-07-08

Picking this back up. I think I should start by writing some tests for the
parser.  Got a test harness written.  Got a simple HTML Formatter and rich
display support.

One thing to remember is to add a simple download button or something, to
recover the raw file.

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
