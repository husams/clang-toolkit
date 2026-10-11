Source: https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/asking_for_input.html
Fetched: 2026-10-10
Description: Official prompt_toolkit prompts documentation
Version: 3.0.52; project lockfile: 3.0.53

Asking for input (prompts) — prompt_toolkit 3.0.52 documentation
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
Asking for input (prompts)
Asking for input (prompts)¶
This page is about building prompts. Pieces of code that we can embed in a
program for asking the user for input. Even if you want to use prompt_toolkit
for building full screen terminal applications, it is probably still a good
idea to read this first, before heading to the building full screen
applications page.
In this page, we will cover autocompletion, syntax highlighting, key bindings,
and so on.
Hello world¶
The following snippet is the most simple example, it uses the
prompt() function to ask the user for input
and returns the text. Just like (raw_)input.
from prompt_toolkit import prompt
text = prompt("Give me some input: ")
print(f"You said: {text}")
What we get here is a simple prompt that supports the Emacs key bindings like
readline, but further nothing special. However,
prompt() has a lot of configuration options.
In the following sections, we will discover all these parameters.
The PromptSession object¶
Instead of calling the prompt() function, it’s
also possible to create a PromptSession
instance followed by calling its
prompt() method for every input
call. This creates a kind of an input session.
from prompt_toolkit import PromptSession
# Create prompt object.
session = PromptSession()
# Do multiple input calls.
text1 = session.prompt()
text2 = session.prompt()
This has mainly two advantages:
The input history will be kept between consecutive
prompt() calls.
The PromptSession() instance and its
prompt() method take about the
same arguments, like all the options described below (highlighting,
completion, etc…). So if you want to ask for multiple inputs, but each
input call needs about the same arguments, they can be passed to the
PromptSession() instance as well, and they
can be overridden by passing values to the
prompt() method.
Syntax highlighting¶
Adding syntax highlighting is as simple as adding a lexer. All of the Pygments lexers can be used after wrapping them in a
PygmentsLexer. It is also possible to create a
custom lexer by implementing the Lexer abstract
base class.
from pygments.lexers.html import HtmlLexer
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.lexers import PygmentsLexer
text = prompt("Enter HTML: ", lexer=PygmentsLexer(HtmlLexer))
print(f"You said: {text}")
The default Pygments colorscheme is included as part of the default style in
prompt_toolkit. If you want to use another Pygments style along with the lexer,
you can do the following:
from pygments.lexers.html import HtmlLexer
from pygments.styles import get_style_by_name
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles.pygments import style_from_pygments_cls
style = style_from_pygments_cls(get_style_by_name("monokai"))
text = prompt(
"Enter HTML: ",
lexer=PygmentsLexer(HtmlLexer),
style=style,
include_default_pygments_style=False
)
print(f"You said: {text}")
We pass include_default_pygments_style=False, because otherwise, both
styles will be merged, possibly giving slightly different colors in the outcome
for cases where where our custom Pygments style doesn’t specify a color.
Colors¶
The colors for syntax highlighting are defined by a
Style instance. By default, a neutral
built-in style is used, but any style instance can be passed to the
prompt() function. A simple way to create a
style, is by using the from_dict()
function:
from pygments.lexers.html import HtmlLexer
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import PygmentsLexer
our_style = Style.from_dict({
"pygments.comment": "#888888 bold",
"pygments.keyword": "#ff88ff bold",
})
text = prompt(
"Enter HTML: ",
lexer=PygmentsLexer(HtmlLexer),
style=our_style
)
The style dictionary is very similar to the Pygments styles dictionary,
with a few differences:
The roman, sans, mono and border options are ignored.
The style has a few additions: blink, noblink, reverse and noreverse.
Colors can be in the #ff0000 format, but they can be one of the built-in
ANSI color names as well. In that case, they map directly to the 16 color
palette of the terminal.
Read more about styling.
Using a Pygments style¶
All Pygments style classes can be used as well, when they are wrapped through
style_from_pygments_cls().
Suppose we’d like to use a Pygments style, for instance
pygments.styles.tango.TangoStyle, that is possible like this:
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import style_from_pygments_cls
from prompt_toolkit.lexers import PygmentsLexer
from pygments.styles.tango import TangoStyle
from pygments.lexers.html import HtmlLexer
tango_style = style_from_pygments_cls(TangoStyle)
text = prompt(
"Enter HTML: ",
lexer=PygmentsLexer(HtmlLexer),
style=tango_style
)
Creating a custom style could be done like this:
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style, style_from_pygments_cls, merge_styles
from prompt_toolkit.lexers import PygmentsLexer
from pygments.styles.tango import TangoStyle
from pygments.lexers.html import HtmlLexer
our_style = merge_styles([
style_from_pygments_cls(TangoStyle),
Style.from_dict({
"pygments.comment": "#888888 bold",
"pygments.keyword": "#ff88ff bold",
})
])
text = prompt(
"Enter HTML: ",
lexer=PygmentsLexer(HtmlLexer),
style=our_style
)
Coloring the prompt itself¶
It is possible to add some colors to the prompt itself. For this, we need to
build some formatted text. One way of doing this is by
creating a list of style/text tuples. In the following example, we use class
names to refer to the style.
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
style = Style.from_dict({
# User input (default text).
"":          "#ff0066",
# Prompt.
"username": "#884444",
"at":       "#00aa00",
"colon":    "#0000aa",
"pound":    "#00aa00",
"host":     "#00ffff bg:#444400",
"path":     "ansicyan underline",
})
message = [
("class:username", "john"),
("class:at",       "@"),
("class:host",     "localhost"),
("class:colon",    ":"),
("class:path",     "/user/john"),
("class:pound",    "# "),
]
text = prompt(message, style=style)
The message can be any kind of formatted text, as discussed here. It can also be a callable that returns some formatted text.
By default, colors are taken from the 256 color palette. If you want to have
24bit true color, this is possible by adding the
color_depth=ColorDepth.TRUE_COLOR option to the
prompt() function.
from prompt_toolkit.output import ColorDepth
text = prompt(message, style=style, color_depth=ColorDepth.TRUE_COLOR)
Autocompletion¶
Autocompletion can be added by passing a completer parameter. This should
be an instance of the Completer abstract
base class. WordCompleter is an example of
a completer that implements that interface.
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
html_completer = WordCompleter(["<html>", "<body>", "<head>", "<title>"])
text = prompt("Enter HTML: ", completer=html_completer)
print(f"You said: {text}")
WordCompleter is a simple completer that
completes the last word before the cursor with any of the given words.
Note
Note that in prompt_toolkit 2.0, the auto completion became synchronous. This
means that if it takes a long time to compute the completions, that this
will block the event loop and the input processing.
For heavy completion algorithms, it is recommended to wrap the completer in
a ThreadedCompleter in order to run it
in a background thread.
Nested completion¶
Sometimes you have a command line interface where the completion depends on the
previous words from the input. Examples are the CLIs from routers and switches.
A simple WordCompleter is not enough in
that case. We want to to be able to define completions at multiple hierarchical
levels. NestedCompleter solves this issue:
from prompt_toolkit import prompt
from prompt_toolkit.completion import NestedCompleter
completer = NestedCompleter.from_nested_dict({
"show": {
"version": None,
"clock": None,
"ip": {
"interface": {"brief"}
}
},
"exit": None,
})
text = prompt("# ", completer=completer)
print(f"You said: {text}")
Whenever there is a None value in the dictionary, it means that there is no
further nested completion at that point. When all values of a dictionary would
be None, it can also be replaced with a set.
A custom completer¶
For more complex examples, it makes sense to create a custom completer. For
instance:
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
class MyCustomCompleter(Completer):
def get_completions(self, document, complete_event):
yield Completion("completion", start_position=0)
text = prompt("> ", completer=MyCustomCompleter())
A Completer class has to implement a
generator named get_completions()
that takes a Document and yields the current
Completion instances. Each completion
contains a portion of text, and a position.
The position is used for fixing text before the cursor. Pressing the tab key
could for instance turn parts of the input from lowercase to uppercase. This
makes sense for a case insensitive completer. Or in case of a fuzzy completion,
it could fix typos. When start_position is something negative, this amount
of characters will be deleted and replaced.
Styling individual completions¶
Each completion can provide a custom style, which is used when it is rendered
in the completion menu or toolbar. This is possible by passing a style to each
Completion instance.
from prompt_toolkit.completion import Completer, Completion
class MyCustomCompleter(Completer):
def get_completions(self, document, complete_event):
# Display this completion, black on yellow.
yield Completion(
"completion1",
start_position=0,
style="bg:ansiyellow fg:ansiblack"
)
# Underline completion.
yield Completion(
"completion2",
start_position=0,
style="underline"
)
# Specify class name, which will be looked up in the style sheet.
yield Completion(
"completion3",
start_position=0,
style="class:special-completion"
)
The “colorful-prompts.py” example uses completion styling:
Finally, it is possible to pass formatted text for the
display attribute of a Completion. This
provides all the freedom you need to display the text in any possible way. It
can also be combined with the style attribute. For instance:
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
class MyCustomCompleter(Completer):
def get_completions(self, document, complete_event):
yield Completion(
"completion1",
start_position=0,
display=HTML("<b>completion</b><ansired>1</ansired>"),
style="bg:ansiyellow"
)
Fuzzy completion¶
If one possible completions is “django_migrations”, a fuzzy completer would
allow you to get this by typing “djm” only, a subset of characters for this
string.
Prompt_toolkit ships with a FuzzyCompleter
and FuzzyWordCompleter class. These provide
the means for doing this kind of “fuzzy completion”. The first one can take any
completer instance and wrap it so that it becomes a fuzzy completer. The second
one behaves like a WordCompleter wrapped
into a FuzzyCompleter.
Complete while typing¶
Autcompletions can be generated automatically while typing or when the user
presses the tab key. This can be configured with the complete_while_typing
option:
text = prompt(
"Enter HTML: ",
completer=my_completer,
complete_while_typing=True
)
Notice that this setting is incompatible with the enable_history_search
option. The reason for this is that the up and down key bindings would conflict
otherwise. So, make sure to disable history search for this.
Asynchronous completion¶
When generating the completions takes a lot of time, it’s better to do this in
a background thread. This is possible by wrapping the completer in a
ThreadedCompleter, but also by passing the
complete_in_thread=True argument.
text = prompt("> ", completer=MyCustomCompleter(), complete_in_thread=True)
Input validation¶
A prompt can have a validator attached. This is some code that will check
whether the given input is acceptable and it will only return it if that’s the
case. Otherwise it will show an error message and move the cursor to a given
position.
A validator should implements the Validator
abstract base class. This requires only one method, named validate that
takes a Document as input and raises
ValidationError when the validation fails.
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit import prompt
class NumberValidator(Validator):
def validate(self, document):
text = document.text
if text and not text.isdigit():
i = 0
# Get index of first non numeric character.
# We want to move the cursor here.
for i, c in enumerate(text):
if not c.isdigit():
break
raise ValidationError(
message="This input contains non-numeric characters",
cursor_position=i
)
number = int(prompt("Give a number: ", validator=NumberValidator()))
print(f"You said: {number}")
By default, the input is validated in real-time while the user is typing, but
prompt_toolkit can also validate after the user presses the enter key:
prompt(
"Give a number: ",
validator=NumberValidator(),
validate_while_typing=False
)
If the input validation contains some heavy CPU intensive code, but you don’t
want to block the event loop, then it’s recommended to wrap the validator class
in a ThreadedValidator.
Validator from a callable¶
Instead of implementing the Validator
abstract base class, it is also possible to start from a simple function and
use the from_callable() classmethod.
This is easier and sufficient for probably 90% of the validators. It looks as
follows:
from prompt_toolkit.validation import Validator
from prompt_toolkit import prompt
def is_number(text):
return text.isdigit()
validator = Validator.from_callable(
is_number,
error_message="This input contains non-numeric characters",
move_cursor_to_end=True
)
number = int(prompt("Give a number: ", validator=validator))
print(f"You said: {number}")
We define a function that takes a string, and tells whether it’s valid input or
not by returning a boolean.
from_callable() turns that into a
Validator instance. Notice that setting the
cursor position is not possible this way.
History¶
A History object keeps track of all the
previously entered strings, so that the up-arrow can reveal previously entered
items.
The recommended way is to use a
PromptSession, which uses an
InMemoryHistory for the entire session by
default. The following example has a history out of the box:
from prompt_toolkit import PromptSession
session = PromptSession()
while True:
session.prompt()
To persist a history to disk, use a FileHistory
instead of the default
InMemoryHistory. This history object can be
passed either to a PromptSession or to the
prompt() function. For instance:
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
session = PromptSession(history=FileHistory("~/.myhistory"))
while True:
session.prompt()
Auto suggestion¶
Auto suggestion is a way to propose some input completions to the user like the
fish shell.
Usually, the input is compared to the history and when there is another entry
starting with the given text, the completion will be shown as gray text behind
the current input. Pressing the right arrow → or c-e will insert
this suggestion, alt-f will insert the first word of the suggestion.
Note
When suggestions are based on the history, don’t forget to share one
History object between consecutive
prompt() calls. Using a
PromptSession does this for you.
Example:
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
session = PromptSession()
while True:
text = session.prompt("> ", auto_suggest=AutoSuggestFromHistory())
print(f"You said: {text}")
A suggestion does not have to come from the history. Any implementation of the
AutoSuggest abstract base class can be
passed as an argument.
Adding a bottom toolbar¶
Adding a bottom toolbar is as easy as passing a bottom_toolbar argument to
prompt(). This argument be either plain text,
formatted text or a callable that returns plain or
formatted text.
When a function is given, it will be called every time the prompt is rendered,
so the bottom toolbar can be used to display dynamic information.
The toolbar is always erased when the prompt returns.
Here we have an example of a callable that returns an
HTML object. By default, the toolbar
has the reversed style, which is why we are setting the background instead
of the foreground.
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
def bottom_toolbar():
return HTML('This is a <b><style bg="ansired">Toolbar</style></b>!')
text = prompt("> ", bottom_toolbar=bottom_toolbar)
print(f"You said: {text}")
Similar, we could use a list of style/text tuples.
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
def bottom_toolbar():
return [("class:bottom-toolbar", " This is a toolbar. ")]
style = Style.from_dict({
"bottom-toolbar": "#ffffff bg:#333333",
})
text = prompt("> ", bottom_toolbar=bottom_toolbar, style=style)
print(f"You said: {text}")
The default class name is bottom-toolbar and that will also be used to fill
the background of the toolbar.
Adding a right prompt¶
The prompt() function has out of the box
support for right prompts as well. People familiar to ZSH could recognize this
as the RPROMPT option.
So, similar to adding a bottom toolbar, we can pass an rprompt argument.
This can be either plain text, formatted text or a
callable which returns either.
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
example_style = Style.from_dict({
"rprompt": "bg:#ff0066 #ffffff",
})
def get_rprompt():
return "<rprompt>"
answer = prompt("> ", rprompt=get_rprompt, style=example_style)
The get_rprompt function can return any kind of formatted text such as
HTML. it is also possible to pass text
directly to the rprompt argument of the
prompt() function. It does not have to be a
callable.
Vi input mode¶
Prompt-toolkit supports both Emacs and Vi key bindings, similar to Readline.
The prompt() function will use Emacs bindings by
default. This is done because on most operating systems, also the Bash shell
uses Emacs bindings by default, and that is more intuitive. If however, Vi
binding are required, just pass vi_mode=True.
from prompt_toolkit import prompt
prompt("> ", vi_mode=True)
Adding custom key bindings¶
By default, every prompt already has a set of key bindings which implements the
usual Vi or Emacs behavior. We can extend this by passing another
KeyBindings instance to the
key_bindings argument of the prompt()
function or the PromptSession class.
An example of a prompt that prints 'hello world' when Control-T is
pressed.
from prompt_toolkit import prompt
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.key_binding import KeyBindings
bindings = KeyBindings()
@bindings.add("c-t")
def _(event):
" Say "hello" when `c-t` is pressed. "
def print_hello():
print("hello world")
run_in_terminal(print_hello)
@bindings.add("c-x")
def _(event):
" Exit when `c-x` is pressed. "
event.app.exit()
text = prompt("> ", key_bindings=bindings)
print(f"You said: {text}")
Note that we use
run_in_terminal() for the first key binding.
This ensures that the output of the print-statement and the prompt don’t mix
up. If the key bindings doesn’t print anything, then it can be handled directly
without nesting functions.
Enable key bindings according to a condition¶
Often, some key bindings can be enabled or disabled according to a certain
condition. For instance, the Emacs and Vi bindings will never be active at the
same time, but it is possible to switch between Emacs and Vi bindings at run
time.
In order to enable a key binding according to a certain condition, we have to
pass it a Filter, usually a
Condition instance. (Read more about
filters.)
from prompt_toolkit import prompt
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
bindings = KeyBindings()
@Condition
def is_active():
" Only activate key binding on the second half of each minute. "
return datetime.datetime.now().second > 30
@bindings.add("c-t", filter=is_active)
def _(event):
# ...
pass
prompt("> ", key_bindings=bindings)
Dynamically switch between Emacs and Vi mode¶
The Application has an editing_mode
attribute. We can change the key bindings by changing this attribute from
EditingMode.VI to EditingMode.EMACS.
from prompt_toolkit import prompt
from prompt_toolkit.application.current import get_app
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.key_binding import KeyBindings
def run():
# Create a set of key bindings.
bindings = KeyBindings()
# Add an additional key binding for toggling this flag.
@bindings.add("f4")
def _(event):
" Toggle between Emacs and Vi mode. "
app = event.app
if app.editing_mode == EditingMode.VI:
app.editing_mode = EditingMode.EMACS
else:
app.editing_mode = EditingMode.VI
# Add a toolbar at the bottom to display the current input mode.
def bottom_toolbar():
" Display the current input mode. "
text = "Vi" if get_app().editing_mode == EditingMode.VI else "Emacs"
return [
("class:toolbar", " [F4] %s " % text)
]
prompt("> ", key_bindings=bindings, bottom_toolbar=bottom_toolbar)
run()
Read more about key bindings …
Using control-space for completion¶
An popular short cut that people sometimes use it to use control-space for
opening the autocompletion menu instead of the tab key. This can be done with
the following key binding.
kb = KeyBindings()
@kb.add("c-space")
def _(event):
" Initialize autocompletion, or select the next completion. "
buff = event.app.current_buffer
if buff.complete_state:
buff.complete_next()
else:
buff.start_completion(select_first=False)
Other prompt options¶
Multiline input¶
Reading multiline input is as easy as passing the multiline=True parameter.
from prompt_toolkit import prompt
prompt("> ", multiline=True)
A side effect of this is that the enter key will now insert a newline instead
of accepting and returning the input. The user will now have to press
Meta+Enter in order to accept the input. (Or Escape followed by
Enter.)
It is possible to specify a continuation prompt. This works by passing a
prompt_continuation callable to prompt().
This function is supposed to return formatted text, or
a list of (style, text) tuples. The width of the returned text should not
exceed the given width. (The width of the prompt margin is defined by the
prompt.)
from prompt_toolkit import prompt
def prompt_continuation(width, line_number, is_soft_wrap):
return "." * width
# Or: return [("", "." * width)]
prompt(
"multiline input> ",
multiline=True,
prompt_continuation=prompt_continuation
)
Passing a default¶
A default value can be given:
from prompt_toolkit import prompt
import getpass
prompt("What is your name: ", default=f"{getpass.getuser()}")
Mouse support¶
There is limited mouse support for positioning the cursor, for scrolling (in
case of large multiline inputs) and for clicking in the autocompletion menu.
Enabling can be done by passing the mouse_support=True option.
from prompt_toolkit import prompt
prompt("What is your name: ", mouse_support=True)
Line wrapping¶
Line wrapping is enabled by default. This is what most people are used to and
this is what GNU Readline does. When it is disabled, the input string will
scroll horizontally.
from prompt_toolkit import prompt
prompt("What is your name: ", wrap_lines=False)
Password input¶
When the is_password=True flag has been given, the input is replaced by
asterisks (* characters).
from prompt_toolkit import prompt
prompt("Enter password: ", is_password=True)
Cursor shapes¶
Many terminals support displaying different types of cursor shapes. The most
common are block, beam or underscore. Either blinking or not. It is possible to
decide which cursor to display while asking for input, or in case of Vi input
mode, have a modal prompt for which its cursor shape changes according to the
input mode.
from prompt_toolkit import prompt
from prompt_toolkit.cursor_shapes import CursorShape, ModalCursorShapeConfig
# Several possible values for the `cursor_shape_config` parameter:
prompt(">", cursor=CursorShape.BLOCK)
prompt(">", cursor=CursorShape.UNDERLINE)
prompt(">", cursor=CursorShape.BEAM)
prompt(">", cursor=CursorShape.BLINKING_BLOCK)
prompt(">", cursor=CursorShape.BLINKING_UNDERLINE)
prompt(">", cursor=CursorShape.BLINKING_BEAM)
prompt(">", cursor=ModalCursorShapeConfig())
Adding a frame¶
A frame can be displayed around the input by passing show_frame=True as a
parameter. The color of the frame can be chosen by styling the frame.border
element:
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
style = Style.from_dict(
{
"frame.border": "#884444",
}
)
answer = prompt("Say something > ", style=style, show_frame=True)
print(f"You said: {answer}")
It is also possible to pass a filter, for instance
show_frame=~is_done, so that the frame is only displayed when asking for
input, but hidden once the input is accepted.
from prompt_toolkit import prompt
from prompt_toolkit.filters import is_done
answer = prompt("Say something > ", show_frame=~is_done)
print(f"You said: {answer}")
Prompt in an asyncio application¶
Note
New in prompt_toolkit 3.0. (In prompt_toolkit 2.0 this was possible using a
work-around).
For asyncio applications,
it’s very important to never block the eventloop. However,
prompt() is blocking, and calling this would
freeze the whole application. Asyncio actually won’t even allow us to run that
function within a coroutine.
The answer is to call
prompt_async() instead of
prompt(). The async variation
returns a coroutines and is awaitable.
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
async def my_coroutine():
session = PromptSession()
while True:
with patch_stdout():
result = await session.prompt_async("Say something: ")
print(f"You said: {result}")
The patch_stdout() context manager is
optional, but it’s recommended, because other coroutines could print to stdout.
This ensures that other output won’t destroy the prompt.
Reading keys from stdin, one key at a time, but without a prompt¶
Suppose that you want to use prompt_toolkit to read the keys from stdin, one
key at a time, but not render a prompt to the output, that is also possible:
import asyncio
from prompt_toolkit.input import create_input
from prompt_toolkit.keys import Keys
async def main() -> None:
done = asyncio.Event()
input = create_input()
def keys_ready():
for key_press in input.read_keys():
print(key_press)
if key_press.key == Keys.ControlC:
done.set()
with input.raw_mode():
with input.attach(keys_ready):
await done.wait()
if __name__ == "__main__":
asyncio.run(main())
The above snippet will print the KeyPress object whenever a key is pressed.
This is also cross platform, and should work on Windows.
On this page
On this page
Asking for input (prompts)
Hello world
The PromptSession object
Syntax highlighting
Colors
Using a Pygments style
Coloring the prompt itself
Autocompletion
Nested completion
A custom completer
Styling individual completions
Fuzzy completion
Complete while typing
Asynchronous completion
Input validation
Validator from a callable
History
Auto suggestion
Adding a bottom toolbar
Adding a right prompt
Vi input mode
Adding custom key bindings
Enable key bindings according to a condition
Dynamically switch between Emacs and Vi mode
Using control-space for completion
Other prompt options
Multiline input
Passing a default
Mouse support
Line wrapping
Password input
Cursor shapes
Adding a frame
Prompt in an asyncio application
Reading keys from stdin, one key at a time, but without a prompt
Previous
Printing (and using) formatted text
Next
Asking for a choice
Documentation
Package
Repository
Issues
prompt_toolkit
2014-2024, Jonathan Slenders
Built with Sphinx 8.2.3 and Nefertiti 0.8.6
