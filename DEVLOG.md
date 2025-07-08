# DEVLOG

## TODO

 - [ ] Write tests for parser
 - [ ] Write watcher
 - [ ] Write renderer
 - [ ] Figure out SSE style updates

## 2025-07-08

Picking this back up. I think I should start by writing some tests for the 
parser.

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
