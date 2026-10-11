Source: https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/full_screen_apps.html
Fetched: 2026-10-10
Description: Official prompt_toolkit layout documentation
Version: 3.0.52; project lockfile: 3.0.53

Building full screen applications — prompt_toolkit 3.0.52 documentation
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
Building full screen applications
Building full screen applications¶
prompt_toolkit can be used to create complex full screen terminal
applications. Typically, an application consists of a layout (to describe the
graphical part) and a set of key bindings.
The sections below describe the components required for full screen
applications (or custom, non full screen applications), and how to assemble
them together.
Before going through this page, it could be helpful to go through asking
for input (prompts) first. Many things that apply to an
input prompt, like styling, key bindings and so on, also apply to full screen
applications.
Note
Also remember that the examples directory of the prompt_toolkit
repository contains plenty of examples. Each example is supposed to explain
one idea. So, this as well should help you get started.
Don’t hesitate to open a GitHub issue if you feel that a certain example is
missing.
A simple application¶
Every prompt_toolkit application is an instance of an
Application object. The simplest full
screen example would look like this:
from prompt_toolkit import Application
app = Application(full_screen=True)
app.run()
This will display a dummy application that says “No layout specified. Press
ENTER to quit.”.
Note
If we wouldn’t set the full_screen option, the application would
not run in the alternate screen buffer, and only consume the least
amount of space required for the layout.
An application consists of several components. The most important are:
I/O objects: the input and output device.
The layout: this defines the graphical structure of the application. For
instance, a text box on the left side, and a button on the right side.
You can also think of the layout as a collection of ‘widgets’.
A style: this defines what colors and underline/bold/italic styles are used
everywhere.
A set of key bindings.
We will discuss all of these in more detail below.
I/O objects¶
Every Application instance requires an I/O
object for input and output:
An Input instance, which is an abstraction
of the input stream (stdin).
An Output instance, which is an
abstraction of the output stream, and is called by the renderer.
Both are optional and normally not needed to pass explicitly. Usually, the
default works fine.
There is a third I/O object which is also required by the application, but not
passed inside. This is the event loop, an
eventloop instance. This is basically a
while-true loop that waits for user input, and when it receives something (like
a key press), it will send that to the the appropriate handler, like for
instance, a key binding.
When run() is called, the event
loop will run until the application is done. An application will quit when
exit() is called.
The layout¶
A layered layout architecture¶
There are several ways to create a prompt_toolkit layout, depending on how
customizable you want things to be. In fact, there are several layers of
abstraction.
The most low-level way of creating a layout is by combining
Container and
UIControl objects.
Examples of Container objects are
VSplit (vertical split),
HSplit (horizontal split) and
FloatContainer. These containers arrange the
layout and can split it in multiple regions. Each container can recursively
contain multiple other containers. They can be combined in any way to define
the “shape” of the layout.
The Window object is a special kind of
container that can contain a UIControl
object. The UIControl object is responsible
for the generation of the actual content. The
Window object acts as an adaptor between the
UIControl and other containers, but it’s also
responsible for the scrolling and line wrapping of the content.
Examples of UIControl objects are
BufferControl for showing the content of an
editable/scrollable buffer, and
FormattedTextControl for displaying
(formatted) text.
Normally, it is never needed to create new
UIControl or
Container classes, but instead you would
create the layout by composing instances of the existing built-ins.
A higher level abstraction of building a layout is by using “widgets”. A
widget is a reusable layout component that can contain multiple containers
and controls. Widgets have a __pt_container__ function, which returns
the root container for this widget. Prompt_toolkit contains a couple of
widgets like TextArea,
Button,
Frame,
VerticalLine and so on.
The highest level abstractions can be found in the shortcuts module.
There we don’t have to think about the layout, controls and containers at
all. This is the simplest way to use prompt_toolkit, but is only meant for
specific use cases, like a prompt or a simple dialog window.
Containers and controls¶
The biggest difference between containers and controls is that containers
arrange the layout by splitting the screen in many regions, while controls are
responsible for generating the actual content.
Note
Under the hood, the difference is:
containers use absolute coordinates, and paint on a
Screen instance.
user controls create a UIContent
instance. This is a collection of lines that represent the actual
content. A UIControl is not aware
of the screen.
Abstract base class
Examples
Container
HSplit
VSplit
FloatContainer
Window
ScrollablePane
UIControl
BufferControl
FormattedTextControl
The Window class itself is
particular: it is a Container that
can contain a UIControl. Thus, it’s the adaptor
between the two. The Window class also takes
care of scrolling the content and wrapping the lines if needed.
Finally, there is the Layout class which wraps
the whole layout. This is responsible for keeping track of which window has the
focus.
Here is an example of a layout that displays the content of the default buffer
on the left, and displays "Hello world" on the right. In between it shows a
vertical line:
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
buffer1 = Buffer()  # Editable buffer.
root_container = VSplit([
# One window that holds the BufferControl with the default buffer on
# the left.
Window(content=BufferControl(buffer=buffer1)),
# A vertical line in the middle. We explicitly specify the width, to
# make sure that the layout engine will not try to divide the whole
# width by three for all these windows. The window will simply fill its
# content by repeating this character.
Window(width=1, char='|'),
# Display the text 'Hello world' on the right.
Window(content=FormattedTextControl(text='Hello world')),
])
layout = Layout(root_container)
app = Application(layout=layout, full_screen=True)
app.run() # You won't be able to Exit this app
Notice that if you execute this right now, there is no way to quit this
application yet. This is something we explain in the next section below.
More complex layouts can be achieved by nesting multiple
VSplit,
HSplit and
FloatContainer objects.
If you want to make some part of the layout only visible when a certain
condition is satisfied, use a
ConditionalContainer.
Finally, there is ScrollablePane, a container
class that can be used to create long forms or nested layouts that are
scrollable as a whole.
Focusing windows¶
Focusing something can be done by calling the
focus() method. This method is very
flexible and accepts a Window, a
Buffer, a
UIControl and more.
In the following example, we use get_app()
for getting the active application.
from prompt_toolkit.application import get_app
# This window was created earlier.
w = Window()
# ...
# Now focus it.
get_app().layout.focus(w)
Changing the focus is something which is typically done in a key binding, so
read on to see how to define key bindings.
Key bindings¶
In order to react to user actions, we need to create a
KeyBindings object and pass
that to our Application.
There are two kinds of key bindings:
Global key bindings, which are always active.
Key bindings that belong to a certain
UIControl and are only active when
this control is focused. Both
BufferControl
FormattedTextControl take a key_bindings
argument.
Global key bindings¶
Key bindings can be passed to the application as follows:
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
kb = KeyBindings()
app = Application(key_bindings=kb)
app.run()
To register a new keyboard shortcut, we can use the
add() method as a decorator of
the key handler:
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
kb = KeyBindings()
@kb.add('c-q')
def exit_(event):
"""
Pressing Ctrl-Q will exit the user interface.
Setting a return value means: quit the event loop that drives the user
interface and return this value from the `Application.run()` call.
"""
event.app.exit()
app = Application(key_bindings=kb, full_screen=True)
app.run()
The callback function is named exit_ for clarity, but it could have been
named _ (underscore) as well, because we won’t refer to this name.
Read more about key bindings …
Modal containers¶
The following container objects take a modal argument
VSplit,
HSplit, and
FloatContainer.
Setting modal=True makes what is called a modal container. Normally, a
child container would inherit its parent key bindings. This does not apply to
modal containers.
Consider a modal container (e.g. VSplit)
is child of another container, its parent. Any key bindings from the parent
are not taken into account if the modal container (child) has the focus.
This is useful in a complex layout, where many controls have their own key
bindings, but you only want to enable the key bindings for a certain region of
the layout.
The global key bindings are always active.
More about the Window class¶
As said earlier, a Window is a
Container that wraps a
UIControl, like a
BufferControl or
FormattedTextControl.
Note
Basically, windows are the leaves in the tree structure that represent the UI.
A Window provides a “view” on the
UIControl, which provides lines of content. The
window is in the first place responsible for the line wrapping and scrolling of
the content, but there are much more options.
Adding left or right margins. These are used for displaying scroll bars or
line numbers.
There are the cursorline and cursorcolumn options. These allow
highlighting the line or column of the cursor position.
Alignment of the content. The content can be left aligned, right aligned or
centered.
Finally, the background can be filled with a default character.
More about buffers and BufferControl¶
Input processors¶
A Processor is used to postprocess
the content of a BufferControl before it’s
displayed. It can for instance highlight matching brackets or change the
visualization of tabs and so on.
A Processor operates on individual
lines. Basically, it takes a (formatted) line and produces a new (formatted)
line.
Some built-in processors:
Processor
Usage:
HighlightSearchProcessor
Highlight the current search results.
HighlightSelectionProcessor
Highlight the selection.
PasswordProcessor
Display input as asterisks. (* characters).
BracketsMismatchProcessor
Highlight open/close mismatches for brackets.
BeforeInput
Insert some text before.
AfterInput
Insert some text after.
AppendAutoSuggestion
Append auto suggestion text.
ShowLeadingWhiteSpaceProcessor
Visualize leading whitespace.
ShowTrailingWhiteSpaceProcessor
Visualize trailing whitespace.
TabsProcessor
Visualize tabs as n spaces, or some symbols.
A BufferControl takes only one processor as
input, but it is possible to “merge” multiple processors into one with the
merge_processors() function.
On this page
On this page
Building full screen applications
A simple application
I/O objects
The layout
A layered layout architecture
Containers and controls
Focusing windows
Key bindings
Global key bindings
Modal containers
More about the Window class
More about buffers and BufferControl
Input processors
Previous
Progress bars
Next
Tutorials
Documentation
Package
Repository
Issues
prompt_toolkit
2014-2024, Jonathan Slenders
Built with Sphinx 8.2.3 and Nefertiti 0.8.6
