Source: https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/advanced_topics/asyncio.html
Fetched: 2026-10-10
Description: Official prompt_toolkit asyncio documentation
Version: 3.0.52; project lockfile: 3.0.53

Running on top of the asyncio event loop — prompt_toolkit 3.0.52 documentation
Back to top
Skip to index filter
Skip to main content
prompt_toolkitprompt_toolkit
Getting started
Tutorials
Build an SQLite REPL
Advanced
More about key bindings
More about styling
Filters
The rendering flow
Running on top of the asyncio event loop
Unit testing
Input hooks
Architecture
The rendering pipeline
Reference
Search the documentation
prompt_toolkit
Getting started
Tutorials
Build an SQLite REPL
Advanced
More about key bindings
More about styling
Filters
The rendering flow
Running on top of the asyncio event loop
Unit testing
Input hooks
Architecture
The rendering pipeline
Reference
python-prompt-toolkit
prompt_toolkit
latest
Versions
Change appearance
Change appearance
Light
Dark
Automatic
Index
Index
Gallery
Getting started
Upgrading
Upgrading to prompt_toolkit 2.0
Upgrading to prompt_toolkit 3.0
Printing (and using) formatted text
Asking for input (prompts)
Asking for a choice
Dialogs
Progress bars
Building full screen applications
Tutorials
Tutorial: Build an SQLite REPL
Advanced topics
More about key bindings
More about styling
Filters
The rendering flow
Running on top of the asyncio event loop
Unit testing
Input hooks
Architecture
The rendering pipeline
Reference
Related projects
Toggle menu contents
Start
Advanced topics
Running on top of the asyncio event loop
Running on top of the asyncio event loop¶
Note
New in prompt_toolkit 3.0. (In prompt_toolkit 2.0 this was possible using a
work-around).
Prompt_toolkit 3.0 uses asyncio natively. Calling Application.run() will
automatically run the asyncio event loop.
If however you want to run a prompt_toolkit Application within an asyncio
environment, you have to call the run_async method, like this:
from prompt_toolkit.application import Application
async def main():
# Define application.
application = Application(
...
)
result = await application.run_async()
print(result)
asyncio.get_event_loop().run_until_complete(main())
Previous
The rendering flow
Next
Unit testing
Documentation
Package
Repository
Issues
prompt_toolkit
2014-2024, Jonathan Slenders
Built with Sphinx 8.2.3 and Nefertiti 0.8.6
