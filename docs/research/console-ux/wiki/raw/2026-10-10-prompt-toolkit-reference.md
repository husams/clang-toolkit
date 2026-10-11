Source: https://python-prompt-toolkit.readthedocs.io/en/3.0.52/pages/reference.html
Fetched: 2026-10-10
Description: Official prompt_toolkit reference documentation
Version: 3.0.52; project lockfile: 3.0.53

Reference — prompt_toolkit 3.0.52 documentation
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
Reference
Reference¶
Application¶
class prompt_toolkit.application.AppSession(input: Input | None = None, output: Output | None = None)¶
An AppSession is an interactive session, usually connected to one terminal.
Within one such session, interaction with many applications can happen, one
after the other.
The input/output device is not supposed to change during one session.
Warning: Always use the create_app_session function to create an
instance, so that it gets activated correctly.
Parameters:
input – Use this as a default input for all applications
running in this session, unless an input is passed to the Application
explicitly.
output – Use this as a default output.
class prompt_toolkit.application.Application(layout: Layout | None = None, style: BaseStyle | None = None, include_default_pygments_style: FilterOrBool = True, style_transformation: StyleTransformation | None = None, key_bindings: KeyBindingsBase | None = None, clipboard: Clipboard | None = None, full_screen: bool = False, color_depth: ColorDepth | Callable[[], ColorDepth | None] | None = None, mouse_support: FilterOrBool = False, enable_page_navigation_bindings: None | FilterOrBool = None, paste_mode: FilterOrBool = False, editing_mode: EditingMode = EditingMode.EMACS, erase_when_done: bool = False, reverse_vi_search_direction: FilterOrBool = False, min_redraw_interval: float | int | None = None, max_render_postpone_time: float | int | None = 0.01, refresh_interval: float | None = None, terminal_size_polling_interval: float | None = 0.5, cursor: AnyCursorShapeConfig = None, on_reset: ApplicationEventHandler[_AppResult] | None = None, on_invalidate: ApplicationEventHandler[_AppResult] | None = None, before_render: ApplicationEventHandler[_AppResult] | None = None, after_render: ApplicationEventHandler[_AppResult] | None = None, input: Input | None = None, output: Output | None = None)¶
The main Application class!
This glues everything together.
Parameters:
layout – A Layout instance.
key_bindings – KeyBindingsBase instance for
the key bindings.
clipboard – Clipboard to use.
full_screen – When True, run the application on the alternate screen buffer.
color_depth – Any ColorDepth value, a callable that
returns a ColorDepth or None for default.
erase_when_done – (bool) Clear the application output when it finishes.
reverse_vi_search_direction – Normally, in Vi mode, a ‘/’ searches
forward and a ‘?’ searches backward. In Readline mode, this is usually
reversed.
min_redraw_interval –
Number of seconds to wait between redraws. Use
this for applications where invalidate is called a lot. This could cause
a lot of terminal output, which some terminals are not able to process.
None means that every invalidate will be scheduled right away
(which is usually fine).
When one invalidate is called, but a scheduled redraw of a previous
invalidate call has not been executed yet, nothing will happen in any
case.
max_render_postpone_time – When there is high CPU (a lot of other
scheduled calls), postpone the rendering max x seconds.  ‘0’ means:
don’t postpone. ‘.5’ means: try to draw at least twice a second.
refresh_interval – Automatically invalidate the UI every so many
seconds. When None (the default), only invalidate when invalidate
has been called.
terminal_size_polling_interval – Poll the terminal size every so many
seconds. Useful if the applications runs in a thread other then then
main thread where SIGWINCH can’t be handled, or on Windows.
Filters:
Parameters:
mouse_support – (Filter or
boolean). When True, enable mouse support.
paste_mode – Filter or boolean.
editing_mode – EditingMode.
enable_page_navigation_bindings – When True, enable the page
navigation key bindings. These include both Emacs and Vi bindings like
page-up, page-down and so on to scroll through pages. Mostly useful for
creating an editor or other full screen applications. Probably, you
don’t want this for the implementation of a REPL. By default, this is
enabled if full_screen is set.
Callbacks (all of these should accept an
Application object as input.)
Parameters:
on_reset – Called during reset.
on_invalidate – Called when the UI has been invalidated.
before_render – Called right before rendering.
after_render – Called right after rendering.
I/O:
(Note that the preferred way to change the input/output is by creating an
AppSession with the required input/output objects. If you need multiple
applications running at the same time, you have to create a separate
AppSession using a with create_app_session(): block.
Parameters:
input – Input instance.
output – Output instance. (Probably
Vt100_Output or Win32Output.)
Usage:
app = Application(…)
app.run()
# Or
await app.run_async()
async cancel_and_wait_for_background_tasks() → None¶
Cancel all background tasks, and wait for the cancellation to complete.
If any of the background tasks raised an exception, this will also
propagate the exception.
(If we had nurseries like Trio, this would be the __aexit__ of a
nursery.)
property color_depth: ColorDepth¶
The active ColorDepth.
The current value is determined as follows:
If a color depth was given explicitly to this application, use that
value.
Otherwise, fall back to the color depth that is reported by the
Output implementation. If the Output class was
created using output.defaults.create_output, then this value is
coming from the $PROMPT_TOOLKIT_COLOR_DEPTH environment variable.
cpr_not_supported_callback() → None¶
Called when we don’t receive the cursor position response in time.
create_background_task(coroutine: Coroutine[Any, Any, None]) → Task[None]¶
Start a background task (coroutine) for the running application. When
the Application terminates, unfinished background tasks will be
cancelled.
Given that we still support Python versions before 3.11, we can’t use
task groups (and exception groups), because of that, these background
tasks are not allowed to raise exceptions. If they do, we’ll call the
default exception handler from the event loop.
If at some point, we have Python 3.11 as the minimum supported Python
version, then we can use a TaskGroup (with the lifetime of
Application.run_async(), and run run the background tasks in there.
This is not threadsafe.
property current_buffer: Buffer¶
The currently focused Buffer.
(This returns a dummy Buffer when none of the actual buffers
has the focus. In this case, it’s really not practical to check for
None values or catch exceptions every time.)
property current_search_state: SearchState¶
Return the current SearchState. (The one for the focused
BufferControl.)
exit(result: _AppResult | None = None, exception: BaseException | type[BaseException] | None = None, style: str = '') → None¶
Exit application.
Note
If Application.exit is called before Application.run() is
called, then the Application won’t exit (because the
Application.future doesn’t correspond to the current run). Use a
pre_run hook and an event to synchronize the closing if there’s a
chance this can happen.
Parameters:
result – Set this result for the application.
exception – Set this exception as the result for an application. For
a prompt, this is often EOFError or KeyboardInterrupt.
style – Apply this style on the whole content when quitting,
often this is ‘class:exiting’ for a prompt. (Used when
erase_when_done is not set.)
get_used_style_strings() → list[str]¶
Return a list of used style strings. This is helpful for debugging, and
for writing a new Style.
invalidate() → None¶
Thread safe way of sending a repaint trigger to the input event loop.
property invalidated: bool¶
True when a redraw operation has been scheduled.
property is_running: bool¶
True when the application is currently active/running.
key_processor¶
The InputProcessor instance.
print_text(text: AnyFormattedText, style: BaseStyle | None = None) → None¶
Print a list of (style_str, text) tuples to the output.
(When the UI is running, this method has to be called through
run_in_terminal, otherwise it will destroy the UI.)
Parameters:
text – List of (style_str, text) tuples.
style – Style class to use. Defaults to the active style in the CLI.
quoted_insert¶
Quoted insert. This flag is set if we go into quoted insert mode.
render_counter¶
Render counter. This one is increased every time the UI is rendered.
It can be used as a key for caching certain information during one
rendering.
reset() → None¶
Reset everything, for reading the next input.
run(pre_run: Callable[[], None] | None = None, set_exception_handler: bool = True, handle_sigint: bool = True, in_thread: bool = False, inputhook: Callable[[InputHookContext], None] | None = None) → _AppResult¶
A blocking ‘run’ call that waits until the UI is finished.
This will run the application in a fresh asyncio event loop.
Parameters:
pre_run – Optional callable, which is called right after the
“reset” of the application.
set_exception_handler – When set, in case of an exception, go out
of the alternate screen and hide the application, display the
exception, and wait for the user to press ENTER.
in_thread – When true, run the application in a background
thread, and block the current thread until the application
terminates. This is useful if we need to be sure the application
won’t use the current event loop (asyncio does not support nested
event loops). A new event loop will be created in this background
thread, and that loop will also be closed when the background
thread terminates. When this is used, it’s especially important to
make sure that all asyncio background tasks are managed through
get_appp().create_background_task(), so that unfinished tasks are
properly cancelled before the event loop is closed. This is used
for instance in ptpython.
handle_sigint – Handle SIGINT signal. Call the key binding for
Keys.SIGINT. (This only works in the main thread.)
async run_async(pre_run: Callable[[], None] | None = None, set_exception_handler: bool = True, handle_sigint: bool = True, slow_callback_duration: float = 0.5) → _AppResult¶
Run the prompt_toolkit Application
until exit() has been
called. Return the value that was passed to
exit().
This is the main entry point for a prompt_toolkit
Application and usually the only
place where the event loop is actually running.
Parameters:
pre_run – Optional callable, which is called right after the
“reset” of the application.
set_exception_handler – When set, in case of an exception, go out
of the alternate screen and hide the application, display the
exception, and wait for the user to press ENTER.
handle_sigint – Handle SIGINT signal if possible. This will call
the <sigint> key binding when a SIGINT is received. (This only
works in the main thread.)
slow_callback_duration – Display warnings if code scheduled in
the asyncio event loop takes more time than this. The asyncio
default of 0.1 is sometimes not sufficient on a slow system,
because exceptionally, the drawing of the app, which happens in the
event loop, can take a bit longer from time to time.
async run_system_command(command: str, wait_for_enter: bool = True, display_before_text: AnyFormattedText = '', wait_text: str = 'Press ENTER to continue...') → None¶
Run system command (While hiding the prompt. When finished, all the
output will scroll above the prompt.)
Parameters:
command – Shell command to be executed.
wait_for_enter – FWait for the user to press enter, when the
command is finished.
display_before_text – If given, text to be displayed before the
command executes.
Returns:
A Future object.
suspend_to_background(suspend_group: bool = True) → None¶
(Not thread safe – to be called from inside the key bindings.)
Suspend process.
Parameters:
suspend_group – When true, suspend the whole process group.
(This is the default, and probably what you want.)
timeoutlen¶
Like Vim’s timeoutlen option. This can be None or a float.  For
instance, suppose that we have a key binding AB and a second key
binding A. If the uses presses A and then waits, we don’t handle
this binding yet (unless it was marked ‘eager’), because we don’t
know what will follow. This timeout is the maximum amount of time
that we wait until we call the handlers anyway. Pass None to
disable this timeout.
ttimeoutlen¶
When to flush the input (For flushing escape keys.) This is important
on terminals that use vt100 input. We can’t distinguish the escape
key from for instance the left-arrow key, if we don’t know what follows
after “x1b”. This little timer will consider “x1b” to be escape if
nothing did follow in this time span.
This seems to work like the ttimeoutlen option in Vim.
vi_state¶
Vi state. (For Vi key bindings.)
class prompt_toolkit.application.DummyApplication¶
When no Application is running,
get_app() will run an instance of this DummyApplication instead.
prompt_toolkit.application.create_app_session(input: Input | None = None, output: Output | None = None) → Generator[AppSession, None, None]¶
Create a separate AppSession.
This is useful if there can be multiple individual AppSession’s going
on. Like in the case of a Telnet/SSH server.
prompt_toolkit.application.get_app() → Application[Any]¶
Get the current active (running) Application.
An Application is active during the
Application.run_async() call.
We assume that there can only be one Application active at the
same time. There is only one terminal window, with only one stdin and
stdout. This makes the code significantly easier than passing around the
Application everywhere.
If no Application is running, then return by default a
DummyApplication. For practical reasons, we prefer to not raise
an exception. This way, we don’t have to check all over the place whether
an actual Application was returned.
(For applications like pymux where we can have more than one Application,
we’ll use a work-around to handle that.)
prompt_toolkit.application.get_app_or_none() → Application[Any] | None¶
Get the current active (running) Application, or return None if no
application is running.
prompt_toolkit.application.in_terminal(render_cli_done: bool = False) → AsyncGenerator[None, None]¶
Asynchronous context manager that suspends the current application and runs
the body in the terminal.
async def f():
async with in_terminal():
call_some_function()
await call_some_async_function()
prompt_toolkit.application.run_in_terminal(func: Callable[[], _T], render_cli_done: bool = False, in_executor: bool = False) → Awaitable[_T]¶
Run function on the terminal above the current application or prompt.
What this does is first hiding the prompt, then running this callable
(which can safely output to the terminal), and then again rendering the
prompt which causes the output of this function to scroll above the
prompt.
func is supposed to be a synchronous function. If you need an
asynchronous version of this function, use the in_terminal context
manager directly.
Parameters:
func – The callable to execute.
render_cli_done – When True, render the interface in the
‘Done’ state first, then execute the function. If False,
erase the interface first.
in_executor – When True, run in executor. (Use this for long
blocking functions, when you don’t want to block the event loop.)
Returns:
A Future.
prompt_toolkit.application.set_app(app: Application[Any]) → Generator[None, None, None]¶
Context manager that sets the given Application active in an
AppSession.
This should only be called by the Application itself.
The application will automatically be active while its running. If you want
the application to be active in other threads/coroutines, where that’s not
the case, use contextvars.copy_context(), or use Application.context to
run it in the appropriate context.
Formatted text¶
Many places in prompt_toolkit can take either plain text, or formatted text.
For instance the prompt() function takes either
plain text or formatted text for the prompt. The
FormattedTextControl can also take either plain
text or formatted text.
In any case, there is an input that can either be just plain text (a string),
an HTML object, an ANSI object or a sequence of
(style_string, text) tuples. The to_formatted_text() conversion
function takes any of these and turns all of them into such a tuple sequence.
class prompt_toolkit.formatted_text.ANSI(value: str)¶
ANSI formatted text.
Take something ANSI escaped text, for use as a formatted string. E.g.
ANSI('\x1b[31mhello \x1b[32mworld')
Characters between \001 and \002 are supposed to have a zero width
when printed, but these are literally sent to the terminal output. This can
be used for instance, for inserting Final Term prompt commands.  They will
be translated into a prompt_toolkit ‘[ZeroWidthEscape]’ fragment.
format(*args: str, **kwargs: str) → ANSI¶
Like str.format, but make sure that the arguments are properly
escaped. (No ANSI escapes can be injected.)
class prompt_toolkit.formatted_text.FormattedText(iterable=(), /)¶
A list of (style, text) tuples.
(In some situations, this can also be (style, text, mouse_handler)
tuples.)
class prompt_toolkit.formatted_text.HTML(value: str)¶
HTML formatted text.
Take something HTML-like, for use as a formatted string.
# Turn something into red.
HTML('<style fg="ansired" bg="#00ff44">...</style>')
# Italic, bold, underline and strike.
HTML('<i>...</i>')
HTML('<b>...</b>')
HTML('<u>...</u>')
HTML('<s>...</s>')
All HTML elements become available as a “class” in the style sheet.
E.g. <username>...</username> can be styled, by setting a style for
username.
format(*args: object, **kwargs: object) → HTML¶
Like str.format, but make sure that the arguments are properly
escaped.
class prompt_toolkit.formatted_text.PygmentsTokens(token_list: list[tuple[Token, str]])¶
Turn a pygments token list into a list of prompt_toolkit text fragments
((style_str, text) tuples).
class prompt_toolkit.formatted_text.Template(text: str)¶
Template for string interpolation with formatted text.
Example:
Template(' ... {} ... ').format(HTML(...))
Parameters:
text – Plain text.
prompt_toolkit.formatted_text.fragment_list_len(fragments: StyleAndTextTuples) → int¶
Return the amount of characters in this text fragment list.
Parameters:
fragments – List of (style_str, text) or
(style_str, text, mouse_handler) tuples.
prompt_toolkit.formatted_text.fragment_list_to_text(fragments: StyleAndTextTuples) → str¶
Concatenate all the text parts again.
Parameters:
fragments – List of (style_str, text) or
(style_str, text, mouse_handler) tuples.
prompt_toolkit.formatted_text.fragment_list_width(fragments: StyleAndTextTuples) → int¶
Return the character width of this text fragment list.
(Take double width characters into account.)
Parameters:
fragments – List of (style_str, text) or
(style_str, text, mouse_handler) tuples.
prompt_toolkit.formatted_text.is_formatted_text(value: object) → TypeGuard[AnyFormattedText]¶
Check whether the input is valid formatted text (for use in assert
statements).
In case of a callable, it doesn’t check the return type.
prompt_toolkit.formatted_text.merge_formatted_text(items: Iterable[AnyFormattedText]) → AnyFormattedText¶
Merge (Concatenate) several pieces of formatted text together.
prompt_toolkit.formatted_text.split_lines(fragments: Iterable[OneStyleAndTextTuple]) → Iterable[StyleAndTextTuples]¶
Take a single list of (style_str, text) tuples and yield one such list for each
line. Just like str.split, this will yield at least one item.
Parameters:
fragments – Iterable of (style_str, text) or
(style_str, text, mouse_handler) tuples.
prompt_toolkit.formatted_text.to_formatted_text(value: AnyFormattedText, style: str = '', auto_convert: bool = False) → FormattedText¶
Convert the given value (which can be formatted text) into a list of text
fragments. (Which is the canonical form of formatted text.) The outcome is
always a FormattedText instance, which is a list of (style, text) tuples.
It can take a plain text string, an HTML or ANSI object, anything that
implements __pt_formatted_text__ or a callable that takes no arguments and
returns one of those.
Parameters:
style – An additional style string which is applied to all text
fragments.
auto_convert – If True, also accept other types, and convert them
to a string first.
prompt_toolkit.formatted_text.to_plain_text(value: AnyFormattedText) → str¶
Turn any kind of formatted text back into plain text.
Buffer¶
Data structures for the Buffer.
It holds the text, cursor position, history, etc…
class prompt_toolkit.buffer.Buffer(completer: Completer | None = None, auto_suggest: AutoSuggest | None = None, history: History | None = None, validator: Validator | None = None, tempfile_suffix: str | Callable[[], str] = '', tempfile: str | Callable[[], str] = '', name: str = '', complete_while_typing: Filter | bool = False, validate_while_typing: Filter | bool = False, enable_history_search: Filter | bool = False, document: Document | None = None, accept_handler: Callable[[Buffer], bool] | None = None, read_only: Filter | bool = False, multiline: Filter | bool = True, max_number_of_completions: int = 10000, on_text_changed: Callable[[Buffer], None] | None = None, on_text_insert: Callable[[Buffer], None] | None = None, on_cursor_position_changed: Callable[[Buffer], None] | None = None, on_completions_changed: Callable[[Buffer], None] | None = None, on_suggestion_set: Callable[[Buffer], None] | None = None)¶
The core data structure that holds the text and cursor position of the
current input line and implements all text manipulations on top of it. It
also implements the history, undo stack and the completion state.
Parameters:
completer – Completer instance.
history – History instance.
tempfile_suffix – The tempfile suffix (extension) to be used for the
“open in editor” function. For a Python REPL, this would be “.py”, so
that the editor knows the syntax highlighting to use. This can also be
a callable that returns a string.
tempfile – For more advanced tempfile situations where you need
control over the subdirectories and filename. For a Git Commit Message,
this would be “.git/COMMIT_EDITMSG”, so that the editor knows the syntax
highlighting to use. This can also be a callable that returns a string.
name – Name for this buffer. E.g. DEFAULT_BUFFER. This is mostly
useful for key bindings where we sometimes prefer to refer to a buffer
by their name instead of by reference.
accept_handler –
Called when the buffer input is accepted. (Usually
when the user presses enter.) The accept handler receives this
Buffer as input and should return True when the buffer text should be
kept instead of calling reset.
In case of a PromptSession for instance, we want to keep the text,
because we will exit the application, and only reset it during the next
run.
max_number_of_completions – Never display more than this number of
completions, even when the completer can produce more (limited by
default to 10k for performance).
Events:
Parameters:
on_text_changed – When the buffer text changes. (Callable or None.)
on_text_insert – When new text is inserted. (Callable or None.)
on_cursor_position_changed – When the cursor moves. (Callable or None.)
on_completions_changed – When the completions were changed. (Callable or None.)
on_suggestion_set – When an auto-suggestion text has been set. (Callable or None.)
Filters:
Parameters:
complete_while_typing – Filter
or bool. Decide whether or not to do asynchronous autocompleting while
typing.
validate_while_typing – Filter
or bool. Decide whether or not to do asynchronous validation while
typing.
enable_history_search – Filter or
bool to indicate when up-arrow partial string matching is enabled. It
is advised to not enable this at the same time as
complete_while_typing, because when there is an autocompletion found,
the up arrows usually browse through the completions, rather than
through the history.
read_only – Filter. When True,
changes will not be allowed.
multiline – Filter or bool. When
not set, pressing Enter will call the accept_handler.  Otherwise,
pressing Esc-Enter is required.
append_to_history() → None¶
Append the current input to the history.
apply_completion(completion: Completion) → None¶
Insert a given completion.
apply_search(search_state: SearchState, include_current_position: bool = True, count: int = 1) → None¶
Apply search. If something is found, set working_index and
cursor_position.
auto_down(count: int = 1, go_to_start_of_line_if_history_changes: bool = False) → None¶
If we’re not on the last line (of a multiline input) go a line down,
otherwise go forward in history. (If nothing is selected.)
auto_up(count: int = 1, go_to_start_of_line_if_history_changes: bool = False) → None¶
If we’re not on the first line (of a multiline input) go a line up,
otherwise go back in history. (If nothing is selected.)
cancel_completion() → None¶
Cancel completion, go back to the original text.
complete_next(count: int = 1, disable_wrap_around: bool = False) → None¶
Browse to the next completions.
(Does nothing if there are no completion.)
complete_previous(count: int = 1, disable_wrap_around: bool = False) → None¶
Browse to the previous completions.
(Does nothing if there are no completion.)
copy_selection(_cut: bool = False) → ClipboardData¶
Copy selected text and return ClipboardData instance.
Notice that this doesn’t store the copied data on the clipboard yet.
You can store it like this:
data = buffer.copy_selection()
get_app().clipboard.set_data(data)
cursor_down(count: int = 1) → None¶
(for multiline edit). Move cursor to the next line.
cursor_up(count: int = 1) → None¶
(for multiline edit). Move cursor to the previous line.
cut_selection() → ClipboardData¶
Delete selected text and return ClipboardData instance.
delete(count: int = 1) → str¶
Delete specified number of characters and Return the deleted text.
delete_before_cursor(count: int = 1) → str¶
Delete specified number of characters before cursor and return the
deleted text.
property document: Document¶
Return Document instance from the
current text, cursor position and selection state.
document_for_search(search_state: SearchState) → Document¶
Return a Document instance that has
the text/cursor position for this search, if we would apply it. This
will be used in the
BufferControl to display feedback while
searching.
get_search_position(search_state: SearchState, include_current_position: bool = True, count: int = 1) → int¶
Get the cursor position for this search.
(This operation won’t change the working_index. It’s won’t go through
the history. Vi text objects can’t span multiple items.)
go_to_completion(index: int | None) → None¶
Select a completion from the list of current completions.
go_to_history(index: int) → None¶
Go to this item in the history.
history_backward(count: int = 1) → None¶
Move backwards through history.
history_forward(count: int = 1) → None¶
Move forwards through the history.
Parameters:
count – Amount of items to move forward.
insert_line_above(copy_margin: bool = True) → None¶
Insert a new line above the current one.
insert_line_below(copy_margin: bool = True) → None¶
Insert a new line below the current one.
insert_text(data: str, overwrite: bool = False, move_cursor: bool = True, fire_event: bool = True) → None¶
Insert characters at cursor position.
Parameters:
fire_event – Fire on_text_insert event. This is mainly used to
trigger autocompletion while typing.
property is_returnable: bool¶
True when there is something handling accept.
join_next_line(separator: str = ' ') → None¶
Join the next line to the current one by deleting the line ending after
the current line.
join_selected_lines(separator: str = ' ') → None¶
Join the selected lines.
load_history_if_not_yet_loaded() → None¶
Create task for populating the buffer history (if not yet done).
Note:
This needs to be called from within the event loop of the
application, because history loading is async, and we need to be
sure the right event loop is active. Therefor, we call this method
in the `BufferControl.create_content`.
There are situations where prompt_toolkit applications are created
in one thread, but will later run in a different thread (Ptpython
is one example. The REPL runs in a separate thread, in order to
prevent interfering with a potential different event loop in the
main thread. The REPL UI however is still created in the main
thread.) We could decide to not support creating prompt_toolkit
objects in one thread and running the application in a different
thread, but history loading is the only place where it matters, and
this solves it.
newline(copy_margin: bool = True) → None¶
Insert a line ending at the current position.
open_in_editor(validate_and_handle: bool = False) → Task[None]¶
Open code in editor.
This returns a future, and runs in a thread executor.
paste_clipboard_data(data: ClipboardData, paste_mode: PasteMode = PasteMode.EMACS, count: int = 1) → None¶
Insert the data from the clipboard.
reset(document: Document | None = None, append_to_history: bool = False) → None¶
Parameters:
append_to_history – Append current input to history first.
save_to_undo_stack(clear_redo_stack: bool = True) → None¶
Safe current state (input text and cursor position), so that we can
restore it by calling undo.
set_document(value: Document, bypass_readonly: bool = False) → None¶
Set Document instance. Like the
document property, but accept an bypass_readonly argument.
Parameters:
bypass_readonly – When True, don’t raise an
EditReadOnlyBuffer exception, even
when the buffer is read-only.
Warning
When this buffer is read-only and bypass_readonly was not passed,
the EditReadOnlyBuffer exception will be caught by the
KeyProcessor and is silently suppressed. This is important to
keep in mind when writing key bindings, because it won’t do what
you expect, and there won’t be a stack trace. Use try/finally
around this function if you need some cleanup code.
start_completion(select_first: bool = False, select_last: bool = False, insert_common_part: bool = False, complete_event: CompleteEvent | None = None) → None¶
Start asynchronous autocompletion of this buffer.
(This will do nothing if a previous completion was still in progress.)
start_history_lines_completion() → None¶
Start a completion based on all the other lines in the document and the
history.
start_selection(selection_type: SelectionType = SelectionType.CHARACTERS) → None¶
Take the current cursor position as the start of this selection.
swap_characters_before_cursor() → None¶
Swap the last two characters before the cursor.
transform_current_line(transform_callback: Callable[[str], str]) → None¶
Apply the given transformation function to the current line.
Parameters:
transform_callback – callable that takes a string and return a new string.
transform_lines(line_index_iterator: Iterable[int], transform_callback: Callable[[str], str]) → str¶
Transforms the text on a range of lines.
When the iterator yield an index not in the range of lines that the
document contains, it skips them silently.
To uppercase some lines:
new_text = transform_lines(range(5,10), lambda text: text.upper())
Parameters:
line_index_iterator – Iterator of line numbers (int)
transform_callback – callable that takes the original text of a
line, and return the new text for this line.
Returns:
The new text.
transform_region(from_: int, to: int, transform_callback: Callable[[str], str]) → None¶
Transform a part of the input string.
Parameters:
from – (int) start position.
to – (int) end position.
transform_callback – Callable which accepts a string and returns
the transformed string.
validate(set_cursor: bool = False) → bool¶
Returns True if valid.
Parameters:
set_cursor – Set the cursor position, if an error was found.
validate_and_handle() → None¶
Validate buffer and handle the accept action.
yank_last_arg(n: int | None = None) → None¶
Like yank_nth_arg, but if no argument has been given, yank the last
word by default.
yank_nth_arg(n: int | None = None, _yank_last_arg: bool = False) → None¶
Pick nth word from previous history entry (depending on current
yank_nth_arg_state) and insert it at current position. Rotate through
history if called repeatedly. If no n has been given, take the first
argument. (The second word.)
Parameters:
n – (None or int), The index of the word from the previous line
to take.
class prompt_toolkit.buffer.CompletionState(original_document: Document, completions: list[Completion] | None = None, complete_index: int | None = None)¶
Immutable class that contains a completion state.
complete_index¶
Position in the completions array.
This can be None to indicate “no completion”, the original text.
completions¶
List of all the current Completion instances which are possible at
this point.
property current_completion: Completion | None¶
Return the current completion, or return None when no completion is
selected.
go_to_index(index: int | None) → None¶
Create a new CompletionState object with the new index.
When index is None deselect the completion.
new_text_and_position() → tuple[str, int]¶
Return (new_text, new_cursor_position) for this completion.
original_document¶
Document as it was when the completion started.
exception prompt_toolkit.buffer.EditReadOnlyBuffer¶
Attempt editing of read-only Buffer.
prompt_toolkit.buffer.indent(buffer: Buffer, from_row: int, to_row: int, count: int = 1) → None¶
Indent text of a Buffer object.
prompt_toolkit.buffer.reshape_text(buffer: Buffer, from_row: int, to_row: int) → None¶
Reformat text, taking the width into account.
to_row is included.
(Vi ‘gq’ operator.)
prompt_toolkit.buffer.unindent(buffer: Buffer, from_row: int, to_row: int, count: int = 1) → None¶
Unindent text of a Buffer object.
Selection¶
Data structures for the selection.
class prompt_toolkit.selection.SelectionState(original_cursor_position: int = 0, type: SelectionType = SelectionType.CHARACTERS)¶
State of the current selection.
Parameters:
original_cursor_position – int
type – SelectionType
class prompt_toolkit.selection.SelectionType(value)¶
Type of selection.
BLOCK = 'BLOCK'¶
A block selection. (Visual-Block in Vi.)
CHARACTERS = 'CHARACTERS'¶
Characters. (Visual in Vi.)
LINES = 'LINES'¶
Whole lines. (Visual-Line in Vi.)
Clipboard¶
class prompt_toolkit.clipboard.Clipboard¶
Abstract baseclass for clipboards.
(An implementation can be in memory, it can share the X11 or Windows
keyboard, or can be persistent.)
abstractmethod get_data() → ClipboardData¶
Return clipboard data.
rotate() → None¶
For Emacs mode, rotate the kill ring.
abstractmethod set_data(data: ClipboardData) → None¶
Set data to the clipboard.
Parameters:
data – ClipboardData instance.
set_text(text: str) → None¶
Shortcut for setting plain text on clipboard.
class prompt_toolkit.clipboard.ClipboardData(text: str = '', type: SelectionType = SelectionType.CHARACTERS)¶
Text on the clipboard.
Parameters:
text – string
type – SelectionType
class prompt_toolkit.clipboard.DummyClipboard¶
Clipboard implementation that doesn’t remember anything.
class prompt_toolkit.clipboard.DynamicClipboard(get_clipboard: Callable[[], Clipboard | None])¶
Clipboard class that can dynamically returns any Clipboard.
Parameters:
get_clipboard – Callable that returns a Clipboard instance.
class prompt_toolkit.clipboard.InMemoryClipboard(data: ClipboardData | None = None, max_size: int = 60)¶
Default clipboard implementation.
Just keep the data in memory.
This implements a kill-ring, for Emacs mode.
class prompt_toolkit.clipboard.pyperclip.PyperclipClipboard¶
Clipboard that synchronizes with the Windows/Mac/Linux system clipboard,
using the pyperclip module.
Auto completion¶
class prompt_toolkit.completion.CompleteEvent(text_inserted: bool = False, completion_requested: bool = False)¶
Event that called the completer.
Parameters:
text_inserted – When True, it means that completions are requested
because of a text insert. (Buffer.complete_while_typing.)
completion_requested – When True, it means that the user explicitly
pressed the Tab key in order to view the completions.
These two flags can be used for instance to implement a completer that
shows some completions when Tab has been pressed, but not
automatically when the user presses a space. (Because of
complete_while_typing.)
completion_requested¶
Used explicitly requested completion by pressing ‘tab’.
text_inserted¶
Automatic completion while typing.
class prompt_toolkit.completion.Completer¶
Base class for completer implementations.
abstractmethod get_completions(document: Document, complete_event: CompleteEvent) → Iterable[Completion]¶
This should be a generator that yields Completion instances.
If the generation of completions is something expensive (that takes a
lot of time), consider wrapping this Completer class in a
ThreadedCompleter. In that case, the completer algorithm runs in a
background thread and completions will be displayed as soon as they
arrive.
Parameters:
document – Document instance.
complete_event – CompleteEvent instance.
async get_completions_async(document: Document, complete_event: CompleteEvent) → AsyncGenerator[Completion, None]¶
Asynchronous generator for completions. (Probably, you won’t have to
override this.)
Asynchronous generator of Completion objects.
class prompt_toolkit.completion.Completion(text: str, start_position: int = 0, display: AnyFormattedText | None = None, display_meta: AnyFormattedText | None = None, style: str = '', selected_style: str = '')¶
Parameters:
text – The new string that will be inserted into the document.
start_position – Position relative to the cursor_position where the
new text will start. The text will be inserted between the
start_position and the original cursor position.
display – (optional string or formatted text) If the completion has
to be displayed differently in the completion menu.
display_meta – (Optional string or formatted text) Meta information
about the completion, e.g. the path or source where it’s coming from.
This can also be a callable that returns a string.
style – Style string.
selected_style – Style string, used for a selected completion.
This can override the style parameter.
property display_meta: StyleAndTextTuples¶
Return meta-text. (This is lazy when using a callable).
property display_meta_text: str¶
The ‘meta’ field as plain text.
property display_text: str¶
The ‘display’ field as plain text.
new_completion_from_position(position: int) → Completion¶
(Only for internal use!)
Get a new completion by splitting this one. Used by Application when
it needs to have a list of new completions after inserting the common
prefix.
class prompt_toolkit.completion.ConditionalCompleter(completer: Completer, filter: Filter | bool)¶
Wrapper around any other completer that will enable/disable the completions
depending on whether the received condition is satisfied.
Parameters:
completer – Completer instance.
filter – Filter instance.
class prompt_toolkit.completion.DeduplicateCompleter(completer: Completer)¶
Wrapper around a completer that removes duplicates. Only the first unique
completions are kept.
Completions are considered to be a duplicate if they result in the same
document text when they would be applied.
class prompt_toolkit.completion.DummyCompleter¶
A completer that doesn’t return any completion.
class prompt_toolkit.completion.DynamicCompleter(get_completer: Callable[[], Completer | None])¶
Completer class that can dynamically returns any Completer.
Parameters:
get_completer – Callable that returns a Completer instance.
class prompt_toolkit.completion.ExecutableCompleter¶
Complete only executable files in the current path.
class prompt_toolkit.completion.FuzzyCompleter(completer: Completer, WORD: bool = False, pattern: str | None = None, enable_fuzzy: Filter | bool = True)¶
Fuzzy completion.
This wraps any other completer and turns it into a fuzzy completer.
If the list of words is: [“leopard” , “gorilla”, “dinosaur”, “cat”, “bee”]
Then trying to complete “oar” would yield “leopard” and “dinosaur”, but not
the others, because they match the regular expression ‘o.*a.*r’.
Similar, in another application “djm” could expand to “django_migrations”.
The results are sorted by relevance, which is defined as the start position
and the length of the match.
Notice that this is not really a tool to work around spelling mistakes,
like what would be possible with difflib. The purpose is rather to have a
quicker or more intuitive way to filter the given completions, especially
when many completions have a common prefix.
Fuzzy algorithm is based on this post:
https://blog.amjith.com/fuzzyfinder-in-10-lines-of-python
Parameters:
completer – A Completer instance.
WORD – When True, use WORD characters.
pattern – Regex pattern which selects the characters before the
cursor that are considered for the fuzzy matching.
enable_fuzzy – (bool or Filter) Enabled the fuzzy behavior. For
easily turning fuzzyness on or off according to a certain condition.
class prompt_toolkit.completion.FuzzyWordCompleter(words: Sequence[str] | Callable[[], Sequence[str]], meta_dict: dict[str, str] | None = None, WORD: bool = False)¶
Fuzzy completion on a list of words.
(This is basically a WordCompleter wrapped in a FuzzyCompleter.)
Parameters:
words – List of words or callable that returns a list of words.
meta_dict – Optional dict mapping words to their meta-information.
WORD – When True, use WORD characters.
class prompt_toolkit.completion.NestedCompleter(options: dict[str, Completer | None], ignore_case: bool = True)¶
Completer which wraps around several other completers, and calls any the
one that corresponds with the first word of the input.
By combining multiple NestedCompleter instances, we can achieve multiple
hierarchical levels of autocompletion. This is useful when WordCompleter
is not sufficient.
If you need multiple levels, check out the from_nested_dict classmethod.
classmethod from_nested_dict(data: Mapping[str, Any | Set[str] | None | Completer]) → NestedCompleter¶
Create a NestedCompleter, starting from a nested dictionary data
structure, like this:
data = {
'show': {
'version': None,
'interfaces': None,
'clock': None,
'ip': {'interface': {'brief'}}
},
'exit': None
'enable': None
}
The value should be None if there is no further completion at some
point. If all values in the dictionary are None, it is also possible to
use a set instead.
Values in this data structure can be a completers as well.
class prompt_toolkit.completion.PathCompleter(only_directories: bool = False, get_paths: Callable[[], list[str]] | None = None, file_filter: Callable[[str], bool] | None = None, min_input_len: int = 0, expanduser: bool = False)¶
Complete for Path variables.
Parameters:
get_paths – Callable which returns a list of directories to look into
when the user enters a relative path.
file_filter – Callable which takes a filename and returns whether
this file should show up in the completion. None
when no filtering has to be done.
min_input_len – Don’t do autocompletion when the input string is shorter.
class prompt_toolkit.completion.ThreadedCompleter(completer: Completer)¶
Wrapper that runs the get_completions generator in a thread.
(Use this to prevent the user interface from becoming unresponsive if the
generation of completions takes too much time.)
The completions will be displayed as soon as they are produced. The user
can already select a completion, even if not all completions are displayed.
async get_completions_async(document: Document, complete_event: CompleteEvent) → AsyncGenerator[Completion, None]¶
Asynchronous generator of completions.
class prompt_toolkit.completion.WordCompleter(words: Sequence[str] | Callable[[], Sequence[str]], ignore_case: bool = False, display_dict: Mapping[str, AnyFormattedText] | None = None, meta_dict: Mapping[str, AnyFormattedText] | None = None, WORD: bool = False, sentence: bool = False, match_middle: bool = False, pattern: Pattern[str] | None = None)¶
Simple autocompletion on a list of words.
Parameters:
words – List of words or callable that returns a list of words.
ignore_case – If True, case-insensitive completion.
meta_dict – Optional dict mapping words to their meta-text. (This
should map strings to strings or formatted text.)
WORD – When True, use WORD characters.
sentence – When True, don’t complete by comparing the word before the
cursor, but by comparing all the text before the cursor. In this case,
the list of words is just a list of strings, where each string can
contain spaces. (Can not be used together with the WORD option.)
match_middle – When True, match not only the start, but also in the
middle of the word.
pattern – Optional compiled regex for finding the word before
the cursor to complete. When given, use this regex pattern instead of
default one (see document._FIND_WORD_RE)
prompt_toolkit.completion.get_common_complete_suffix(document: Document, completions: Sequence[Completion]) → str¶
Return the common prefix for all completions.
prompt_toolkit.completion.merge_completers(completers: Sequence[Completer], deduplicate: bool = False) → Completer¶
Combine several completers into one.
Parameters:
deduplicate – If True, wrap the result in a DeduplicateCompleter
so that completions that would result in the same text will be
deduplicated.
Document¶
The Document that implements all the text operations/querying.
class prompt_toolkit.document.Document(text: str = '', cursor_position: int | None = None, selection: SelectionState | None = None)¶
This is a immutable class around the text and cursor position, and contains
methods for querying this data, e.g. to give the text before the cursor.
This class is usually instantiated by a Buffer
object, and accessed as the document property of that class.
Parameters:
text – string
cursor_position – int
selection – SelectionState
property char_before_cursor: str¶
Return character before the cursor or an empty string.
property current_char: str¶
Return character under cursor or an empty string.
property current_line: str¶
Return the text on the line where the cursor is. (when the input
consists of just one line, it equals text.
property current_line_after_cursor: str¶
Text from the cursor until the end of the line.
property current_line_before_cursor: str¶
Text from the start of the line until the cursor.
property cursor_position: int¶
The document cursor position.
property cursor_position_col: int¶
Current column. (0-based.)
property cursor_position_row: int¶
Current row. (0-based.)
cut_selection() → tuple[Document, ClipboardData]¶
Return a (Document, ClipboardData) tuple, where the
document represents the new document when the selection is cut, and the
clipboard data, represents whatever has to be put on the clipboard.
empty_line_count_at_the_end() → int¶
Return number of empty lines at the end of the document.
end_of_paragraph(count: int = 1, after: bool = False) → int¶
Return the end of the current paragraph. (Relative cursor position.)
find(sub: str, in_current_line: bool = False, include_current_position: bool = False, ignore_case: bool = False, count: int = 1) → int | None¶
Find text after the cursor, return position relative to the cursor
position. Return None if nothing was found.
Parameters:
count – Find the n-th occurrence.
find_all(sub: str, ignore_case: bool = False) → list[int]¶
Find all occurrences of the substring. Return a list of absolute
positions in the document.
find_backwards(sub: str, in_current_line: bool = False, ignore_case: bool = False, count: int = 1) → int | None¶
Find text before the cursor, return position relative to the cursor
position. Return None if nothing was found.
Parameters:
count – Find the n-th occurrence.
find_boundaries_of_current_word(WORD: bool = False, include_leading_whitespace: bool = False, include_trailing_whitespace: bool = False) → tuple[int, int]¶
Return the relative boundaries (startpos, endpos) of the current word under the
cursor. (This is at the current line, because line boundaries obviously
don’t belong to any word.)
If not on a word, this returns (0,0)
find_enclosing_bracket_left(left_ch: str, right_ch: str, start_pos: int | None = None) → int | None¶
Find the left bracket enclosing current position. Return the relative
position to the cursor position.
When start_pos is given, don’t look past the position.
find_enclosing_bracket_right(left_ch: str, right_ch: str, end_pos: int | None = None) → int | None¶
Find the right bracket enclosing current position. Return the relative
position to the cursor position.
When end_pos is given, don’t look past the position.
find_matching_bracket_position(start_pos: int | None = None, end_pos: int | None = None) → int¶
Return relative cursor position of matching [, (, { or < bracket.
When start_pos or end_pos are given. Don’t look past the positions.
find_next_matching_line(match_func: Callable[[str], bool], count: int = 1) → int | None¶
Look downwards for empty lines.
Return the line index, relative to the current line.
find_next_word_beginning(count: int = 1, WORD: bool = False) → int | None¶
Return an index relative to the cursor position pointing to the start
of the next word. Return None if nothing was found.
find_next_word_ending(include_current_position: bool = False, count: int = 1, WORD: bool = False) → int | None¶
Return an index relative to the cursor position pointing to the end
of the next word. Return None if nothing was found.
find_previous_matching_line(match_func: Callable[[str], bool], count: int = 1) → int | None¶
Look upwards for empty lines.
Return the line index, relative to the current line.
find_previous_word_beginning(count: int = 1, WORD: bool = False) → int | None¶
Return an index relative to the cursor position pointing to the start
of the previous word. Return None if nothing was found.
find_previous_word_ending(count: int = 1, WORD: bool = False) → int | None¶
Return an index relative to the cursor position pointing to the end
of the previous word. Return None if nothing was found.
find_start_of_previous_word(count: int = 1, WORD: bool = False, pattern: Pattern[str] | None = None) → int | None¶
Return an index relative to the cursor position pointing to the start
of the previous word. Return None if nothing was found.
Parameters:
pattern – (None or compiled regex). When given, use this regex
pattern.
get_column_cursor_position(column: int) → int¶
Return the relative cursor position for this column at the current
line. (It will stay between the boundaries of the line in case of a
larger number.)
get_cursor_down_position(count: int = 1, preferred_column: int | None = None) → int¶
Return the relative cursor position (character index) where we would be if the
user pressed the arrow-down button.
Parameters:
preferred_column – When given, go to this column instead of
staying at the current column.
get_cursor_left_position(count: int = 1) → int¶
Relative position for cursor left.
get_cursor_right_position(count: int = 1) → int¶
Relative position for cursor_right.
get_cursor_up_position(count: int = 1, preferred_column: int | None = None) → int¶
Return the relative cursor position (character index) where we would be if the
user pressed the arrow-up button.
Parameters:
preferred_column – When given, go to this column instead of
staying at the current column.
get_end_of_document_position() → int¶
Relative position for the end of the document.
get_end_of_line_position() → int¶
Relative position for the end of this line.
get_start_of_document_position() → int¶
Relative position for the start of the document.
get_start_of_line_position(after_whitespace: bool = False) → int¶
Relative position for the start of this line.
get_word_before_cursor(WORD: bool = False, pattern: Pattern[str] | None = None) → str¶
Give the word before the cursor.
If we have whitespace before the cursor this returns an empty string.
Parameters:
pattern – (None or compiled regex). When given, use this regex
pattern.
get_word_under_cursor(WORD: bool = False) → str¶
Return the word, currently below the cursor.
This returns an empty string when the cursor is on a whitespace region.
has_match_at_current_position(sub: str) → bool¶
True when this substring is found at the cursor position.
insert_after(text: str) → Document¶
Create a new document, with this text inserted after the buffer.
It keeps selection ranges and cursor position in sync.
insert_before(text: str) → Document¶
Create a new document, with this text inserted before the buffer.
It keeps selection ranges and cursor position in sync.
property is_cursor_at_the_end: bool¶
True when the cursor is at the end of the text.
property is_cursor_at_the_end_of_line: bool¶
True when the cursor is at the end of this line.
last_non_blank_of_current_line_position() → int¶
Relative position for the last non blank character of this line.
property leading_whitespace_in_current_line: str¶
The leading whitespace in the left margin of the current line.
property line_count: int¶
Return the number of lines in this document. If the document ends
with a trailing n, that counts as the beginning of a new line.
property lines: list[str]¶
Array of all the lines.
property lines_from_current: list[str]¶
Array of the lines starting from the current line, until the last line.
property on_first_line: bool¶
True when we are at the first line.
property on_last_line: bool¶
True when we are at the last line.
paste_clipboard_data(data: ClipboardData, paste_mode: PasteMode = PasteMode.EMACS, count: int = 1) → Document¶
Return a new Document instance which contains the result if
we would paste this data at the current cursor position.
Parameters:
paste_mode – Where to paste. (Before/after/emacs.)
count – When >1, Paste multiple times.
property selection: SelectionState | None¶
SelectionState object.
selection_range() → tuple[int, int]¶
Return (from, to) tuple of the selection.
start and end position are included.
This doesn’t take the selection type into account. Use
selection_ranges instead.
selection_range_at_line(row: int) → tuple[int, int] | None¶
If the selection spans a portion of the given line, return a (from, to) tuple.
The returned upper boundary is not included in the selection, so
(0, 0) is an empty selection.  (0, 1), is a one character selection.
Returns None if the selection doesn’t cover this line at all.
selection_ranges() → Iterable[tuple[int, int]]¶
Return a list of (from, to) tuples for the selection or none if
nothing was selected. The upper boundary is not included.
This will yield several (from, to) tuples in case of a BLOCK selection.
This will return zero ranges, like (8,8) for empty lines in a block
selection.
start_of_paragraph(count: int = 1, before: bool = False) → int¶
Return the start of the current paragraph. (Relative cursor position.)
property text: str¶
The document text.
translate_index_to_position(index: int) → tuple[int, int]¶
Given an index for the text, return the corresponding (row, col) tuple.
(0-based. Returns (0, 0) for index=0.)
translate_row_col_to_index(row: int, col: int) → int¶
Given a (row, col) tuple, return the corresponding index.
(Row and col params are 0-based.)
Negative row/col values are turned into zero.
Enums¶
prompt_toolkit.enums.DEFAULT_BUFFER = 'DEFAULT_BUFFER'¶
Name of the default buffer.
prompt_toolkit.enums.SEARCH_BUFFER = 'SEARCH_BUFFER'¶
Name of the search buffer.
prompt_toolkit.enums.SYSTEM_BUFFER = 'SYSTEM_BUFFER'¶
Name of the system buffer.
History¶
Implementations for the history of a Buffer.
NOTE: There is no DynamicHistory:
This doesn’t work well, because the Buffer needs to be able to attach
an event handler to the event when a history entry is loaded. This
loading can be done asynchronously and making the history swappable would
probably break this.
class prompt_toolkit.history.DummyHistory¶
History object that doesn’t remember anything.
class prompt_toolkit.history.FileHistory(filename: str | bytes | PathLike[str] | PathLike[bytes])¶
History class that stores all strings in a file.
class prompt_toolkit.history.History¶
Base History class.
This also includes abstract methods for loading/storing history.
append_string(string: str) → None¶
Add string to the history.
get_strings() → list[str]¶
Get the strings from the history that are loaded so far.
(In order. Oldest item first.)
async load() → AsyncGenerator[str, None]¶
Load the history and yield all the entries in reverse order (latest,
most recent history entry first).
This method can be called multiple times from the Buffer to
repopulate the history when prompting for a new input. So we are
responsible here for both caching, and making sure that strings that
were were appended to the history will be incorporated next time this
method is called.
abstractmethod load_history_strings() → Iterable[str]¶
This should be a generator that yields str instances.
It should yield the most recent items first, because they are the most
important. (The history can already be used, even when it’s only
partially loaded.)
abstractmethod store_string(string: str) → None¶
Store the string in persistent storage.
class prompt_toolkit.history.InMemoryHistory(history_strings: Sequence[str] | None = None)¶
History class that keeps a list of all strings in memory.
In order to prepopulate the history, it’s possible to call either
append_string for all items or pass a list of strings to __init__ here.
class prompt_toolkit.history.ThreadedHistory(history: History)¶
Wrapper around History implementations that run the load() generator in
a thread.
Use this to increase the start-up time of prompt_toolkit applications.
History entries are available as soon as they are loaded. We don’t have to
wait for everything to be loaded.
async load() → AsyncGenerator[str, None]¶
Like History.load(), but call `self.load_history_strings() in a
background thread.
Keys¶
class prompt_toolkit.keys.Keys(value)¶
List of keys for use in key bindings.
Note that this is an “StrEnum”, all values can be compared against
strings.
Style¶
Styling for prompt_toolkit applications.
class prompt_toolkit.styles.AdjustBrightnessStyleTransformation(min_brightness: Callable[[], float] | float = 0.0, max_brightness: Callable[[], float] | float = 1.0)¶
Adjust the brightness to improve the rendering on either dark or light
backgrounds.
For dark backgrounds, it’s best to increase min_brightness. For light
backgrounds it’s best to decrease max_brightness. Usually, only one
setting is adjusted.
This will only change the brightness for text that has a foreground color
defined, but no background color. It works best for 256 or true color
output.
Note
Notice that there is no universal way to detect whether the
application is running in a light or dark terminal. As a
developer of an command line application, you’ll have to make
this configurable for the user.
Parameters:
min_brightness – Float between 0.0 and 1.0 or a callable that returns
a float.
max_brightness – Float between 0.0 and 1.0 or a callable that returns
a float.
class prompt_toolkit.styles.Attrs(color, bgcolor, bold, underline, strike, italic, blink, reverse, hidden, dim)¶
bgcolor: str | None¶
Alias for field number 1
blink: bool | None¶
Alias for field number 6
bold: bool | None¶
Alias for field number 2
color: str | None¶
Alias for field number 0
dim: bool | None¶
Alias for field number 9
hidden: bool | None¶
Alias for field number 8
italic: bool | None¶
Alias for field number 5
reverse: bool | None¶
Alias for field number 7
strike: bool | None¶
Alias for field number 4
underline: bool | None¶
Alias for field number 3
class prompt_toolkit.styles.BaseStyle¶
Abstract base class for prompt_toolkit styles.
abstractmethod get_attrs_for_style_str(style_str: str, default: Attrs = ('', '', False, False, False, False, False, False, False, False)) → Attrs¶
Return Attrs for the given style string.
Parameters:
style_str – The style string. This can contain inline styling as
well as classnames (e.g. “class:title”).
default – Attrs to be used if no styling was defined.
abstractmethod invalidation_hash() → Hashable¶
Invalidation hash for the style. When this changes over time, the
renderer knows that something in the style changed, and that everything
has to be redrawn.
abstract property style_rules: list[tuple[str, str]]¶
The list of style rules, used to create this style.
(Required for DynamicStyle and _MergedStyle to work.)
class prompt_toolkit.styles.ConditionalStyleTransformation(style_transformation: StyleTransformation, filter: Filter | bool)¶
Apply the style transformation depending on a condition.
class prompt_toolkit.styles.DummyStyle¶
A style that doesn’t style anything.
class prompt_toolkit.styles.DummyStyleTransformation¶
Don’t transform anything at all.
class prompt_toolkit.styles.DynamicStyle(get_style: Callable[[], BaseStyle | None])¶
Style class that can dynamically returns an other Style.
Parameters:
get_style – Callable that returns a Style instance.
class prompt_toolkit.styles.DynamicStyleTransformation(get_style_transformation: Callable[[], StyleTransformation | None])¶
StyleTransformation class that can dynamically returns any
StyleTransformation.
Parameters:
get_style_transformation – Callable that returns a
StyleTransformation instance.
class prompt_toolkit.styles.Priority(value)¶
The priority of the rules, when a style is created from a dictionary.
In a Style, rules that are defined later will always override previous
defined rules, however in a dictionary, the key order was arbitrary before
Python 3.6. This means that the style could change at random between rules.
We have two options:
DICT_KEY_ORDER: This means, iterate through the dictionary, and take
the key/value pairs in order as they come. This is a good option if you
have Python >3.6. Rules at the end will override rules at the beginning.
MOST_PRECISE: keys that are defined with most precision will get higher
priority. (More precise means: more elements.)
class prompt_toolkit.styles.Style(style_rules: list[tuple[str, str]])¶
Create a Style instance from a list of style rules.
The style_rules is supposed to be a list of (‘classnames’, ‘style’) tuples.
The classnames are a whitespace separated string of class names and the
style string is just like a Pygments style definition, but with a few
additions: it supports ‘reverse’ and ‘blink’.
Later rules always override previous rules.
Usage:
Style([
('title', '#ff0000 bold underline'),
('something-else', 'reverse'),
('class1 class2', 'reverse'),
])
The from_dict classmethod is similar, but takes a dictionary as input.
classmethod from_dict(style_dict: dict[str, str], priority: Priority = Priority.DICT_KEY_ORDER) → Style¶
Parameters:
style_dict – Style dictionary.
priority – Priority value.
get_attrs_for_style_str(style_str: str, default: Attrs = ('', '', False, False, False, False, False, False, False, False)) → Attrs¶
Get Attrs for the given style string.
class prompt_toolkit.styles.StyleTransformation¶
Base class for any style transformation.
invalidation_hash() → Hashable¶
When this changes, the cache should be invalidated.
abstractmethod transform_attrs(attrs: Attrs) → Attrs¶
Take an Attrs object and return a new Attrs object.
Remember that the color formats can be either “ansi…” or a 6 digit
lowercase hexadecimal color (without ‘#’ prefix).
class prompt_toolkit.styles.SwapLightAndDarkStyleTransformation¶
Turn dark colors into light colors and the other way around.
This is meant to make color schemes that work on a dark background usable
on a light background (and the other way around).
Notice that this doesn’t swap foreground and background like “reverse”
does. It turns light green into dark green and the other way around.
Foreground and background colors are considered individually.
Also notice that when <reverse> is used somewhere and no colors are given
in particular (like what is the default for the bottom toolbar), then this
doesn’t change anything. This is what makes sense, because when the
‘default’ color is chosen, it’s what works best for the terminal, and
reverse works good with that.
transform_attrs(attrs: Attrs) → Attrs¶
Return the Attrs used when opposite luminosity should be used.
prompt_toolkit.styles.merge_style_transformations(style_transformations: Sequence[StyleTransformation]) → StyleTransformation¶
Merge multiple transformations together.
prompt_toolkit.styles.merge_styles(styles: list[BaseStyle]) → _MergedStyle¶
Merge multiple Style objects.
prompt_toolkit.styles.pygments_token_to_classname(token: Token) → str¶
Turn e.g. Token.Name.Exception into ‘pygments.name.exception’.
(Our Pygments lexer will also turn the tokens that pygments produces in a
prompt_toolkit list of fragments that match these styling rules.)
prompt_toolkit.styles.style_from_pygments_cls(pygments_style_cls: type[PygmentsStyle]) → Style¶
Shortcut to create a Style instance from a Pygments style class
and a style dictionary.
Example:
from prompt_toolkit.styles.from_pygments import style_from_pygments_cls
from pygments.styles import get_style_by_name
style = style_from_pygments_cls(get_style_by_name('monokai'))
Parameters:
pygments_style_cls – Pygments style class to start from.
prompt_toolkit.styles.style_from_pygments_dict(pygments_dict: dict[Token, str]) → Style¶
Create a Style instance from a Pygments style dictionary.
(One that maps Token objects to style strings.)
Shortcuts¶
class prompt_toolkit.shortcuts.CompleteStyle(value)¶
How to display autocompletions for the prompt.
class prompt_toolkit.shortcuts.ProgressBar(title: AnyFormattedText = None, formatters: Sequence[Formatter] | None = None, bottom_toolbar: AnyFormattedText = None, style: BaseStyle | None = None, key_bindings: KeyBindings | None = None, cancel_callback: Callable[[], None] | None = None, file: TextIO | None = None, color_depth: ColorDepth | None = None, output: Output | None = None, input: Input | None = None)¶
Progress bar context manager.
Usage
with ProgressBar(...) as pb:
for item in pb(data):
...
Parameters:
title – Text to be displayed above the progress bars. This can be a
callable or formatted text as well.
formatters – List of Formatter instances.
bottom_toolbar – Text to be displayed in the bottom toolbar. This
can be a callable or formatted text.
style – prompt_toolkit.styles.BaseStyle instance.
key_bindings – KeyBindings instance.
cancel_callback – Callback function that’s called when control-c is
pressed by the user. This can be used for instance to start “proper”
cancellation if the wrapped code supports it.
file – The file object used for rendering, by default sys.stderr is used.
color_depth – prompt_toolkit ColorDepth instance.
output – Output instance.
input – Input instance.
class prompt_toolkit.shortcuts.PromptSession(message: AnyFormattedText = '', *, multiline: FilterOrBool = False, wrap_lines: FilterOrBool = True, is_password: FilterOrBool = False, vi_mode: bool = False, editing_mode: EditingMode = EditingMode.EMACS, complete_while_typing: FilterOrBool = True, validate_while_typing: FilterOrBool = True, enable_history_search: FilterOrBool = False, search_ignore_case: FilterOrBool = False, lexer: Lexer | None = None, enable_system_prompt: FilterOrBool = False, enable_suspend: FilterOrBool = False, enable_open_in_editor: FilterOrBool = False, validator: Validator | None = None, completer: Completer | None = None, complete_in_thread: bool = False, reserve_space_for_menu: int = 8, complete_style: CompleteStyle = CompleteStyle.COLUMN, auto_suggest: AutoSuggest | None = None, style: BaseStyle | None = None, style_transformation: StyleTransformation | None = None, swap_light_and_dark_colors: FilterOrBool = False, color_depth: ColorDepth | None = None, cursor: AnyCursorShapeConfig = None, include_default_pygments_style: FilterOrBool = True, history: History | None = None, clipboard: Clipboard | None = None, prompt_continuation: PromptContinuationText | None = None, rprompt: AnyFormattedText = None, bottom_toolbar: AnyFormattedText = None, mouse_support: FilterOrBool = False, input_processors: list[Processor] | None = None, placeholder: AnyFormattedText | None = None, key_bindings: KeyBindingsBase | None = None, erase_when_done: bool = False, tempfile_suffix: str | Callable[[], str] | None = '.txt', tempfile: str | Callable[[], str] | None = None, refresh_interval: float = 0, show_frame: FilterOrBool = False, input: Input | None = None, output: Output | None = None, interrupt_exception: type[BaseException] = <class 'KeyboardInterrupt'>, eof_exception: type[BaseException] = <class 'EOFError'>)¶
PromptSession for a prompt application, which can be used as a GNU Readline
replacement.
This is a wrapper around a lot of prompt_toolkit functionality and can
be a replacement for raw_input.
All parameters that expect “formatted text” can take either just plain text
(a unicode object), a list of (style_str, text) tuples or an HTML object.
Example usage:
s = PromptSession(message='>')
text = s.prompt()
Parameters:
message – Plain text or formatted text to be shown before the prompt.
This can also be a callable that returns formatted text.
multiline – bool or Filter.
When True, prefer a layout that is more adapted for multiline input.
Text after newlines is automatically indented, and search/arg input is
shown below the input, instead of replacing the prompt.
wrap_lines – bool or Filter.
When True (the default), automatically wrap long lines instead of
scrolling horizontally.
is_password – Show asterisks instead of the actual typed characters.
editing_mode – EditingMode.VI or EditingMode.EMACS.
vi_mode – bool, if True, Identical to editing_mode=EditingMode.VI.
complete_while_typing – bool or
Filter. Enable autocompletion while
typing.
validate_while_typing – bool or
Filter. Enable input validation while
typing.
enable_history_search – bool or
Filter. Enable up-arrow parting
string matching.
search_ignore_case – Filter. Search case insensitive.
lexer – Lexer to be used for the
syntax highlighting.
validator – Validator instance
for input validation.
completer – Completer instance
for input completion.
complete_in_thread – bool or
Filter. Run the completer code in a
background thread in order to avoid blocking the user interface.
For CompleteStyle.READLINE_LIKE, this setting has no effect. There
we always run the completions in the main thread.
reserve_space_for_menu – Space to be reserved for displaying the menu.
(0 means that no space needs to be reserved.)
auto_suggest – AutoSuggest
instance for input suggestions.
style – Style instance for the color scheme.
include_default_pygments_style – bool or
Filter. Tell whether the default
styling for Pygments lexers has to be included. By default, this is
true, but it is recommended to be disabled if another Pygments style is
passed as the style argument, otherwise, two Pygments styles will be
merged.
style_transformation – StyleTransformation instance.
swap_light_and_dark_colors – bool or
Filter. When enabled, apply
SwapLightAndDarkStyleTransformation.
This is useful for switching between dark and light terminal
backgrounds.
enable_system_prompt – bool or
Filter. Pressing Meta+’!’ will show
a system prompt.
enable_suspend – bool or Filter.
Enable Control-Z style suspension.
enable_open_in_editor – bool or
Filter. Pressing ‘v’ in Vi mode or
C-X C-E in emacs mode will open an external editor.
history – History instance.
clipboard – Clipboard instance.
(e.g. InMemoryClipboard)
rprompt – Text or formatted text to be displayed on the right side.
This can also be a callable that returns (formatted) text.
bottom_toolbar – Formatted text or callable that returns formatted
text to be displayed at the bottom of the screen.
prompt_continuation – Text that needs to be displayed for a multiline
prompt continuation. This can either be formatted text or a callable
that takes a prompt_width, line_number and wrap_count as input
and returns formatted text. When this is None (the default), then
prompt_width spaces will be used.
complete_style – CompleteStyle.COLUMN,
CompleteStyle.MULTI_COLUMN or CompleteStyle.READLINE_LIKE.
mouse_support – bool or Filter
to enable mouse support.
placeholder – Text to be displayed when no input has been given
yet. Unlike the default parameter, this won’t be returned as part of
the output ever. This can be formatted text or a callable that returns
formatted text.
show_frame – bool or
Filter. When True, surround the input
with a frame.
refresh_interval – (number; in seconds) When given, refresh the UI
every so many seconds.
input – Input object. (Note that the preferred way to change the
input/output is by creating an AppSession.)
output – Output object.
interrupt_exception – The exception type that will be raised when
there is a keyboard interrupt (control-c keypress).
eof_exception – The exception type that will be raised when there is
an end-of-file/exit event (control-d keypress).
prompt(message: AnyFormattedText | None = None, *, editing_mode: EditingMode | None = None, refresh_interval: float | None = None, vi_mode: bool | None = None, lexer: Lexer | None = None, completer: Completer | None = None, complete_in_thread: bool | None = None, is_password: bool | None = None, key_bindings: KeyBindingsBase | None = None, bottom_toolbar: AnyFormattedText | None = None, style: BaseStyle | None = None, color_depth: ColorDepth | None = None, cursor: AnyCursorShapeConfig | None = None, include_default_pygments_style: FilterOrBool | None = None, style_transformation: StyleTransformation | None = None, swap_light_and_dark_colors: FilterOrBool | None = None, rprompt: AnyFormattedText | None = None, multiline: FilterOrBool | None = None, prompt_continuation: PromptContinuationText | None = None, wrap_lines: FilterOrBool | None = None, enable_history_search: FilterOrBool | None = None, search_ignore_case: FilterOrBool | None = None, complete_while_typing: FilterOrBool | None = None, validate_while_typing: FilterOrBool | None = None, complete_style: CompleteStyle | None = None, auto_suggest: AutoSuggest | None = None, validator: Validator | None = None, clipboard: Clipboard | None = None, mouse_support: FilterOrBool | None = None, input_processors: list[Processor] | None = None, placeholder: AnyFormattedText | None = None, reserve_space_for_menu: int | None = None, enable_system_prompt: FilterOrBool | None = None, enable_suspend: FilterOrBool | None = None, enable_open_in_editor: FilterOrBool | None = None, tempfile_suffix: str | Callable[[], str] | None = None, tempfile: str | Callable[[], str] | None = None, show_frame: FilterOrBool | None = None, default: str | Document = '', accept_default: bool = False, pre_run: Callable[[], None] | None = None, set_exception_handler: bool = True, handle_sigint: bool = True, in_thread: bool = False, inputhook: InputHook | None = None) → _T¶
Display the prompt.
The first set of arguments is a subset of the PromptSession
class itself. For these, passing in None will keep the current
values that are active in the session. Passing in a value will set the
attribute for the session, which means that it applies to the current,
but also to the next prompts.
Note that in order to erase a Completer, Validator or
AutoSuggest, you can’t use None. Instead pass in a
DummyCompleter, DummyValidator or DummyAutoSuggest instance
respectively. For a Lexer you can pass in an empty SimpleLexer.
Additional arguments, specific for this prompt:
Parameters:
default – The default input text to be shown. (This can be edited
by the user).
accept_default – When True, automatically accept the default
value without allowing the user to edit the input.
pre_run – Callable, called at the start of Application.run.
in_thread – Run the prompt in a background thread; block the
current thread. This avoids interference with an event loop in the
current thread. Like Application.run(in_thread=True).
This method will raise KeyboardInterrupt when control-c has been
pressed (for abort) and EOFError when control-d has been pressed
(for exit).
prompt_toolkit.shortcuts.button_dialog(title: AnyFormattedText = '', text: AnyFormattedText = '', buttons: list[tuple[str, _T]] = [], style: BaseStyle | None = None) → Application[_T]¶
Display a dialog with button choices (given as a list of tuples).
Return the value associated with button.
prompt_toolkit.shortcuts.choice(message: AnyFormattedText, *, options: Sequence[tuple[_T, AnyFormattedText]], default: _T | None = None, mouse_support: bool = False, style: BaseStyle | None = None, symbol: str = '>', bottom_toolbar: AnyFormattedText = None, show_frame: bool = False, enable_suspend: FilterOrBool = False, enable_interrupt: FilterOrBool = True, interrupt_exception: type[BaseException] = <class 'KeyboardInterrupt'>, key_bindings: KeyBindingsBase | None = None) → _T¶
Choice selection prompt. Ask the user to choose among a set of options.
Example usage:
result = choice(
message="Please select a dish:",
options=[
("pizza", "Pizza with mushrooms"),
("salad", "Salad with tomatoes"),
("sushi", "Sushi"),
],
default="pizza",
)
Parameters:
message – Plain text or formatted text to be shown before the options.
options – Sequence of (value, label) tuples. The labels can be
formatted text.
default – Default value. If none is given, the first option is
considered the default.
mouse_support – Enable mouse support.
style – Style instance for the color scheme.
symbol – Symbol to be displayed in front of the selected choice.
bottom_toolbar – Formatted text or callable that returns formatted
text to be displayed at the bottom of the screen.
show_frame – bool or
Filter. When True, surround the input
with a frame.
enable_interrupt – bool or
Filter. When True, raise
the interrupt_exception (KeyboardInterrupt by default) when
control-c has been pressed.
interrupt_exception – The exception type that will be raised when
there is a keyboard interrupt (control-c keypress).
prompt_toolkit.shortcuts.clear() → None¶
Clear the screen.
prompt_toolkit.shortcuts.clear_title() → None¶
Erase the current title.
prompt_toolkit.shortcuts.confirm(message: AnyFormattedText = 'Confirm?', suffix: str = ' (y/n) ') → bool¶
Display a confirmation prompt that returns True/False.
prompt_toolkit.shortcuts.create_confirm_session(message: AnyFormattedText, suffix: str = ' (y/n) ') → PromptSession[bool]¶
Create a PromptSession object for the ‘confirm’ function.
prompt_toolkit.shortcuts.input_dialog(title: AnyFormattedText = '', text: AnyFormattedText = '', ok_text: str = 'OK', cancel_text: str = 'Cancel', completer: Completer | None = None, validator: Validator | None = None, password: FilterOrBool = False, style: BaseStyle | None = None, default: str = '') → Application[str]¶
Display a text input box.
Return the given text, or None when cancelled.
prompt_toolkit.shortcuts.message_dialog(title: AnyFormattedText = '', text: AnyFormattedText = '', ok_text: str = 'Ok', style: BaseStyle | None = None) → Application[None]¶
Display a simple message box and wait until the user presses enter.
prompt_toolkit.shortcuts.print_formatted_text(*values: Any, sep: str = ' ', end: str = '\n', file: TextIO | None = None, flush: bool = False, style: BaseStyle | None = None, output: Output | None = None, color_depth: ColorDepth | None = None, style_transformation: StyleTransformation | None = None, include_default_pygments_style: bool = True) → None¶
print_formatted_text(*values, sep=' ', end='\n', file=None, flush=False, style=None, output=None)
Print text to stdout. This is supposed to be compatible with Python’s print
function, but supports printing of formatted text. You can pass a
FormattedText,
HTML or
ANSI object to print formatted
text.
Print HTML as follows:
print_formatted_text(HTML('<i>Some italic text</i> <ansired>This is red!</ansired>'))
style = Style.from_dict({
'hello': '#ff0066',
'world': '#884444 italic',
})
print_formatted_text(HTML('<hello>Hello</hello> <world>world</world>!'), style=style)
Print a list of (style_str, text) tuples in the given style to the
output.  E.g.:
style = Style.from_dict({
'hello': '#ff0066',
'world': '#884444 italic',
})
fragments = FormattedText([
('class:hello', 'Hello'),
('class:world', 'World'),
])
print_formatted_text(fragments, style=style)
If you want to print a list of Pygments tokens, wrap it in
PygmentsTokens to do the
conversion.
If a prompt_toolkit Application is currently running, this will always
print above the application or prompt (similar to patch_stdout). So,
print_formatted_text will erase the current application, print the text,
and render the application again.
Parameters:
values – Any kind of printable object, or formatted string.
sep – String inserted between values, default a space.
end – String appended after the last value, default a newline.
style – Style instance for the color scheme.
include_default_pygments_style – bool. Include the default Pygments
style when set to True (the default).
prompt_toolkit.shortcuts.progress_dialog(title: AnyFormattedText = '', text: AnyFormattedText = '', run_callback: Callable[[Callable[[int], None], Callable[[str], None]], None] = <function <lambda>>, style: BaseStyle | None = None) → Application[None]¶
Parameters:
run_callback – A function that receives as input a set_percentage
function and it does the work.
prompt_toolkit.shortcuts.prompt(message: AnyFormattedText | None = None, *, history: History | None = None, editing_mode: EditingMode | None = None, refresh_interval: float | None = None, vi_mode: bool | None = None, lexer: Lexer | None = None, completer: Completer | None = None, complete_in_thread: bool | None = None, is_password: bool | None = None, key_bindings: KeyBindingsBase | None = None, bottom_toolbar: AnyFormattedText | None = None, style: BaseStyle | None = None, color_depth: ColorDepth | None = None, cursor: AnyCursorShapeConfig = None, include_default_pygments_style: FilterOrBool | None = None, style_transformation: StyleTransformation | None = None, swap_light_and_dark_colors: FilterOrBool | None = None, rprompt: AnyFormattedText | None = None, multiline: FilterOrBool | None = None, prompt_continuation: PromptContinuationText | None = None, wrap_lines: FilterOrBool | None = None, enable_history_search: FilterOrBool | None = None, search_ignore_case: FilterOrBool | None = None, complete_while_typing: FilterOrBool | None = None, validate_while_typing: FilterOrBool | None = None, complete_style: CompleteStyle | None = None, auto_suggest: AutoSuggest | None = None, validator: Validator | None = None, clipboard: Clipboard | None = None, mouse_support: FilterOrBool | None = None, input_processors: list[Processor] | None = None, placeholder: AnyFormattedText | None = None, reserve_space_for_menu: int | None = None, enable_system_prompt: FilterOrBool | None = None, enable_suspend: FilterOrBool | None = None, enable_open_in_editor: FilterOrBool | None = None, tempfile_suffix: str | Callable[[], str] | None = None, tempfile: str | Callable[[], str] | None = None, show_frame: FilterOrBool | None = None, default: str = '', accept_default: bool = False, pre_run: Callable[[], None] | None = None, set_exception_handler: bool = True, handle_sigint: bool = True, in_thread: bool = False, inputhook: InputHook | None = None) → str¶
Display the prompt.
The first set of arguments is a subset of the PromptSession
class itself. For these, passing in None will keep the current
values that are active in the session. Passing in a value will set the
attribute for the session, which means that it applies to the current,
but also to the next prompts.
Note that in order to erase a Completer, Validator or
AutoSuggest, you can’t use None. Instead pass in a
DummyCompleter, DummyValidator or DummyAutoSuggest instance
respectively. For a Lexer you can pass in an empty SimpleLexer.
Additional arguments, specific for this prompt:
Parameters:
default – The default input text to be shown. (This can be edited
by the user).
accept_default – When True, automatically accept the default
value without allowing the user to edit the input.
pre_run – Callable, called at the start of Application.run.
in_thread – Run the prompt in a background thread; block the
current thread. This avoids interference with an event loop in the
current thread. Like Application.run(in_thread=True).
This method will raise KeyboardInterrupt when control-c has been
pressed (for abort) and EOFError when control-d has been pressed
(for exit).
prompt_toolkit.shortcuts.radiolist_dialog(title: AnyFormattedText = '', text: AnyFormattedText = '', ok_text: str = 'Ok', cancel_text: str = 'Cancel', values: Sequence[tuple[_T, AnyFormattedText]] | None = None, default: _T | None = None, style: BaseStyle | None = None) → Application[_T]¶
Display a simple list of element the user can choose amongst.
Only one element can be selected at a time using Arrow keys and Enter.
The focus can be moved between the list and the Ok/Cancel button with tab.
prompt_toolkit.shortcuts.set_title(text: str) → None¶
Set the terminal title.
prompt_toolkit.shortcuts.yes_no_dialog(title: AnyFormattedText = '', text: AnyFormattedText = '', yes_text: str = 'Yes', no_text: str = 'No', style: BaseStyle | None = None) → Application[bool]¶
Display a Yes/No dialog.
Return a boolean.
Formatter classes for the progress bar.
Each progress bar consists of a list of these formatters.
class prompt_toolkit.shortcuts.progress_bar.formatters.Bar(start: str = '[', end: str = ']', sym_a: str = '=', sym_b: str = '>', sym_c: str = ' ', unknown: str = '#')¶
Display the progress bar itself.
class prompt_toolkit.shortcuts.progress_bar.formatters.Formatter¶
Base class for any formatter.
class prompt_toolkit.shortcuts.progress_bar.formatters.IterationsPerSecond¶
Display the iterations per second.
class prompt_toolkit.shortcuts.progress_bar.formatters.Label(width: None | int | Dimension | Callable[[], Any] = None, suffix: str = '')¶
Display the name of the current task.
Parameters:
width – If a width is given, use this width. Scroll the text if it
doesn’t fit in this width.
suffix – String suffix to be added after the task name, e.g. ‘: ‘.
If no task name was given, no suffix will be added.
class prompt_toolkit.shortcuts.progress_bar.formatters.Percentage¶
Display the progress as a percentage.
class prompt_toolkit.shortcuts.progress_bar.formatters.Progress¶
Display the progress as text.  E.g. “8/20”
class prompt_toolkit.shortcuts.progress_bar.formatters.Rainbow(formatter: Formatter)¶
For the fun. Add rainbow colors to any of the other formatters.
class prompt_toolkit.shortcuts.progress_bar.formatters.SpinningWheel¶
Display a spinning wheel.
class prompt_toolkit.shortcuts.progress_bar.formatters.Text(text: AnyFormattedText, style: str = '')¶
Display plain text.
class prompt_toolkit.shortcuts.progress_bar.formatters.TimeElapsed¶
Display the elapsed time.
class prompt_toolkit.shortcuts.progress_bar.formatters.TimeLeft¶
Display the time left.
prompt_toolkit.shortcuts.progress_bar.formatters.create_default_formatters() → list[Formatter]¶
Return the list of default formatters.
Validation¶
Input validation for a Buffer.
(Validators will be called before accepting input.)
class prompt_toolkit.validation.ConditionalValidator(validator: Validator, filter: Filter | bool)¶
Validator that can be switched on/off according to
a filter. (This wraps around another validator.)
class prompt_toolkit.validation.DummyValidator¶
Validator class that accepts any input.
class prompt_toolkit.validation.DynamicValidator(get_validator: Callable[[], Validator | None])¶
Validator class that can dynamically returns any Validator.
Parameters:
get_validator – Callable that returns a Validator instance.
class prompt_toolkit.validation.ThreadedValidator(validator: Validator)¶
Wrapper that runs input validation in a thread.
(Use this to prevent the user interface from becoming unresponsive if the
input validation takes too much time.)
async validate_async(document: Document) → None¶
Run the validate function in a thread.
exception prompt_toolkit.validation.ValidationError(cursor_position: int = 0, message: str = '')¶
Error raised by Validator.validate().
Parameters:
cursor_position – The cursor position where the error occurred.
message – Text.
class prompt_toolkit.validation.Validator¶
Abstract base class for an input validator.
A validator is typically created in one of the following two ways:
Either by overriding this class and implementing the validate method.
Or by passing a callable to Validator.from_callable.
If the validation takes some time and needs to happen in a background
thread, this can be wrapped in a ThreadedValidator.
classmethod from_callable(validate_func: Callable[[str], bool], error_message: str = 'Invalid input', move_cursor_to_end: bool = False) → Validator¶
Create a validator from a simple validate callable. E.g.:
def is_valid(text):
return text in ['hello', 'world']
Validator.from_callable(is_valid, error_message='Invalid input')
Parameters:
validate_func – Callable that takes the input string, and returns
True if the input is valid input.
error_message – Message to be displayed if the input is invalid.
move_cursor_to_end – Move the cursor to the end of the input, if
the input is invalid.
abstractmethod validate(document: Document) → None¶
Validate the input.
If invalid, this should raise a ValidationError.
Parameters:
document – Document instance.
async validate_async(document: Document) → None¶
Return a Future which is set when the validation is ready.
This function can be overloaded in order to provide an asynchronous
implementation.
Auto suggestion¶
Fish-style  like auto-suggestion.
While a user types input in a certain buffer, suggestions are generated
(asynchronously.) Usually, they are displayed after the input. When the cursor
presses the right arrow and the cursor is at the end of the input, the
suggestion will be inserted.
If you want the auto suggestions to be asynchronous (in a background thread),
because they take too much time, and could potentially block the event loop,
then wrap the AutoSuggest instance into a
ThreadedAutoSuggest.
class prompt_toolkit.auto_suggest.AutoSuggest¶
Base class for auto suggestion implementations.
abstractmethod get_suggestion(buffer: Buffer, document: Document) → Suggestion | None¶
Return None or a Suggestion instance.
We receive both Buffer and
Document. The reason is that auto
suggestions are retrieved asynchronously. (Like completions.) The
buffer text could be changed in the meantime, but document contains
the buffer document like it was at the start of the auto suggestion
call. So, from here, don’t access buffer.text, but use
document.text instead.
Parameters:
buffer – The Buffer instance.
document – The Document instance.
async get_suggestion_async(buff: Buffer, document: Document) → Suggestion | None¶
Return a Future which is set when the suggestions are ready.
This function can be overloaded in order to provide an asynchronous
implementation.
class prompt_toolkit.auto_suggest.AutoSuggestFromHistory¶
Give suggestions based on the lines in the history.
class prompt_toolkit.auto_suggest.ConditionalAutoSuggest(auto_suggest: AutoSuggest, filter: bool | Filter)¶
Auto suggest that can be turned on and of according to a certain condition.
class prompt_toolkit.auto_suggest.DummyAutoSuggest¶
AutoSuggest class that doesn’t return any suggestion.
class prompt_toolkit.auto_suggest.DynamicAutoSuggest(get_auto_suggest: Callable[[], AutoSuggest | None])¶
Validator class that can dynamically returns any Validator.
Parameters:
get_validator – Callable that returns a Validator instance.
class prompt_toolkit.auto_suggest.Suggestion(text: str)¶
Suggestion returned by an auto-suggest algorithm.
Parameters:
text – The suggestion text.
class prompt_toolkit.auto_suggest.ThreadedAutoSuggest(auto_suggest: AutoSuggest)¶
Wrapper that runs auto suggestions in a thread.
(Use this to prevent the user interface from becoming unresponsive if the
generation of suggestions takes too much time.)
async get_suggestion_async(buff: Buffer, document: Document) → Suggestion | None¶
Run the get_suggestion function in a thread.
Renderer¶
Renders the command line on the console.
(Redraws parts of the input line that were changed.)
class prompt_toolkit.renderer.Renderer(style: BaseStyle, output: Output, full_screen: bool = False, mouse_support: Filter | bool = False, cpr_not_supported_callback: Callable[[], None] | None = None)¶
Typical usage:
output = Vt100_Output.from_pty(sys.stdout)
r = Renderer(style, output)
r.render(app, layout=...)
clear() → None¶
Clear screen and go to 0,0
erase(leave_alternate_screen: bool = True) → None¶
Hide all output and put the cursor back at the first line. This is for
instance used for running a system command (while hiding the CLI) and
later resuming the same CLI.)
Parameters:
leave_alternate_screen – When True, and when inside an alternate
screen buffer, quit the alternate screen.
property height_is_known: bool¶
True when the height from the cursor until the bottom of the terminal
is known. (It’s often nicer to draw bottom toolbars only if the height
is known, in order to avoid flickering when the CPR response arrives.)
property last_rendered_screen: Screen | None¶
The Screen class that was generated during the last rendering.
This can be None.
render(app: Application[Any], layout: Layout, is_done: bool = False) → None¶
Render the current interface to the output.
Parameters:
is_done – When True, put the cursor at the end of the interface. We
won’t print any changes to this part.
report_absolute_cursor_row(row: int) → None¶
To be called when we know the absolute cursor position.
(As an answer of a “Cursor Position Request” response.)
request_absolute_cursor_position() → None¶
Get current cursor position.
We do this to calculate the minimum available height that we can
consume for rendering the prompt. This is the available space below te
cursor.
For vt100: Do CPR request. (answer will arrive later.)
For win32: Do API call. (Answer comes immediately.)
property rows_above_layout: int¶
Return the number of rows visible in the terminal above the layout.
async wait_for_cpr_responses(timeout: int = 1) → None¶
Wait for a CPR response.
property waiting_for_cpr: bool¶
Waiting for CPR flag. True when we send the request, but didn’t got a
response.
prompt_toolkit.renderer.print_formatted_text(output: Output, formatted_text: AnyFormattedText, style: BaseStyle, style_transformation: StyleTransformation | None = None, color_depth: ColorDepth | None = None) → None¶
Print a list of (style_str, text) tuples in the given style to the output.
Lexers¶
Lexer interface and implementations.
Used for syntax highlighting.
class prompt_toolkit.lexers.DynamicLexer(get_lexer: Callable[[], Lexer | None])¶
Lexer class that can dynamically returns any Lexer.
Parameters:
get_lexer – Callable that returns a Lexer instance.
class prompt_toolkit.lexers.Lexer¶
Base class for all lexers.
invalidation_hash() → Hashable¶
When this changes, lex_document could give a different output.
(Only used for DynamicLexer.)
abstractmethod lex_document(document: Document) → Callable[[int], StyleAndTextTuples]¶
Takes a Document and returns a
callable that takes a line number and returns a list of
(style_str, text) tuples for that line.
XXX: Note that in the past, this was supposed to return a list
of (Token, text) tuples, just like a Pygments lexer.
class prompt_toolkit.lexers.PygmentsLexer(pygments_lexer_cls: type[PygmentsLexerCls], sync_from_start: FilterOrBool = True, syntax_sync: SyntaxSync | None = None)¶
Lexer that calls a pygments lexer.
Example:
from pygments.lexers.html import HtmlLexer
lexer = PygmentsLexer(HtmlLexer)
Note: Don’t forget to also load a Pygments compatible style. E.g.:
from prompt_toolkit.styles.from_pygments import style_from_pygments_cls
from pygments.styles import get_style_by_name
style = style_from_pygments_cls(get_style_by_name('monokai'))
Parameters:
pygments_lexer_cls – A Lexer from Pygments.
sync_from_start – Start lexing at the start of the document. This
will always give the best results, but it will be slow for bigger
documents. (When the last part of the document is display, then the
whole document will be lexed by Pygments on every key stroke.) It is
recommended to disable this for inputs that are expected to be more
than 1,000 lines.
syntax_sync – SyntaxSync object.
classmethod from_filename(filename: str, sync_from_start: Filter | bool = True) → Lexer¶
Create a Lexer from a filename.
lex_document(document: Document) → Callable[[int], StyleAndTextTuples]¶
Create a lexer function that takes a line number and returns the list
of (style_str, text) tuples as the Pygments lexer returns for that line.
class prompt_toolkit.lexers.RegexSync(pattern: str)¶
Synchronize by starting at a line that matches the given regex pattern.
classmethod from_pygments_lexer_cls(lexer_cls: PygmentsLexerCls) → RegexSync¶
Create a RegexSync instance for this Pygments lexer class.
get_sync_start_position(document: Document, lineno: int) → tuple[int, int]¶
Scan backwards, and find a possible position to start.
class prompt_toolkit.lexers.SimpleLexer(style: str = '')¶
Lexer that doesn’t do any tokenizing and returns the whole input as one
token.
Parameters:
style – The style string for this lexer.
class prompt_toolkit.lexers.SyncFromStart¶
Always start the syntax highlighting from the beginning.
class prompt_toolkit.lexers.SyntaxSync¶
Syntax synchronizer. This is a tool that finds a start position for the
lexer. This is especially important when editing big documents; we don’t
want to start the highlighting by running the lexer from the beginning of
the file. That is very slow when editing.
abstractmethod get_sync_start_position(document: Document, lineno: int) → tuple[int, int]¶
Return the position from where we can start lexing as a (row, column)
tuple.
Parameters:
document – Document instance that contains all the lines.
lineno – The line that we want to highlight. (We need to return
this line, or an earlier position.)
Layout¶
Command line layout definitions¶
The layout of a command line interface is defined by a Container instance.
There are two main groups of classes here. Containers and controls:
A container can contain other containers or controls, it can have multiple
children and it decides about the dimensions.
A control is responsible for rendering the actual content to a screen.
A control can propose some dimensions, but it’s the container who decides
about the dimensions – or when the control consumes more space – which part
of the control will be visible.
Container classes:
- Container (Abstract base class)
|- HSplit (Horizontal split)
|- VSplit (Vertical split)
|- FloatContainer (Container which can also contain menus and other floats)
`- Window (Container which contains one actual control
Control classes:
- UIControl (Abstract base class)
|- FormattedTextControl (Renders formatted text, or a simple list of text fragments)
`- BufferControl (Renders an input buffer.)
Usually, you end up wrapping every control inside a Window object, because
that’s the only way to render it in a layout.
There are some prepared toolbars which are ready to use:
- SystemToolbar (Shows the 'system' input buffer, for entering system commands.)
- ArgToolbar (Shows the input 'arg', for repetition of input commands.)
- SearchToolbar (Shows the 'search' input buffer, for incremental search.)
- CompletionsToolbar (Shows the completions of the current buffer.)
- ValidationToolbar (Shows validation errors of the current buffer.)
And one prepared menu:
CompletionsMenu
The layout class itself¶
class prompt_toolkit.layout.Layout(container: AnyContainer, focused_element: FocusableElement | None = None)¶
The layout for a prompt_toolkit
Application.
This also keeps track of which user control is focused.
Parameters:
container – The “root” container for the layout.
focused_element – element to be focused initially. (Can be anything
the focus function accepts.)
property buffer_has_focus: bool¶
Return True if the currently focused control is a
BufferControl. (For instance, used to determine whether the
default key bindings should be active or not.)
property current_buffer: Buffer | None¶
The currently focused Buffer or None.
property current_control: UIControl¶
Get the UIControl to currently has the focus.
property current_window: Window¶
Return the Window object that is currently focused.
find_all_windows() → Generator[Window, None, None]¶
Find all the UIControl objects in this layout.
focus(value: FocusableElement) → None¶
Focus the given UI element.
value can be either:
a UIControl
a Buffer instance or the name of a Buffer
a Window
Any container object. In this case we will focus the Window
from this container that was focused most recent, or the very first
focusable Window of the container.
focus_last() → None¶
Give the focus to the last focused control.
focus_next() → None¶
Focus the next visible/focusable Window.
focus_previous() → None¶
Focus the previous visible/focusable Window.
get_buffer_by_name(buffer_name: str) → Buffer | None¶
Look in the layout for a buffer with the given name.
Return None when nothing was found.
get_focusable_windows() → Iterable[Window]¶
Return all the Window objects which are focusable (in the
‘modal’ area).
get_parent(container: Container) → Container | None¶
Return the parent container for the given container, or None, if it
wasn’t found.
get_visible_focusable_windows() → list[Window]¶
Return a list of Window objects that are focusable.
has_focus(value: FocusableElement) → bool¶
Check whether the given control has the focus.
:param value: UIControl or Window instance.
property is_searching: bool¶
True if we are searching right now.
property previous_control: UIControl¶
Get the UIControl to previously had the focus.
property search_target_buffer_control: BufferControl | None¶
Return the BufferControl in which we are searching or None.
update_parents_relations() → None¶
Update child->parent relationships mapping.
walk() → Iterable[Container]¶
Walk through all the layout nodes (and their children) and yield them.
walk_through_modal_area() → Iterable[Container]¶
Walk through all the containers which are in the current ‘modal’ part
of the layout.
class prompt_toolkit.layout.InvalidLayoutError¶
class prompt_toolkit.layout.walk(container: Container, skip_hidden: bool = False)¶
Walk through layout, starting at this container.
Containers¶
class prompt_toolkit.layout.Container¶
Base class for user interface layout.
abstractmethod get_children() → list[Container]¶
Return the list of child Container objects.
get_key_bindings() → KeyBindingsBase | None¶
Returns a KeyBindings object. These bindings become active when any
user control in this container has the focus, except if any containers
between this container and the focused user control is modal.
is_modal() → bool¶
When this container is modal, key bindings from parent containers are
not taken into account if a user control in this container is focused.
abstractmethod preferred_height(width: int, max_available_height: int) → Dimension¶
Return a Dimension that represents the
desired height for this container.
abstractmethod preferred_width(max_available_width: int) → Dimension¶
Return a Dimension that represents the
desired width for this container.
abstractmethod reset() → None¶
Reset the state of this container and all the children.
(E.g. reset scroll offsets, etc…)
abstractmethod write_to_screen(screen: Screen, mouse_handlers: MouseHandlers, write_position: WritePosition, parent_style: str, erase_bg: bool, z_index: int | None) → None¶
Write the actual content to the screen.
Parameters:
screen – Screen
mouse_handlers – MouseHandlers.
parent_style – Style string to pass to the Window
object. This will be applied to all content of the windows.
VSplit and HSplit can use it to pass their
style down to the windows that they contain.
z_index – Used for propagating z_index from parent to child.
class prompt_toolkit.layout.HSplit(children: Sequence[AnyContainer], window_too_small: Container | None = None, align: VerticalAlign = VerticalAlign.JUSTIFY, padding: AnyDimension = 0, padding_char: str | None = None, padding_style: str = '', width: AnyDimension = None, height: AnyDimension = None, z_index: int | None = None, modal: bool = False, key_bindings: KeyBindingsBase | None = None, style: str | Callable[[], str] = '')¶
Several layouts, one stacked above/under the other.
+--------------------+
|                    |
+--------------------+
|                    |
+--------------------+
By default, this doesn’t display a horizontal line between the children,
but if this is something you need, then create a HSplit as follows:
HSplit(children=[ ... ], padding_char='-',
padding=1, padding_style='#ffff00')
Parameters:
children – List of child Container objects.
window_too_small – A Container object that is displayed if
there is not enough space for all the children. By default, this is a
“Window too small” message.
align – VerticalAlign value.
width – When given, use this width instead of looking at the children.
height – When given, use this height instead of looking at the children.
z_index – (int or None) When specified, this can be used to bring
element in front of floating elements.  None means: inherit from parent.
style – A style string.
modal – True or False.
key_bindings – None or a KeyBindings object.
padding – (Dimension or int), size to be used for the padding.
padding_char – Character to be used for filling in the padding.
padding_style – Style to applied to the padding.
write_to_screen(screen: Screen, mouse_handlers: MouseHandlers, write_position: WritePosition, parent_style: str, erase_bg: bool, z_index: int | None) → None¶
Render the prompt to a Screen instance.
Parameters:
screen – The Screen class
to which the output has to be written.
class prompt_toolkit.layout.VSplit(children: Sequence[AnyContainer], window_too_small: Container | None = None, align: HorizontalAlign = HorizontalAlign.JUSTIFY, padding: AnyDimension = 0, padding_char: str | None = None, padding_style: str = '', width: AnyDimension = None, height: AnyDimension = None, z_index: int | None = None, modal: bool = False, key_bindings: KeyBindingsBase | None = None, style: str | Callable[[], str] = '')¶
Several layouts, one stacked left/right of the other.
+---------+----------+
|         |          |
|         |          |
+---------+----------+
By default, this doesn’t display a vertical line between the children, but
if this is something you need, then create a HSplit as follows:
VSplit(children=[ ... ], padding_char='|',
padding=1, padding_style='#ffff00')
Parameters:
children – List of child Container objects.
window_too_small – A Container object that is displayed if
there is not enough space for all the children. By default, this is a
“Window too small” message.
align – HorizontalAlign value.
width – When given, use this width instead of looking at the children.
height – When given, use this height instead of looking at the children.
z_index – (int or None) When specified, this can be used to bring
element in front of floating elements.  None means: inherit from parent.
style – A style string.
modal – True or False.
key_bindings – None or a KeyBindings object.
padding – (Dimension or int), size to be used for the padding.
padding_char – Character to be used for filling in the padding.
padding_style – Style to applied to the padding.
write_to_screen(screen: Screen, mouse_handlers: MouseHandlers, write_position: WritePosition, parent_style: str, erase_bg: bool, z_index: int | None) → None¶
Render the prompt to a Screen instance.
Parameters:
screen – The Screen class
to which the output has to be written.
class prompt_toolkit.layout.FloatContainer(content: AnyContainer, floats: list[Float], modal: bool = False, key_bindings: KeyBindingsBase | None = None, style: str | Callable[[], str] = '', z_index: int | None = None)¶
Container which can contain another container for the background, as well
as a list of floating containers on top of it.
Example Usage:
FloatContainer(content=Window(...),
floats=[
Float(xcursor=True,
ycursor=True,
content=CompletionsMenu(...))
])
Parameters:
z_index – (int or None) When specified, this can be used to bring
element in front of floating elements.  None means: inherit from parent.
This is the z_index for the whole Float container as a whole.
preferred_height(width: int, max_available_height: int) → Dimension¶
Return the preferred height of the float container.
(We don’t care about the height of the floats, they should always fit
into the dimensions provided by the container.)
class prompt_toolkit.layout.Float(content: AnyContainer, top: int | None = None, right: int | None = None, bottom: int | None = None, left: int | None = None, width: int | Callable[[], int] | None = None, height: int | Callable[[], int] | None = None, xcursor: bool = False, ycursor: bool = False, attach_to_window: AnyContainer | None = None, hide_when_covering_content: bool = False, allow_cover_cursor: bool = False, z_index: int = 1, transparent: bool = False)¶
Float for use in a FloatContainer.
Except for the content parameter, all other options are optional.
Parameters:
content – Container instance.
width – Dimension or callable which returns a Dimension.
height – Dimension or callable which returns a Dimension.
left – Distance to the left edge of the FloatContainer.
right – Distance to the right edge of the FloatContainer.
top – Distance to the top of the FloatContainer.
bottom – Distance to the bottom of the FloatContainer.
attach_to_window – Attach to the cursor from this window, instead of
the current window.
hide_when_covering_content – Hide the float when it covers content underneath.
allow_cover_cursor – When False, make sure to display the float
below the cursor. Not on top of the indicated position.
z_index – Z-index position. For a Float, this needs to be at least
one. It is relative to the z_index of the parent container.
transparent – Filter indicating whether this float needs to be
drawn transparently.
class prompt_toolkit.layout.Window(content: UIControl | None = None, width: AnyDimension = None, height: AnyDimension = None, z_index: int | None = None, dont_extend_width: FilterOrBool = False, dont_extend_height: FilterOrBool = False, ignore_content_width: FilterOrBool = False, ignore_content_height: FilterOrBool = False, left_margins: Sequence[Margin] | None = None, right_margins: Sequence[Margin] | None = None, scroll_offsets: ScrollOffsets | None = None, allow_scroll_beyond_bottom: FilterOrBool = False, wrap_lines: FilterOrBool = False, get_vertical_scroll: Callable[[Window], int] | None = None, get_horizontal_scroll: Callable[[Window], int] | None = None, always_hide_cursor: FilterOrBool = False, cursorline: FilterOrBool = False, cursorcolumn: FilterOrBool = False, colorcolumns: None | list[ColorColumn] | Callable[[], list[ColorColumn]] = None, align: WindowAlign | Callable[[], WindowAlign] = WindowAlign.LEFT, style: str | Callable[[], str] = '', char: None | str | Callable[[], str] = None, get_line_prefix: GetLinePrefixCallable | None = None)¶
Container that holds a control.
Parameters:
content – UIControl instance.
width – Dimension instance or callable.
height – Dimension instance or callable.
z_index – When specified, this can be used to bring element in front
of floating elements.
dont_extend_width – When True, don’t take up more width then the
preferred width reported by the control.
dont_extend_height – When True, don’t take up more width then the
preferred height reported by the control.
ignore_content_width – A bool or Filter instance. Ignore
the UIContent width when calculating the dimensions.
ignore_content_height – A bool or Filter instance. Ignore
the UIContent height when calculating the dimensions.
left_margins – A list of Margin instance to be displayed on
the left. For instance: NumberedMargin
can be one of them in order to show line numbers.
right_margins – Like left_margins, but on the other side.
scroll_offsets – ScrollOffsets instance, representing the
preferred amount of lines/columns to be always visible before/after the
cursor. When both top and bottom are a very high number, the cursor
will be centered vertically most of the time.
allow_scroll_beyond_bottom – A bool or
Filter instance. When True, allow scrolling so far, that the
top part of the content is not visible anymore, while there is still
empty space available at the bottom of the window. In the Vi editor for
instance, this is possible. You will see tildes while the top part of
the body is hidden.
wrap_lines – A bool or Filter instance. When True, don’t
scroll horizontally, but wrap lines instead.
get_vertical_scroll – Callable that takes this window
instance as input and returns a preferred vertical scroll.
(When this is None, the scroll is only determined by the last and
current cursor position.)
get_horizontal_scroll – Callable that takes this window
instance as input and returns a preferred vertical scroll.
always_hide_cursor – A bool or
Filter instance. When True, never display the cursor, even
when the user control specifies a cursor position.
cursorline – A bool or Filter instance. When True,
display a cursorline.
cursorcolumn – A bool or Filter instance. When True,
display a cursorcolumn.
colorcolumns – A list of ColorColumn instances that
describe the columns to be highlighted, or a callable that returns such
a list.
align – WindowAlign value or callable that returns an
WindowAlign value. alignment of content.
style – A style string. Style to be applied to all the cells in this
window. (This can be a callable that returns a string.)
char – (string) Character to be used for filling the background. This
can also be a callable that returns a character.
get_line_prefix – None or a callable that returns formatted text to
be inserted before a line. It takes a line number (int) and a
wrap_count and returns formatted text. This can be used for
implementation of line continuations, things like Vim “breakindent” and
so on.
preferred_height(width: int, max_available_height: int) → Dimension¶
Calculate the preferred height for this window.
preferred_width(max_available_width: int) → Dimension¶
Calculate the preferred width for this window.
write_to_screen(screen: Screen, mouse_handlers: MouseHandlers, write_position: WritePosition, parent_style: str, erase_bg: bool, z_index: int | None) → None¶
Write window to screen. This renders the user control, the margins and
copies everything over to the absolute position at the given screen.
class prompt_toolkit.layout.WindowAlign(value)¶
Alignment of the Window content.
Note that this is different from HorizontalAlign and VerticalAlign,
which are used for the alignment of the child containers in respectively
VSplit and HSplit.
class prompt_toolkit.layout.ConditionalContainer(content: AnyContainer, filter: FilterOrBool, alternative_content: AnyContainer | None = None)¶
Wrapper around any other container that can change the visibility. The
received filter determines whether the given container should be
displayed or not.
Parameters:
content – Container instance.
filter – Filter instance.
class prompt_toolkit.layout.DynamicContainer(get_container: Callable[[], AnyContainer])¶
Container class that dynamically returns any Container.
Parameters:
get_container – Callable that returns a Container instance
or any widget with a __pt_container__ method.
class prompt_toolkit.layout.ScrollablePane(content: Container, scroll_offsets: ScrollOffsets | None = None, keep_cursor_visible: Filter | bool = True, keep_focused_window_visible: Filter | bool = True, max_available_height: int = 10000, width: None | int | Dimension | Callable[[], Any] = None, height: None | int | Dimension | Callable[[], Any] = None, show_scrollbar: Filter | bool = True, display_arrows: Filter | bool = True, up_arrow_symbol: str = '^', down_arrow_symbol: str = 'v')¶
Container widget that exposes a larger virtual screen to its content and
displays it in a vertical scrollbale region.
Typically this is wrapped in a large HSplit container. Make sure in that
case to not specify a height dimension of the HSplit, so that it will
scale according to the content.
Note
If you want to display a completion menu for widgets in this
ScrollablePane, then it’s still a good practice to use a
FloatContainer with a CompletionsMenu in a Float at the top-level
of the layout hierarchy, rather then nesting a FloatContainer in this
ScrollablePane. (Otherwise, it’s possible that the completion menu
is clipped.)
Parameters:
content – The content container.
scrolloffset – Try to keep the cursor within this distance from the
top/bottom (left/right offset is not used).
keep_cursor_visible – When True, automatically scroll the pane so
that the cursor (of the focused window) is always visible.
keep_focused_window_visible – When True, automatically scroll the
pane so that the focused window is visible, or as much visible as
possible if it doesn’t completely fit the screen.
max_available_height – Always constraint the height to this amount
for performance reasons.
width – When given, use this width instead of looking at the children.
height – When given, use this height instead of looking at the children.
show_scrollbar – When True display a scrollbar on the right.
write_to_screen(screen: Screen, mouse_handlers: MouseHandlers, write_position: WritePosition, parent_style: str, erase_bg: bool, z_index: int | None) → None¶
Render scrollable pane content.
This works by rendering on an off-screen canvas, and copying over the
visible region.
class prompt_toolkit.layout.ScrollOffsets(top: int | Callable[[], int] = 0, bottom: int | Callable[[], int] = 0, left: int | Callable[[], int] = 0, right: int | Callable[[], int] = 0)¶
Scroll offsets for the Window class.
Note that left/right offsets only make sense if line wrapping is disabled.
class prompt_toolkit.layout.ColorColumn(position: int, style: str = 'class:color-column')¶
Column for a Window to be colored.
class prompt_toolkit.layout.to_container(container: AnyContainer)¶
Make sure that the given object is a Container.
class prompt_toolkit.layout.to_window(container: AnyContainer)¶
Make sure that the given argument is a Window.
class prompt_toolkit.layout.is_container(value: object)¶
Checks whether the given value is a container object
(for use in assert statements).
class prompt_toolkit.layout.HorizontalAlign(value)¶
Alignment for VSplit.
class prompt_toolkit.layout.VerticalAlign(value)¶
Alignment for HSplit.
Controls¶
class prompt_toolkit.layout.BufferControl(buffer: Buffer | None = None, input_processors: list[Processor] | None = None, include_default_input_processors: bool = True, lexer: Lexer | None = None, preview_search: FilterOrBool = False, focusable: FilterOrBool = True, search_buffer_control: None | SearchBufferControl | Callable[[], SearchBufferControl] = None, menu_position: Callable[[], int | None] | None = None, focus_on_click: FilterOrBool = False, key_bindings: KeyBindingsBase | None = None)¶
Control for visualizing the content of a Buffer.
Parameters:
buffer – The Buffer object to be displayed.
input_processors – A list of
Processor objects.
include_default_input_processors – When True, include the default
processors for highlighting of selection, search and displaying of
multiple cursors.
lexer – Lexer instance for syntax highlighting.
preview_search – bool or Filter: Show search while
typing. When this is True, probably you want to add a
HighlightIncrementalSearchProcessor as well. Otherwise only the
cursor position will move, but the text won’t be highlighted.
focusable – bool or Filter: Tell whether this control is focusable.
focus_on_click – Focus this buffer when it’s click, but not yet focused.
key_bindings – a KeyBindings object.
create_content(width: int, height: int, preview_search: bool = False) → UIContent¶
Create a UIContent.
get_invalidate_events() → Iterable[Event[object]]¶
Return the Window invalidate events.
get_key_bindings() → KeyBindingsBase | None¶
When additional key bindings are given. Return these.
mouse_handler(mouse_event: MouseEvent) → NotImplementedOrNone¶
Mouse handler for this control.
preferred_width(max_available_width: int) → int | None¶
This should return the preferred width.
Note: We don’t specify a preferred width according to the content,
because it would be too expensive. Calculating the preferred
width can be done by calculating the longest line, but this would
require applying all the processors to each line. This is
unfeasible for a larger document, and doing it for small
documents only would result in inconsistent behavior.
property search_state: SearchState¶
Return the SearchState for searching this BufferControl. This is
always associated with the search control. If one search bar is used
for searching multiple BufferControls, then they share the same
SearchState.
class prompt_toolkit.layout.SearchBufferControl(buffer: Buffer | None = None, input_processors: list[Processor] | None = None, lexer: Lexer | None = None, focus_on_click: FilterOrBool = False, key_bindings: KeyBindingsBase | None = None, ignore_case: FilterOrBool = False)¶
BufferControl which is used for searching another
BufferControl.
Parameters:
ignore_case – Search case insensitive.
class prompt_toolkit.layout.DummyControl¶
A dummy control object that doesn’t paint any content.
Useful for filling a Window. (The
fragment and char attributes of the Window class can be used to
define the filling.)
class prompt_toolkit.layout.FormattedTextControl(text: AnyFormattedText = '', style: str = '', focusable: FilterOrBool = False, key_bindings: KeyBindingsBase | None = None, show_cursor: bool = True, modal: bool = False, get_cursor_position: Callable[[], Point | None] | None = None)¶
Control that displays formatted text. This can be either plain text, an
HTML object an
ANSI object, a list of (style_str,
text) tuples or a callable that takes no argument and returns one of
those, depending on how you prefer to do the formatting. See
prompt_toolkit.layout.formatted_text for more information.
(It’s mostly optimized for rather small widgets, like toolbars, menus, etc…)
When this UI control has the focus, the cursor will be shown in the upper
left corner of this control by default. There are two ways for specifying
the cursor position:
Pass a get_cursor_position function which returns a Point instance
with the current cursor position.
If the (formatted) text is passed as a list of (style, text) tuples
and there is one that looks like ('[SetCursorPosition]', ''), then
this will specify the cursor position.
Mouse support:
The list of fragments can also contain tuples of three items, looking like:
(style_str, text, handler). When mouse support is enabled and the user
clicks on this fragment, then the given handler is called. That handler
should accept two inputs: (Application, MouseEvent) and it should
either handle the event or return NotImplemented in case we want the
containing Window to handle this event.
Parameters:
focusable – bool or Filter: Tell whether this control is
focusable.
text – Text or formatted text to be displayed.
style – Style string applied to the content. (If you want to style
the whole Window, pass the style to the
Window instead.)
key_bindings – a KeyBindings object.
get_cursor_position – A callable that returns the cursor position as
a Point instance.
mouse_handler(mouse_event: MouseEvent) → NotImplementedOrNone¶
Handle mouse events.
(When the fragment list contained mouse handlers and the user clicked on
on any of these, the matching handler is called. This handler can still
return NotImplemented in case we want the
Window to handle this particular
event.)
preferred_height(width: int, max_available_height: int, wrap_lines: bool, get_line_prefix: GetLinePrefixCallable | None) → int | None¶
Return the preferred height for this control.
preferred_width(max_available_width: int) → int¶
Return the preferred width for this control.
That is the width of the longest line.
class prompt_toolkit.layout.UIControl¶
Base class for all user interface controls.
abstractmethod create_content(width: int, height: int) → UIContent¶
Generate the content for this user control.
Returns a UIContent instance.
get_invalidate_events() → Iterable[Event[object]]¶
Return a list of Event objects. This can be a generator.
(The application collects all these events, in order to bind redraw
handlers to these events.)
get_key_bindings() → KeyBindingsBase | None¶
The key bindings that are specific for this user control.
Return a KeyBindings object if some key bindings are
specified, or None otherwise.
is_focusable() → bool¶
Tell whether this user control is focusable.
mouse_handler(mouse_event: MouseEvent) → NotImplementedOrNone¶
Handle mouse events.
When NotImplemented is returned, it means that the given event is not
handled by the UIControl itself. The Window or key bindings can
decide to handle this event as scrolling or changing focus.
Parameters:
mouse_event – MouseEvent instance.
move_cursor_down() → None¶
Request to move the cursor down.
This happens when scrolling down and the cursor is completely at the
top.
move_cursor_up() → None¶
Request to move the cursor up.
class prompt_toolkit.layout.UIContent(get_line: Callable[[int], StyleAndTextTuples] = <function UIContent.<lambda>>, line_count: int = 0, cursor_position: Point | None = None, menu_position: Point | None = None, show_cursor: bool = True)¶
Content generated by a user control. This content consists of a list of
lines.
Parameters:
get_line – Callable that takes a line number and returns the current
line. This is a list of (style_str, text) tuples.
line_count – The number of lines.
cursor_position – a Point for the cursor position.
menu_position – a Point for the menu position.
show_cursor – Make the cursor visible.
get_height_for_line(lineno: int, width: int, get_line_prefix: GetLinePrefixCallable | None, slice_stop: int | None = None) → int¶
Return the height that a given line would need if it is rendered in a
space with the given width (using line wrapping).
Parameters:
get_line_prefix – None or a Window.get_line_prefix callable
that returns the prefix to be inserted before this line.
slice_stop – Wrap only “line[:slice_stop]” and return that
partial result. This is needed for scrolling the window correctly
when line wrapping.
Returns:
The computed height.
Other¶
Sizing¶
class prompt_toolkit.layout.Dimension(min: int | None = None, max: int | None = None, weight: int | None = None, preferred: int | None = None)¶
Specified dimension (width/height) of a user control or window.
The layout engine tries to honor the preferred size. If that is not
possible, because the terminal is larger or smaller, it tries to keep in
between min and max.
Parameters:
min – Minimum size.
max – Maximum size.
weight – For a VSplit/HSplit, the actual size will be determined
by taking the proportion of weights from all the children.
E.g. When there are two children, one with a weight of 1,
and the other with a weight of 2, the second will always be
twice as big as the first, if the min/max values allow it.
preferred – Preferred size.
classmethod exact(amount: int) → Dimension¶
Return a Dimension with an exact size. (min, max and
preferred set to amount).
classmethod zero() → Dimension¶
Create a dimension that represents a zero size. (Used for ‘invisible’
controls.)
Margins¶
class prompt_toolkit.layout.Margin¶
Base interface for a margin.
abstractmethod create_margin(window_render_info: WindowRenderInfo, width: int, height: int) → StyleAndTextTuples¶
Creates a margin.
This should return a list of (style_str, text) tuples.
Parameters:
window_render_info – WindowRenderInfo
instance, generated after rendering and copying the visible part of
the UIControl into the
Window.
width – The width that’s available for this margin. (As reported
by get_width().)
height – The height that’s available for this margin. (The height
of the Window.)
abstractmethod get_width(get_ui_content: Callable[[], UIContent]) → int¶
Return the width that this margin is going to consume.
Parameters:
get_ui_content – Callable that asks the user control to create
a UIContent instance. This can be used for instance to
obtain the number of lines.
class prompt_toolkit.layout.NumberedMargin(relative: Filter | bool = False, display_tildes: Filter | bool = False)¶
Margin that displays the line numbers.
Parameters:
relative – Number relative to the cursor position. Similar to the Vi
‘relativenumber’ option.
display_tildes – Display tildes after the end of the document, just
like Vi does.
class prompt_toolkit.layout.ScrollbarMargin(display_arrows: Filter | bool = False, up_arrow_symbol: str = '^', down_arrow_symbol: str = 'v')¶
Margin displaying a scrollbar.
Parameters:
display_arrows – Display scroll up/down arrows.
class prompt_toolkit.layout.ConditionalMargin(margin: Margin, filter: Filter | bool)¶
Wrapper around other Margin classes to show/hide them.
class prompt_toolkit.layout.PromptMargin(get_prompt: Callable[[], StyleAndTextTuples], get_continuation: None | Callable[[int, int, bool], StyleAndTextTuples] = None)¶
[Deprecated]
Create margin that displays a prompt.
This can display one prompt at the first line, and a continuation prompt
(e.g, just dots) on all the following lines.
This PromptMargin implementation has been largely superseded in favor of
the get_line_prefix attribute of Window. The reason is that a margin is
always a fixed width, while get_line_prefix can return a variable width
prefix in front of every line, making it more powerful, especially for line
continuations.
Parameters:
get_prompt – Callable returns formatted text or a list of
(style_str, type) tuples to be shown as the prompt at the first line.
get_continuation – Callable that takes three inputs. The width (int),
line_number (int), and is_soft_wrap (bool). It should return formatted
text or a list of (style_str, type) tuples for the next lines of the
input.
get_width(get_ui_content: Callable[[], UIContent]) → int¶
Width to report to the Window.
Completion Menus¶
class prompt_toolkit.layout.CompletionsMenu(max_height: int | None = None, scroll_offset: int | Callable[[], int] = 0, extra_filter: Filter | bool = True, display_arrows: Filter | bool = False, z_index: int = 100000000)¶
class prompt_toolkit.layout.MultiColumnCompletionsMenu(min_rows: int = 3, suggested_max_column_width: int = 30, show_meta: Filter | bool = True, extra_filter: Filter | bool = True, z_index: int = 100000000)¶
Container that displays the completions in several columns.
When show_meta (a Filter) evaluates
to True, it shows the meta information at the bottom.
Processors¶
Processors are little transformation blocks that transform the fragments list
from a buffer before the BufferControl will render it to the screen.
They can insert fragments before or after, or highlight fragments by replacing the
fragment types.
class prompt_toolkit.layout.processors.AfterInput(text: AnyFormattedText, style: str = '')¶
Insert text after the input.
Parameters:
text – This can be either plain text or formatted text
(or a callable that returns any of those).
style – style to be applied to this prompt/prefix.
class prompt_toolkit.layout.processors.AppendAutoSuggestion(style: str = 'class:auto-suggestion')¶
Append the auto suggestion to the input.
(The user can then press the right arrow the insert the suggestion.)
class prompt_toolkit.layout.processors.BeforeInput(text: AnyFormattedText, style: str = '')¶
Insert text before the input.
Parameters:
text – This can be either plain text or formatted text
(or a callable that returns any of those).
style – style to be applied to this prompt/prefix.
class prompt_toolkit.layout.processors.ConditionalProcessor(processor: Processor, filter: Filter | bool)¶
Processor that applies another processor, according to a certain condition.
Example:
# Create a function that returns whether or not the processor should
# currently be applied.
def highlight_enabled():
return true_or_false
# Wrapped it in a `ConditionalProcessor` for usage in a `BufferControl`.
BufferControl(input_processors=[
ConditionalProcessor(HighlightSearchProcessor(),
Condition(highlight_enabled))])
Parameters:
processor – Processor instance.
filter – Filter instance.
class prompt_toolkit.layout.processors.DisplayMultipleCursors¶
When we’re in Vi block insert mode, display all the cursors.
class prompt_toolkit.layout.processors.DummyProcessor¶
A Processor that doesn’t do anything.
class prompt_toolkit.layout.processors.DynamicProcessor(get_processor: Callable[[], Processor | None])¶
Processor class that dynamically returns any Processor.
Parameters:
get_processor – Callable that returns a Processor instance.
class prompt_toolkit.layout.processors.HighlightIncrementalSearchProcessor¶
Highlight the search terms that are used for highlighting the incremental
search. The style class ‘incsearch’ will be applied to the content.
Important: this requires the preview_search=True flag to be set for the
BufferControl. Otherwise, the cursor position won’t be set to the search
match while searching, and nothing happens.
class prompt_toolkit.layout.processors.HighlightMatchingBracketProcessor(chars: str = '[](){}<>', max_cursor_distance: int = 1000)¶
When the cursor is on or right after a bracket, it highlights the matching
bracket.
Parameters:
max_cursor_distance – Only highlight matching brackets when the
cursor is within this distance. (From inside a Processor, we can’t
know which lines will be visible on the screen. But we also don’t want
to scan the whole document for matching brackets on each key press, so
we limit to this value.)
class prompt_toolkit.layout.processors.HighlightSearchProcessor¶
Processor that highlights search matches in the document.
Note that this doesn’t support multiline search matches yet.
The style classes ‘search’ and ‘search.current’ will be applied to the
content.
class prompt_toolkit.layout.processors.HighlightSelectionProcessor¶
Processor that highlights the selection in the document.
class prompt_toolkit.layout.processors.PasswordProcessor(char: str = '*')¶
Processor that masks the input. (For passwords.)
Parameters:
char – (string) Character to be used. “*” by default.
class prompt_toolkit.layout.processors.Processor¶
Manipulate the fragments for a given line in a
BufferControl.
abstractmethod apply_transformation(transformation_input: TransformationInput) → Transformation¶
Apply transformation. Returns a Transformation instance.
Parameters:
transformation_input – TransformationInput object.
class prompt_toolkit.layout.processors.ReverseSearchProcessor¶
Process to display the “(reverse-i-search)`…`:…” stuff around
the search buffer.
Note: This processor is meant to be applied to the BufferControl that
contains the search buffer, it’s not meant for the original input.
class prompt_toolkit.layout.processors.ShowArg¶
Display the ‘arg’ in front of the input.
This was used by the PromptSession, but now it uses the
Window.get_line_prefix function instead.
class prompt_toolkit.layout.processors.ShowLeadingWhiteSpaceProcessor(get_char: Callable[[], str] | None = None, style: str = 'class:leading-whitespace')¶
Make leading whitespace visible.
Parameters:
get_char – Callable that returns one character.
class prompt_toolkit.layout.processors.ShowTrailingWhiteSpaceProcessor(get_char: Callable[[], str] | None = None, style: str = 'class:training-whitespace')¶
Make trailing whitespace visible.
Parameters:
get_char – Callable that returns one character.
class prompt_toolkit.layout.processors.TabsProcessor(tabstop: int | Callable[[], int] = 4, char1: str | Callable[[], str] = '|', char2: str | Callable[[], str] = '┈', style: str = 'class:tab')¶
Render tabs as spaces (instead of ^I) or make them visible (for instance,
by replacing them with dots.)
Parameters:
tabstop – Horizontal space taken by a tab. (int or callable that
returns an int).
char1 – Character or callable that returns a character (text of
length one). This one is used for the first space taken by the tab.
char2 – Like char1, but for the rest of the space.
class prompt_toolkit.layout.processors.Transformation(fragments: StyleAndTextTuples, source_to_display: SourceToDisplay | None = None, display_to_source: DisplayToSource | None = None)¶
Transformation result, as returned by Processor.apply_transformation().
Important: Always make sure that the length of document.text is equal to
the length of all the text in fragments!
Parameters:
fragments – The transformed fragments. To be displayed, or to pass to
the next processor.
source_to_display – Cursor position transformation from original
string to transformed string.
display_to_source – Cursor position transformed from source string to
original string.
class prompt_toolkit.layout.processors.TransformationInput(buffer_control: BufferControl, document: Document, lineno: int, source_to_display: SourceToDisplay, fragments: StyleAndTextTuples, width: int, height: int, get_line: Callable[[int], StyleAndTextTuples] | None = None)¶
Parameters:
buffer_control – BufferControl instance.
lineno – The number of the line to which we apply the processor.
source_to_display – A function that returns the position in the
fragments for any position in the source string. (This takes
previous processors into account.)
fragments – List of fragments that we can transform. (Received from the
previous processor.)
get_line – Optional ; a callable that returns the fragments of another
line in the  current buffer; This can be used to create processors capable
of affecting transforms across multiple lines.
prompt_toolkit.layout.processors.merge_processors(processors: list[Processor]) → Processor¶
Merge multiple Processor objects into one.
Utils¶
prompt_toolkit.layout.utils.explode_text_fragments(fragments: Iterable[_T]) → _ExplodedList[_T]¶
Turn a list of (style_str, text) tuples into another list where each string is
exactly one character.
It should be fine to call this function several times. Calling this on a
list that is already exploded, is a null operation.
Parameters:
fragments – List of (style, text) tuples.
Screen¶
class prompt_toolkit.layout.screen.Char(char: str = ' ', style: str = '')¶
Represent a single character in a Screen.
This should be considered immutable.
Parameters:
char – A single character (can be a double-width character).
style – A style string. (Can contain classnames.)
class prompt_toolkit.layout.screen.Screen(default_char: Char | None = None, initial_width: int = 0, initial_height: int = 0)¶
Two dimensional buffer of Char instances.
append_style_to_content(style_str: str) → None¶
For all the characters in the screen.
Set the style string to the given style_str.
cursor_positions: dict[Window, Point]¶
Position of the cursor.
draw_all_floats() → None¶
Draw all float functions in order of z-index.
draw_with_z_index(z_index: int, draw_func: Callable[[], None]) → None¶
Add a draw-function for a Window which has a >= 0 z_index.
This will be postponed until draw_all_floats is called.
fill_area(write_position: WritePosition, style: str = '', after: bool = False) → None¶
Fill the content of this area, using the given style.
The style is prepended before whatever was here before.
get_cursor_position(window: Window) → Point¶
Get the cursor position for a given window.
Returns a Point.
get_menu_position(window: Window) → Point¶
Get the menu position for a given window.
(This falls back to the cursor position if no menu position was set.)
menu_positions: dict[Window, Point]¶
(Optional) Where to position the menu. E.g. at the start of a completion.
(We can’t use the cursor position, because we don’t want the
completion menu to change its position when we browse through all the
completions.)
set_cursor_position(window: Window, position: Point) → None¶
Set the cursor position for a given window.
set_menu_position(window: Window, position: Point) → None¶
Set the cursor position for a given window.
show_cursor¶
Visibility of the cursor.
width¶
Currently used width/height of the screen. This will increase when
data is written to the screen.
zero_width_escapes: defaultdict[int, defaultdict[int, str]]¶
Escape sequences to be injected.
Widgets¶
Collection of reusable components for building full screen applications.
These are higher level abstractions on top of the prompt_toolkit.layout
module.
Most of these widgets implement the __pt_container__ method, which makes it
possible to embed these in the layout like any other container.
class prompt_toolkit.widgets.Box(body: AnyContainer, padding: AnyDimension = None, padding_left: AnyDimension = None, padding_right: AnyDimension = None, padding_top: AnyDimension = None, padding_bottom: AnyDimension = None, width: AnyDimension = None, height: AnyDimension = None, style: str = '', char: None | str | Callable[[], str] = None, modal: bool = False, key_bindings: KeyBindings | None = None)¶
Add padding around a container.
This also makes sure that the parent can provide more space than required by
the child. This is very useful when wrapping a small element with a fixed
size into a VSplit or HSplit object. The HSplit and VSplit
try to make sure to adapt respectively the width and height, possibly
shrinking other elements. Wrapping something in a Box makes it flexible.
Parameters:
body – Another container object.
padding – The margin to be used around the body. This can be
overridden by padding_left, padding_right`, padding_top and
padding_bottom.
style – A style string.
char – Character to be used for filling the space around the body.
(This is supposed to be a character with a terminal width of 1.)
class prompt_toolkit.widgets.Button(text: str, handler: Callable[[], None] | None = None, width: int = 12, left_symbol: str = '<', right_symbol: str = '>')¶
Clickable button.
Parameters:
text – The caption for the button.
handler – None or callable. Called when the button is clicked. No
parameters are passed to this callable. Use for instance Python’s
functools.partial to pass parameters to this callable if needed.
width – Width of the button.
class prompt_toolkit.widgets.Checkbox(text: AnyFormattedText = '', checked: bool = False)¶
Backward compatibility util: creates a 1-sized CheckboxList
Parameters:
text – the text
class prompt_toolkit.widgets.Frame(body: AnyContainer, title: AnyFormattedText = '', style: str = '', width: AnyDimension = None, height: AnyDimension = None, key_bindings: KeyBindings | None = None, modal: bool = False)¶
Draw a border around any container, optionally with a title text.
Changing the title and body of the frame is possible at runtime by
assigning to the body and title attributes of this class.
Parameters:
body – Another container object.
title – Text to be displayed in the top of the frame (can be formatted text).
style – Style string to be applied to this widget.
class prompt_toolkit.widgets.HorizontalLine¶
A simple horizontal line with a height of 1.
class prompt_toolkit.widgets.Label(text: AnyFormattedText, style: str = '', width: AnyDimension = None, dont_extend_height: bool = True, dont_extend_width: bool = False, align: WindowAlign | Callable[[], WindowAlign] = WindowAlign.LEFT, wrap_lines: FilterOrBool = True)¶
Widget that displays the given text. It is not editable or focusable.
Parameters:
text – Text to display. Can be multiline. All value types accepted by
prompt_toolkit.layout.FormattedTextControl are allowed,
including a callable.
style – A style string.
width – When given, use this width, rather than calculating it from
the text size.
dont_extend_width – When True, don’t take up more width than
preferred, i.e. the length of the longest line of
the text, or value of width parameter, if
given. True by default
dont_extend_height – When True, don’t take up more width than the
preferred height, i.e. the number of lines of
the text. False by default.
class prompt_toolkit.widgets.MenuContainer(body: AnyContainer, menu_items: list[MenuItem], floats: list[Float] | None = None, key_bindings: KeyBindingsBase | None = None)¶
Parameters:
floats – List of extra Float objects to display.
menu_items – List of MenuItem objects.
class prompt_toolkit.widgets.RadioList(values: Sequence[tuple[_T, AnyFormattedText]], default: _T | None = None, show_numbers: bool = False, select_on_focus: bool = False, open_character: str = '(', select_character: str = '*', close_character: str = ')', container_style: str = 'class:radio-list', default_style: str = 'class:radio', selected_style: str = 'class:radio-selected', checked_style: str = 'class:radio-checked', number_style: str = 'class:radio-number', multiple_selection: bool = False, show_cursor: bool = True, show_scrollbar: bool = True)¶
List of radio buttons. Only one can be checked at the same time.
Parameters:
values – List of (value, label) tuples.
class prompt_toolkit.widgets.SearchToolbar(search_buffer: Buffer | None = None, vi_mode: bool = False, text_if_not_searching: AnyFormattedText = '', forward_search_prompt: AnyFormattedText = 'I-search: ', backward_search_prompt: AnyFormattedText = 'I-search backward: ', ignore_case: FilterOrBool = False)¶
Parameters:
vi_mode – Display ‘/’ and ‘?’ instead of I-search.
ignore_case – Search case insensitive.
class prompt_toolkit.widgets.Shadow(body: AnyContainer)¶
Draw a shadow underneath/behind this container.
(This applies class:shadow the the cells under the shadow. The Style
should define the colors for the shadow.)
Parameters:
body – Another container object.
class prompt_toolkit.widgets.SystemToolbar(prompt: AnyFormattedText = 'Shell command: ', enable_global_bindings: FilterOrBool = True)¶
Toolbar for a system prompt.
Parameters:
prompt – Prompt to be displayed to the user.
class prompt_toolkit.widgets.TextArea(text: str = '', multiline: FilterOrBool = True, password: FilterOrBool = False, lexer: Lexer | None = None, auto_suggest: AutoSuggest | None = None, completer: Completer | None = None, complete_while_typing: FilterOrBool = True, validator: Validator | None = None, accept_handler: BufferAcceptHandler | None = None, history: History | None = None, focusable: FilterOrBool = True, focus_on_click: FilterOrBool = False, wrap_lines: FilterOrBool = True, read_only: FilterOrBool = False, width: AnyDimension = None, height: AnyDimension = None, dont_extend_height: FilterOrBool = False, dont_extend_width: FilterOrBool = False, line_numbers: bool = False, get_line_prefix: GetLinePrefixCallable | None = None, scrollbar: bool = False, style: str = '', search_field: SearchToolbar | None = None, preview_search: FilterOrBool = True, prompt: AnyFormattedText = '', input_processors: list[Processor] | None = None, name: str = '')¶
A simple input field.
This is a higher level abstraction on top of several other classes with
sane defaults.
This widget does have the most common options, but it does not intend to
cover every single use case. For more configurations options, you can
always build a text area manually, using a
Buffer,
BufferControl and
Window.
Buffer attributes:
Parameters:
text – The initial text.
multiline – If True, allow multiline input.
completer – Completer instance
for auto completion.
complete_while_typing – Boolean.
accept_handler – Called when Enter is pressed (This should be a
callable that takes a buffer as input).
history – History instance.
auto_suggest – AutoSuggest
instance for input suggestions.
BufferControl attributes:
Parameters:
password – When True, display using asterisks.
focusable – When True, allow this widget to receive the focus.
focus_on_click – When True, focus after mouse click.
input_processors – None or a list of
Processor objects.
validator – None or a Validator
object.
Window attributes:
Parameters:
lexer – Lexer instance for syntax
highlighting.
wrap_lines – When True, don’t scroll horizontally, but wrap lines.
width – Window width. (Dimension object.)
height – Window height. (Dimension object.)
scrollbar – When True, display a scroll bar.
style – A style string.
dont_extend_width – When True, don’t take up more width then the
preferred width reported by the control.
dont_extend_height – When True, don’t take up more width then the
preferred height reported by the control.
get_line_prefix – None or a callable that returns formatted text to
be inserted before a line. It takes a line number (int) and a
wrap_count and returns formatted text. This can be used for
implementation of line continuations, things like Vim “breakindent” and
so on.
Other attributes:
Parameters:
search_field – An optional SearchToolbar object.
property accept_handler: Callable[[Buffer], bool] | None¶
The accept handler. Called when the user accepts the input.
property document: Document¶
The Buffer document (text + cursor position).
property text: str¶
The Buffer text.
class prompt_toolkit.widgets.VerticalLine¶
A simple vertical line with a width of 1.
Filters¶
Filters decide whether something is active or not (they decide about a boolean
state). This is used to enable/disable features, like key bindings, parts of
the layout and other stuff. For instance, we could have a HasSearch filter
attached to some part of the layout, in order to show that part of the user
interface only while the user is searching.
Filters are made to avoid having to attach callbacks to all event in order to
propagate state. However, they are lazy, they don’t automatically propagate the
state of what they are observing. Only when a filter is called (it’s actually a
callable), it will calculate its value. So, its not really reactive
programming, but it’s made to fit for this framework.
Filters can be chained using & and | operations, and inverted using the
~ operator, for instance:
filter = has_focus('default') & ~ has_selection
class prompt_toolkit.filters.Always¶
Always enable feature.
class prompt_toolkit.filters.Condition(func: Callable[[], bool])¶
Turn any callable into a Filter. The callable is supposed to not take any
arguments.
This can be used as a decorator:
@Condition
def feature_is_active():  # `feature_is_active` becomes a Filter.
return True
Parameters:
func – Callable which takes no inputs and returns a boolean.
class prompt_toolkit.filters.Filter¶
Base class for any filter to activate/deactivate a feature, depending on a
condition.
The return value of __call__ will tell if the feature should be active.
prompt_toolkit.filters.HasFocus(value: FocusableElement) → Condition¶
Enable when this buffer has the focus.
prompt_toolkit.filters.InEditingMode(editing_mode: EditingMode) → Condition¶
Check whether a given editing mode is active. (Vi or Emacs.)
class prompt_toolkit.filters.Never¶
Never enable feature.
prompt_toolkit.filters.has_focus(value: FocusableElement) → Condition¶
Enable when this buffer has the focus.
prompt_toolkit.filters.in_editing_mode(editing_mode: EditingMode) → Condition¶
Check whether a given editing mode is active. (Vi or Emacs.)
prompt_toolkit.filters.is_true(value: Filter | bool) → bool¶
Test whether value is True. In case of a Filter, call it.
Parameters:
value – Boolean or Filter instance.
prompt_toolkit.filters.to_filter(bool_or_filter: Filter | bool) → Filter¶
Accept both booleans and Filters as input and
turn it into a Filter.
class prompt_toolkit.filters.Filter
Base class for any filter to activate/deactivate a feature, depending on a
condition.
The return value of __call__ will tell if the feature should be active.
class prompt_toolkit.filters.Condition(func: Callable[[], bool])
Turn any callable into a Filter. The callable is supposed to not take any
arguments.
This can be used as a decorator:
@Condition
def feature_is_active():  # `feature_is_active` becomes a Filter.
return True
Parameters:
func – Callable which takes no inputs and returns a boolean.
prompt_toolkit.filters.utils.is_true(value: Filter | bool) → bool¶
Test whether value is True. In case of a Filter, call it.
Parameters:
value – Boolean or Filter instance.
prompt_toolkit.filters.utils.to_filter(bool_or_filter: Filter | bool) → Filter¶
Accept both booleans and Filters as input and
turn it into a Filter.
Filters that accept a Application as argument.
prompt_toolkit.filters.app.has_focus(value: FocusableElement) → Condition¶
Enable when this buffer has the focus.
prompt_toolkit.filters.app.in_editing_mode(editing_mode: EditingMode) → Condition¶
Check whether a given editing mode is active. (Vi or Emacs.)
Key binding¶
class prompt_toolkit.key_binding.ConditionalKeyBindings(key_bindings: KeyBindingsBase, filter: Filter | bool = True)¶
Wraps around a KeyBindings. Disable/enable all the key bindings according to
the given (additional) filter.:
@Condition
def setting_is_true():
return True  # or False
registry = ConditionalKeyBindings(key_bindings, setting_is_true)
When new key bindings are added to this object. They are also
enable/disabled according to the given filter.
Parameters:
registries – List of KeyBindings objects.
filter – Filter object.
class prompt_toolkit.key_binding.DynamicKeyBindings(get_key_bindings: Callable[[], KeyBindingsBase | None])¶
KeyBindings class that can dynamically returns any KeyBindings.
Parameters:
get_key_bindings – Callable that returns a KeyBindings instance.
class prompt_toolkit.key_binding.KeyBindings¶
A container for a set of key bindings.
Example usage:
kb = KeyBindings()
@kb.add('c-t')
def _(event):
print('Control-T pressed')
@kb.add('c-a', 'c-b')
def _(event):
print('Control-A pressed, followed by Control-B')
@kb.add('c-x', filter=is_searching)
def _(event):
print('Control-X pressed')  # Works only if we are searching.
add(*keys: Keys | str, filter: FilterOrBool = True, eager: FilterOrBool = False, is_global: FilterOrBool = False, save_before: Callable[[KeyPressEvent], bool] = <function KeyBindings.<lambda>>, record_in_macro: FilterOrBool = True) → Callable[[T], T]¶
Decorator for adding a key bindings.
Parameters:
filter – Filter to determine
when this key binding is active.
eager – Filter or bool.
When True, ignore potential longer matches when this key binding is
hit. E.g. when there is an active eager key binding for Ctrl-X,
execute the handler immediately and ignore the key binding for
Ctrl-X Ctrl-E of which it is a prefix.
is_global – When this key bindings is added to a Container or
Control, make it a global (always active) binding.
save_before – Callable that takes an Event and returns True if
we should save the current buffer, before handling the event.
(That’s the default.)
record_in_macro – Record these key bindings when a macro is
being recorded. (True by default.)
add_binding(*keys: Keys | str, filter: FilterOrBool = True, eager: FilterOrBool = False, is_global: FilterOrBool = False, save_before: Callable[[KeyPressEvent], bool] = <function KeyBindings.<lambda>>, record_in_macro: FilterOrBool = True) → Callable[[T], T]¶
Decorator for adding a key bindings.
Parameters:
filter – Filter to determine
when this key binding is active.
eager – Filter or bool.
When True, ignore potential longer matches when this key binding is
hit. E.g. when there is an active eager key binding for Ctrl-X,
execute the handler immediately and ignore the key binding for
Ctrl-X Ctrl-E of which it is a prefix.
is_global – When this key bindings is added to a Container or
Control, make it a global (always active) binding.
save_before – Callable that takes an Event and returns True if
we should save the current buffer, before handling the event.
(That’s the default.)
record_in_macro – Record these key bindings when a macro is
being recorded. (True by default.)
get_bindings_for_keys(keys: Tuple[Keys | str, ...]) → list[Binding]¶
Return a list of key bindings that can handle this key.
(This return also inactive bindings, so the filter still has to be
called, for checking it.)
Parameters:
keys – tuple of keys.
get_bindings_starting_with_keys(keys: Tuple[Keys | str, ...]) → list[Binding]¶
Return a list of key bindings that handle a key sequence starting with
keys. (It does only return bindings for which the sequences are
longer than keys. And like get_bindings_for_keys, it also includes
inactive bindings.)
Parameters:
keys – tuple of keys.
remove(*args: Keys | str | KeyHandlerCallable) → None¶
Remove a key binding.
This expects either a function that was given to add method as
parameter or a sequence of key bindings.
Raises ValueError when no bindings was found.
Usage:
remove(handler)  # Pass handler.
remove('c-x', 'c-a')  # Or pass the key bindings.
remove_binding(*args: Keys | str | KeyHandlerCallable) → None¶
Remove a key binding.
This expects either a function that was given to add method as
parameter or a sequence of key bindings.
Raises ValueError when no bindings was found.
Usage:
remove(handler)  # Pass handler.
remove('c-x', 'c-a')  # Or pass the key bindings.
class prompt_toolkit.key_binding.KeyBindingsBase¶
Interface for a KeyBindings.
abstract property bindings: list[Binding]¶
List of Binding objects.
(These need to be exposed, so that KeyBindings objects can be merged
together.)
abstractmethod get_bindings_for_keys(keys: Tuple[Keys | str, ...]) → list[Binding]¶
Return a list of key bindings that can handle these keys.
(This return also inactive bindings, so the filter still has to be
called, for checking it.)
Parameters:
keys – tuple of keys.
abstractmethod get_bindings_starting_with_keys(keys: Tuple[Keys | str, ...]) → list[Binding]¶
Return a list of key bindings that handle a key sequence starting with
keys. (It does only return bindings for which the sequences are
longer than keys. And like get_bindings_for_keys, it also includes
inactive bindings.)
Parameters:
keys – tuple of keys.
prompt_toolkit.key_binding.merge_key_bindings(bindings: Sequence[KeyBindingsBase]) → _MergedKeyBindings¶
Merge multiple Keybinding objects together.
Usage:
bindings = merge_key_bindings([bindings1, bindings2, ...])
Default key bindings.:
key_bindings = load_key_bindings()
app = Application(key_bindings=key_bindings)
prompt_toolkit.key_binding.defaults.load_key_bindings() → KeyBindingsBase¶
Create a KeyBindings object that contains the default key bindings.
class prompt_toolkit.key_binding.vi_state.ViState¶
Mutable class to hold the state of the Vi navigation.
property input_mode: InputMode¶
Get InputMode.
last_character_find: CharacterFind | None¶
None or CharacterFind instance. (This is used to repeat the last
search in Vi mode, by pressing the ‘n’ or ‘N’ in navigation mode.)
named_registers: dict[str, ClipboardData]¶
Named registers. Maps register name (e.g. ‘a’) to
ClipboardData instances.
reset() → None¶
Reset state, go back to the given mode. INSERT by default.
tilde_operator¶
When true, make ~ act as an operator.
waiting_for_digraph¶
Waiting for digraph.
An KeyProcessor receives callbacks for the keystrokes parsed from
the input in the InputStream instance.
The KeyProcessor will according to the implemented keybindings call the
correct callbacks when new key presses are feed through feed.
class prompt_toolkit.key_binding.key_processor.KeyPress(key: Keys | str, data: str | None = None)¶
Parameters:
key – A Keys instance or text (one character).
data – The received string on stdin. (Often vt100 escape codes.)
class prompt_toolkit.key_binding.key_processor.KeyPressEvent(key_processor_ref: ReferenceType[KeyProcessor], arg: str | None, key_sequence: list[KeyPress], previous_key_sequence: list[KeyPress], is_repeat: bool)¶
Key press event, delivered to key bindings.
Parameters:
key_processor_ref – Weak reference to the KeyProcessor.
arg – Repetition argument.
key_sequence – List of KeyPress instances.
previouskey_sequence – Previous list of KeyPress instances.
is_repeat – True when the previous event was delivered to the same handler.
property app: Application[Any]¶
The current Application object.
append_to_arg_count(data: str) → None¶
Add digit to the input argument.
Parameters:
data – the typed digit as string
property arg: int¶
Repetition argument.
property arg_present: bool¶
True if repetition argument was explicitly provided.
property cli: Application[Any]¶
For backward-compatibility.
property current_buffer: Buffer¶
The current buffer.
is_repeat¶
True when the previous key sequence was handled by the same handler.
class prompt_toolkit.key_binding.key_processor.KeyProcessor(key_bindings: KeyBindingsBase)¶
Statemachine that receives KeyPress instances and according to the
key bindings in the given KeyBindings, calls the matching handlers.
p = KeyProcessor(key_bindings)
# Send keys into the processor.
p.feed(KeyPress(Keys.ControlX, ''))
p.feed(KeyPress(Keys.ControlC, '')
# Process all the keys in the queue.
p.process_keys()
# Now the ControlX-ControlC callback will be called if this sequence is
# registered in the key bindings.
Parameters:
key_bindings – KeyBindingsBase instance.
empty_queue() → list[KeyPress]¶
Empty the input queue. Return the unprocessed input.
feed(key_press: KeyPress, first: bool = False) → None¶
Add a new KeyPress to the input queue.
(Don’t forget to call process_keys in order to process the queue.)
Parameters:
first – If true, insert before everything else.
feed_multiple(key_presses: list[KeyPress], first: bool = False) → None¶
Parameters:
first – If true, insert before everything else.
process_keys() → None¶
Process all the keys in the input_queue.
(To be called after feed.)
Note: because of the feed/process_keys separation, it is
possible to call feed from inside a key binding.
This function keeps looping until the queue is empty.
send_sigint() → None¶
Send SIGINT. Immediately call the SIGINT key handler.
Eventloop¶
prompt_toolkit.eventloop.call_soon_threadsafe(func: Callable[[], None], max_postpone_time: float | None = None, loop: AbstractEventLoop | None = None) → None¶
Wrapper around asyncio’s call_soon_threadsafe.
This takes a max_postpone_time which can be used to tune the urgency of
the method.
Asyncio runs tasks in first-in-first-out. However, this is not what we
want for the render function of the prompt_toolkit UI. Rendering is
expensive, but since the UI is invalidated very often, in some situations
we render the UI too often, so much that the rendering CPU usage slows down
the rest of the processing of the application.  (Pymux is an example where
we have to balance the CPU time spend on rendering the UI, and parsing
process output.)
However, we want to set a deadline value, for when the rendering should
happen. (The UI should stay responsive).
prompt_toolkit.eventloop.get_traceback_from_context(context: dict[str, Any]) → TracebackType | None¶
Get the traceback object from the context.
prompt_toolkit.eventloop.run_in_executor_with_context(func: Callable[[...], _T], *args: Any, loop: AbstractEventLoop | None = None) → Awaitable[_T]¶
Run a function in an executor, but make sure it uses the same contextvars.
This is required so that the function will see the right application.
See also: https://bugs.python.org/issue34014
Similar to PyOS_InputHook of the Python API, we can plug in an input hook in
the asyncio event loop.
The way this works is by using a custom ‘selector’ that runs the other event
loop until the real selector is ready.
It’s the responsibility of this event hook to return when there is input ready.
There are two ways to detect when input is ready:
The inputhook itself is a callable that receives an InputHookContext. This
callable should run the other event loop, and return when the main loop has
stuff to do. There are two ways to detect when to return:
Call the input_is_ready method periodically. Quit when this returns True.
Add the fileno as a watch to the external eventloop. Quit when file descriptor
becomes readable. (But don’t read from it.)
Note that this is not the same as checking for sys.stdin.fileno(). The
eventloop of prompt-toolkit allows thread-based executors, for example for
asynchronous autocompletion. When the completion for instance is ready, we
also want prompt-toolkit to gain control again in order to display that.
class prompt_toolkit.eventloop.inputhook.InputHookContext(fileno: int, input_is_ready: Callable[[], bool])¶
Given as a parameter to the inputhook.
class prompt_toolkit.eventloop.inputhook.InputHookSelector(selector: BaseSelector, inputhook: Callable[[InputHookContext], None])¶
Usage:
selector = selectors.SelectSelector()
loop = asyncio.SelectorEventLoop(InputHookSelector(selector, inputhook))
asyncio.set_event_loop(loop)
close() → None¶
Clean up resources.
prompt_toolkit.eventloop.inputhook.new_eventloop_with_inputhook(inputhook: Callable[[InputHookContext], None]) → AbstractEventLoop¶
Create a new event loop with the given inputhook.
prompt_toolkit.eventloop.inputhook.set_eventloop_with_inputhook(inputhook: Callable[[InputHookContext], None]) → AbstractEventLoop¶
Create a new event loop with the given inputhook, and activate it.
prompt_toolkit.eventloop.utils.call_soon_threadsafe(func: Callable[[], None], max_postpone_time: float | None = None, loop: AbstractEventLoop | None = None) → None¶
Wrapper around asyncio’s call_soon_threadsafe.
This takes a max_postpone_time which can be used to tune the urgency of
the method.
Asyncio runs tasks in first-in-first-out. However, this is not what we
want for the render function of the prompt_toolkit UI. Rendering is
expensive, but since the UI is invalidated very often, in some situations
we render the UI too often, so much that the rendering CPU usage slows down
the rest of the processing of the application.  (Pymux is an example where
we have to balance the CPU time spend on rendering the UI, and parsing
process output.)
However, we want to set a deadline value, for when the rendering should
happen. (The UI should stay responsive).
prompt_toolkit.eventloop.utils.get_traceback_from_context(context: dict[str, Any]) → TracebackType | None¶
Get the traceback object from the context.
prompt_toolkit.eventloop.utils.run_in_executor_with_context(func: Callable[[...], _T], *args: Any, loop: AbstractEventLoop | None = None) → Awaitable[_T]¶
Run a function in an executor, but make sure it uses the same contextvars.
This is required so that the function will see the right application.
See also: https://bugs.python.org/issue34014
Input¶
class prompt_toolkit.input.DummyInput¶
Input for use in a DummyApplication
If used in an actual application, it will make the application render
itself once and exit immediately, due to an EOFError.
class prompt_toolkit.input.Input¶
Abstraction for any input.
An instance of this class can be given to the constructor of a
Application and will also be
passed to the EventLoop.
abstractmethod attach(input_ready_callback: Callable[[], None]) → ContextManager[None]¶
Return a context manager that makes this input active in the current
event loop.
close() → None¶
Close input.
abstract property closed: bool¶
Should be true when the input stream is closed.
abstractmethod cooked_mode() → ContextManager[None]¶
Context manager that turns the input into cooked mode.
abstractmethod detach() → ContextManager[None]¶
Return a context manager that makes sure that this input is not active
in the current event loop.
abstractmethod fileno() → int¶
Fileno for putting this in an event loop.
flush() → None¶
The event loop can call this when the input has to be flushed.
flush_keys() → list[KeyPress]¶
Flush the underlying parser. and return the pending keys.
(Used for vt100 input.)
abstractmethod raw_mode() → ContextManager[None]¶
Context manager that turns the input into raw mode.
abstractmethod read_keys() → list[KeyPress]¶
Return a list of Key objects which are read/parsed from the input.
abstractmethod typeahead_hash() → str¶
Identifier for storing type ahead key presses.
prompt_toolkit.input.create_input(stdin: TextIO | None = None, always_prefer_tty: bool = False) → Input¶
Create the appropriate Input object for the current os/environment.
Parameters:
always_prefer_tty – When set, if sys.stdin is connected to a Unix
pipe, check whether sys.stdout or sys.stderr are connected to a
pseudo terminal. If so, open the tty for reading instead of reading for
sys.stdin. (We can open stdout or stderr for reading, this is how
a $PAGER works.)
prompt_toolkit.input.create_pipe_input() → ContextManager[PipeInput]¶
Create an input pipe.
This is mostly useful for unit testing.
Usage:
with create_pipe_input() as input:
input.send_text('inputdata')
Breaking change: In prompt_toolkit 3.0.28 and earlier, this was returning
the PipeInput directly, rather than through a context manager.
class prompt_toolkit.input.vt100.Vt100Input(stdin: TextIO)¶
Vt100 input for Posix systems.
(This uses a posix file descriptor that can be registered in the event loop.)
attach(input_ready_callback: Callable[[], None]) → ContextManager[None]¶
Return a context manager that makes this input active in the current
event loop.
detach() → ContextManager[None]¶
Return a context manager that makes sure that this input is not active
in the current event loop.
flush_keys() → list[KeyPress]¶
Flush pending keys and return them.
(Used for flushing the ‘escape’ key.)
read_keys() → list[KeyPress]¶
Read list of KeyPress.
class prompt_toolkit.input.vt100.cooked_mode(fileno: int)¶
The opposite of raw_mode, used when we need cooked mode inside a
raw_mode block.  Used in Application.run_in_terminal.:
with cooked_mode(stdin):
''' the pseudo-terminal stdin is now used in cooked mode. '''
class prompt_toolkit.input.vt100.raw_mode(fileno: int)¶
with raw_mode(stdin):
''' the pseudo-terminal stdin is now used in raw mode '''
We ignore errors when executing tcgetattr fails.
Parser for VT100 input stream.
class prompt_toolkit.input.vt100_parser.Vt100Parser(feed_key_callback: Callable[[KeyPress], None])¶
Parser for VT100 input stream.
Data can be fed through the feed method and the given callback will be
called with KeyPress objects.
def callback(key):
pass
i = Vt100Parser(callback)
i.feed('data...')
Attr feed_key_callback:
Function that will be called when a key is parsed.
feed(data: str) → None¶
Feed the input stream.
Parameters:
data – Input string (unicode).
feed_and_flush(data: str) → None¶
Wrapper around feed and flush.
flush() → None¶
Flush the buffer of the input stream.
This will allow us to handle the escape key (or maybe meta) sooner.
The input received by the escape key is actually the same as the first
characters of e.g. Arrow-Up, so without knowing what follows the escape
sequence, we don’t know whether escape has been pressed, or whether
it’s something else. This flush function should be called after a
timeout, and processes everything that’s still in the buffer as-is, so
without assuming any characters will follow.
Mappings from VT100 (ANSI) escape sequences to the corresponding prompt_toolkit
keys.
We are not using the terminfo/termcap databases to detect the ANSI escape
sequences for the input. Instead, we recognize 99% of the most common
sequences. This works well, because in practice, every modern terminal is
mostly Xterm compatible.
Some useful docs:
- Mintty: https://github.com/mintty/mintty/blob/master/wiki/Keycodes.md
Output¶
class prompt_toolkit.output.ColorDepth(value)¶
Possible color depth values for the output.
DEPTH_1_BIT = 'DEPTH_1_BIT'¶
One color only.
DEPTH_24_BIT = 'DEPTH_24_BIT'¶
24 bit True color.
DEPTH_4_BIT = 'DEPTH_4_BIT'¶
ANSI Colors.
DEPTH_8_BIT = 'DEPTH_8_BIT'¶
The default.
classmethod default() → ColorDepth¶
Return the default color depth for the default output.
classmethod from_env() → ColorDepth | None¶
Return the color depth if the $PROMPT_TOOLKIT_COLOR_DEPTH environment
variable has been set.
This is a way to enforce a certain color depth in all prompt_toolkit
applications.
class prompt_toolkit.output.DummyOutput¶
For testing. An output class that doesn’t render anything.
fileno() → int¶
There is no sensible default for fileno().
class prompt_toolkit.output.Output¶
Base class defining the output interface for a
Renderer.
Actual implementations are
Vt100_Output and
Win32Output.
ask_for_cpr() → None¶
Asks for a cursor position report (CPR).
(VT100 only.)
bell() → None¶
Sound bell.
abstractmethod clear_title() → None¶
Clear title again. (or restore previous title.)
abstractmethod cursor_backward(amount: int) → None¶
Move cursor amount place backward.
abstractmethod cursor_down(amount: int) → None¶
Move cursor amount place down.
abstractmethod cursor_forward(amount: int) → None¶
Move cursor amount place forward.
abstractmethod cursor_goto(row: int = 0, column: int = 0) → None¶
Move cursor position.
abstractmethod cursor_up(amount: int) → None¶
Move cursor amount place up.
abstractmethod disable_autowrap() → None¶
Disable auto line wrapping.
disable_bracketed_paste() → None¶
For vt100 only.
abstractmethod disable_mouse_support() → None¶
Disable mouse.
abstractmethod enable_autowrap() → None¶
Enable auto line wrapping.
enable_bracketed_paste() → None¶
For vt100 only.
abstractmethod enable_mouse_support() → None¶
Enable mouse.
abstractmethod encoding() → str¶
Return the encoding for this output, e.g. ‘utf-8’.
(This is used mainly to know which characters are supported by the
output the data, so that the UI can provide alternatives, when
required.)
abstractmethod enter_alternate_screen() → None¶
Go to the alternate screen buffer. (For full screen applications).
abstractmethod erase_down() → None¶
Erases the screen from the current line down to the bottom of the
screen.
abstractmethod erase_end_of_line() → None¶
Erases from the current cursor position to the end of the current line.
abstractmethod erase_screen() → None¶
Erases the screen with the background color and moves the cursor to
home.
abstractmethod fileno() → int¶
Return the file descriptor to which we can write for the output.
abstractmethod flush() → None¶
Write to output stream and flush.
abstractmethod get_default_color_depth() → ColorDepth¶
Get default color depth for this output.
This value will be used if no color depth was explicitly passed to the
Application.
Note
If the $PROMPT_TOOLKIT_COLOR_DEPTH environment variable has been
set, then outputs.defaults.create_output will pass this value to
the implementation as the default_color_depth, which is returned
here. (This is not used when the output corresponds to a
prompt_toolkit SSH/Telnet session.)
get_rows_below_cursor_position() → int¶
For Windows only.
abstractmethod get_size() → Size¶
Return the size of the output window.
abstractmethod hide_cursor() → None¶
Hide cursor.
abstractmethod quit_alternate_screen() → None¶
Leave the alternate screen buffer.
abstractmethod reset_attributes() → None¶
Reset color and styling attributes.
reset_cursor_key_mode() → None¶
For vt100 only.
Put the terminal in normal cursor mode (instead of application mode).
See: https://vt100.net/docs/vt100-ug/chapter3.html
abstractmethod reset_cursor_shape() → None¶
Reset cursor shape.
property responds_to_cpr: bool¶
True if the Application can expect to receive a CPR response after
calling ask_for_cpr (this will come back through the corresponding
Input).
This is used to determine the amount of available rows we have below
the cursor position. In the first place, we have this so that the drop
down autocompletion menus are sized according to the available space.
On Windows, we don’t need this, there we have
get_rows_below_cursor_position.
scroll_buffer_to_prompt() → None¶
For Win32 only.
abstractmethod set_attributes(attrs: Attrs, color_depth: ColorDepth) → None¶
Set new color and styling attributes.
abstractmethod set_cursor_shape(cursor_shape: CursorShape) → None¶
Set cursor shape to block, beam or underline.
abstractmethod set_title(title: str) → None¶
Set terminal title.
abstractmethod show_cursor() → None¶
Show cursor.
abstractmethod write(data: str) → None¶
Write text (Terminal escape sequences will be removed/escaped.)
abstractmethod write_raw(data: str) → None¶
Write text.
prompt_toolkit.output.create_output(stdout: TextIO | StdoutProxy | None = None, always_prefer_tty: bool = False) → Output¶
Return an Output instance for the command
line.
Parameters:
stdout – The stdout object
always_prefer_tty –
When set, look for sys.stderr if sys.stdout
is not a TTY. Useful if sys.stdout is redirected to a file, but we
still want user input and output on the terminal.
By default, this is False. If sys.stdout is not a terminal (maybe
it’s redirected to a file), then a PlainTextOutput will be returned.
That way, tools like print_formatted_text will write plain text into
that file.
Output for vt100 terminals.
A lot of thanks, regarding outputting of colors, goes to the Pygments project:
(We don’t rely on Pygments anymore, because many things are very custom, and
everything has been highly optimized.)
http://pygments.org/
class prompt_toolkit.output.vt100.Vt100_Output(stdout: TextIO, get_size: Callable[[], Size], term: str | None = None, default_color_depth: ColorDepth | None = None, enable_bell: bool = True, enable_cpr: bool = True)¶
Parameters:
get_size – A callable which returns the Size of the output terminal.
stdout – Any object with has a write and flush method + an ‘encoding’ property.
term – The terminal environment variable. (xterm, xterm-256color, linux, …)
enable_cpr – When True (the default), send “cursor position
request” escape sequences to the output in order to detect the cursor
position. That way, we can properly determine how much space there is
available for the UI (especially for drop down menus) to render. The
Renderer will still try to figure out whether the current terminal
does respond to CPR escapes. When False, never attempt to send CPR
requests.
ask_for_cpr() → None¶
Asks for a cursor position report (CPR).
bell() → None¶
Sound bell.
cursor_goto(row: int = 0, column: int = 0) → None¶
Move cursor position.
encoding() → str¶
Return encoding used for stdout.
erase_down() → None¶
Erases the screen from the current line down to the bottom of the
screen.
erase_end_of_line() → None¶
Erases from the current cursor position to the end of the current line.
erase_screen() → None¶
Erases the screen with the background color and moves the cursor to
home.
fileno() → int¶
Return file descriptor.
flush() → None¶
Write to output stream and flush.
classmethod from_pty(stdout: TextIO, term: str | None = None, default_color_depth: ColorDepth | None = None, enable_bell: bool = True) → Vt100_Output¶
Create an Output class from a pseudo terminal.
(This will take the dimensions by reading the pseudo
terminal attributes.)
get_default_color_depth() → ColorDepth¶
Return the default color depth for a vt100 terminal, according to the
our term value.
We prefer 256 colors almost always, because this is what most terminals
support these days, and is a good default.
reset_cursor_key_mode() → None¶
For vt100 only.
Put the terminal in cursor mode (instead of application mode).
reset_cursor_shape() → None¶
Reset cursor shape.
set_attributes(attrs: Attrs, color_depth: ColorDepth) → None¶
Create new style and output.
Parameters:
attrs – Attrs instance.
set_title(title: str) → None¶
Set terminal title.
write(data: str) → None¶
Write text to output.
(Removes vt100 escape codes. – used for safely writing text.)
write_raw(data: str) → None¶
Write raw data to output.
Data structures¶
class prompt_toolkit.layout.WindowRenderInfo(window: Window, ui_content: UIContent, horizontal_scroll: int, vertical_scroll: int, window_width: int, window_height: int, configured_scroll_offsets: ScrollOffsets, visible_line_to_row_col: dict[int, tuple[int, int]], rowcol_to_yx: dict[tuple[int, int], tuple[int, int]], x_offset: int, y_offset: int, wrap_lines: bool)¶
Render information for the last render time of this control.
It stores mapping information between the input buffers (in case of a
BufferControl) and the actual
render position on the output screen.
(Could be used for implementation of the Vi ‘H’ and ‘L’ key bindings as
well as implementing mouse support.)
Parameters:
ui_content – The original UIContent instance that contains
the whole input, without clipping. (ui_content)
horizontal_scroll – The horizontal scroll of the Window instance.
vertical_scroll – The vertical scroll of the Window instance.
window_width – The width of the window that displays the content,
without the margins.
window_height – The height of the window that displays the content.
configured_scroll_offsets – The scroll offsets as configured for the
Window instance.
visible_line_to_row_col – Mapping that maps the row numbers on the
displayed screen (starting from zero for the first visible line) to
(row, col) tuples pointing to the row and column of the UIContent.
rowcol_to_yx – Mapping that maps (row, column) tuples representing
coordinates of the UIContent to (y, x) absolute coordinates at
the rendered screen.
property applied_scroll_offsets: ScrollOffsets¶
Return a ScrollOffsets instance that indicates the actual
offset. This can be less than or equal to what’s configured. E.g, when
the cursor is completely at the top, the top offset will be zero rather
than what’s configured.
property bottom_visible: bool¶
True when the bottom of the buffer is visible.
center_visible_line(before_scroll_offset: bool = False, after_scroll_offset: bool = False) → int¶
Like first_visible_line, but for the center visible line.
property content_height: int¶
The full height of the user control.
property cursor_position: Point¶
Return the cursor position coordinates, relative to the left/top corner
of the rendered screen.
property displayed_lines: list[int]¶
List of all the visible rows. (Line numbers of the input buffer.)
The last line may not be entirely visible.
first_visible_line(after_scroll_offset: bool = False) → int¶
Return the line number (0 based) of the input document that corresponds
with the first visible line.
property full_height_visible: bool¶
True when the full height is visible (There is no vertical scroll.)
get_height_for_line(lineno: int) → int¶
Return the height of the given line.
(The height that it would take, if this line became visible.)
property input_line_to_visible_line: dict[int, int]¶
Return the dictionary mapping the line numbers of the input buffer to
the lines of the screen. When a line spans several rows at the screen,
the first row appears in the dictionary.
last_visible_line(before_scroll_offset: bool = False) → int¶
Like first_visible_line, but for the last visible line.
property top_visible: bool¶
True when the top of the buffer is visible.
property vertical_scroll_percentage: int¶
Vertical scroll as a percentage. (0 means: the top is visible,
100 means: the bottom is visible.)
class prompt_toolkit.data_structures.Point(x, y)¶
x: int¶
Alias for field number 0
y: int¶
Alias for field number 1
class prompt_toolkit.data_structures.Size(rows, columns)¶
columns: int¶
Alias for field number 1
rows: int¶
Alias for field number 0
Patch stdout¶
patch_stdout¶
This implements a context manager that ensures that print statements within
it won’t destroy the user interface. The context manager will replace
sys.stdout by something that draws the output above the current prompt,
rather than overwriting the UI.
Usage:
with patch_stdout(application):
...
application.run()
...
Multiple applications can run in the body of the context manager, one after the
other.
class prompt_toolkit.patch_stdout.StdoutProxy(sleep_between_writes: float = 0.2, raw: bool = False)¶
File-like object, which prints everything written to it, output above the
current application/prompt. This class is compatible with other file
objects and can be used as a drop-in replacement for sys.stdout or can
for instance be passed to logging.StreamHandler.
The current application, above which we print, is determined by looking
what application currently runs in the AppSession that is active during
the creation of this instance.
This class can be used as a context manager.
In order to avoid having to repaint the prompt continuously for every
little write, a short delay of sleep_between_writes seconds will be added
between writes in order to bundle many smaller writes in a short timespan.
close() → None¶
Stop StdoutProxy proxy.
This will terminate the write thread, make sure everything is flushed
and wait for the write thread to finish.
flush() → None¶
Flush buffered output.
prompt_toolkit.patch_stdout.patch_stdout(raw: bool = False) → Generator[None, None, None]¶
Replace sys.stdout by an _StdoutProxy instance.
Writing to this proxy will make sure that the text appears above the
prompt, and that it doesn’t destroy the output from the renderer.  If no
application is curring, the behavior should be identical to writing to
sys.stdout directly.
Warning: If a new event loop is installed using asyncio.set_event_loop(),
then make sure that the context manager is applied after the event loop
is changed. Printing to stdout will be scheduled in the event loop
that’s active when the context manager is created.
Parameters:
raw – (bool) When True, vt100 terminal escape sequences are not
removed/escaped.
On this page
On this page
Reference
Application
AppSession
Application
Application.cancel_and_wait_for_background_tasks()
Application.color_depth
Application.cpr_not_supported_callback()
Application.create_background_task()
Application.current_buffer
Application.current_search_state
Application.exit()
Application.get_used_style_strings()
Application.invalidate()
Application.invalidated
Application.is_running
Application.key_processor
Application.print_text()
Application.quoted_insert
Application.render_counter
Application.reset()
Application.run()
Application.run_async()
Application.run_system_command()
Application.suspend_to_background()
Application.timeoutlen
Application.ttimeoutlen
Application.vi_state
DummyApplication
create_app_session()
get_app()
get_app_or_none()
in_terminal()
run_in_terminal()
set_app()
Formatted text
ANSI
ANSI.format()
FormattedText
HTML
HTML.format()
PygmentsTokens
Template
fragment_list_len()
fragment_list_to_text()
fragment_list_width()
is_formatted_text()
merge_formatted_text()
split_lines()
to_formatted_text()
to_plain_text()
Buffer
Buffer
Buffer.append_to_history()
Buffer.apply_completion()
Buffer.apply_search()
Buffer.auto_down()
Buffer.auto_up()
Buffer.cancel_completion()
Buffer.complete_next()
Buffer.complete_previous()
Buffer.copy_selection()
Buffer.cursor_down()
Buffer.cursor_up()
Buffer.cut_selection()
Buffer.delete()
Buffer.delete_before_cursor()
Buffer.document
Buffer.document_for_search()
Buffer.get_search_position()
Buffer.go_to_completion()
Buffer.go_to_history()
Buffer.history_backward()
Buffer.history_forward()
Buffer.insert_line_above()
Buffer.insert_line_below()
Buffer.insert_text()
Buffer.is_returnable
Buffer.join_next_line()
Buffer.join_selected_lines()
Buffer.load_history_if_not_yet_loaded()
Buffer.newline()
Buffer.open_in_editor()
Buffer.paste_clipboard_data()
Buffer.reset()
Buffer.save_to_undo_stack()
Buffer.set_document()
Buffer.start_completion()
Buffer.start_history_lines_completion()
Buffer.start_selection()
Buffer.swap_characters_before_cursor()
Buffer.transform_current_line()
Buffer.transform_lines()
Buffer.transform_region()
Buffer.validate()
Buffer.validate_and_handle()
Buffer.yank_last_arg()
Buffer.yank_nth_arg()
CompletionState
CompletionState.complete_index
CompletionState.completions
CompletionState.current_completion
CompletionState.go_to_index()
CompletionState.new_text_and_position()
CompletionState.original_document
EditReadOnlyBuffer
indent()
reshape_text()
unindent()
Selection
SelectionState
SelectionType
SelectionType.BLOCK
SelectionType.CHARACTERS
SelectionType.LINES
Clipboard
Clipboard
Clipboard.get_data()
Clipboard.rotate()
Clipboard.set_data()
Clipboard.set_text()
ClipboardData
DummyClipboard
DynamicClipboard
InMemoryClipboard
PyperclipClipboard
Auto completion
CompleteEvent
CompleteEvent.completion_requested
CompleteEvent.text_inserted
Completer
Completer.get_completions()
Completer.get_completions_async()
Completion
Completion.display_meta
Completion.display_meta_text
Completion.display_text
Completion.new_completion_from_position()
ConditionalCompleter
DeduplicateCompleter
DummyCompleter
DynamicCompleter
ExecutableCompleter
FuzzyCompleter
FuzzyWordCompleter
NestedCompleter
NestedCompleter.from_nested_dict()
PathCompleter
ThreadedCompleter
ThreadedCompleter.get_completions_async()
WordCompleter
get_common_complete_suffix()
merge_completers()
Document
Document
Document.char_before_cursor
Document.current_char
Document.current_line
Document.current_line_after_cursor
Document.current_line_before_cursor
Document.cursor_position
Document.cursor_position_col
Document.cursor_position_row
Document.cut_selection()
Document.empty_line_count_at_the_end()
Document.end_of_paragraph()
Document.find()
Document.find_all()
Document.find_backwards()
Document.find_boundaries_of_current_word()
Document.find_enclosing_bracket_left()
Document.find_enclosing_bracket_right()
Document.find_matching_bracket_position()
Document.find_next_matching_line()
Document.find_next_word_beginning()
Document.find_next_word_ending()
Document.find_previous_matching_line()
Document.find_previous_word_beginning()
Document.find_previous_word_ending()
Document.find_start_of_previous_word()
Document.get_column_cursor_position()
Document.get_cursor_down_position()
Document.get_cursor_left_position()
Document.get_cursor_right_position()
Document.get_cursor_up_position()
Document.get_end_of_document_position()
Document.get_end_of_line_position()
Document.get_start_of_document_position()
Document.get_start_of_line_position()
Document.get_word_before_cursor()
Document.get_word_under_cursor()
Document.has_match_at_current_position()
Document.insert_after()
Document.insert_before()
Document.is_cursor_at_the_end
Document.is_cursor_at_the_end_of_line
Document.last_non_blank_of_current_line_position()
Document.leading_whitespace_in_current_line
Document.line_count
Document.lines
Document.lines_from_current
Document.on_first_line
Document.on_last_line
Document.paste_clipboard_data()
Document.selection
Document.selection_range()
Document.selection_range_at_line()
Document.selection_ranges()
Document.start_of_paragraph()
Document.text
Document.translate_index_to_position()
Document.translate_row_col_to_index()
Enums
DEFAULT_BUFFER
SEARCH_BUFFER
SYSTEM_BUFFER
History
DummyHistory
FileHistory
History
History.append_string()
History.get_strings()
History.load()
History.load_history_strings()
History.store_string()
InMemoryHistory
ThreadedHistory
ThreadedHistory.load()
Keys
Keys
Style
AdjustBrightnessStyleTransformation
Attrs
Attrs.bgcolor
Attrs.blink
Attrs.bold
Attrs.color
Attrs.dim
Attrs.hidden
Attrs.italic
Attrs.reverse
Attrs.strike
Attrs.underline
BaseStyle
BaseStyle.get_attrs_for_style_str()
BaseStyle.invalidation_hash()
BaseStyle.style_rules
ConditionalStyleTransformation
DummyStyle
DummyStyleTransformation
DynamicStyle
DynamicStyleTransformation
Priority
Style
Style.from_dict()
Style.get_attrs_for_style_str()
StyleTransformation
StyleTransformation.invalidation_hash()
StyleTransformation.transform_attrs()
SwapLightAndDarkStyleTransformation
SwapLightAndDarkStyleTransformation.transform_attrs()
merge_style_transformations()
merge_styles()
pygments_token_to_classname()
style_from_pygments_cls()
style_from_pygments_dict()
Shortcuts
CompleteStyle
ProgressBar
PromptSession
PromptSession.prompt()
button_dialog()
choice()
clear()
clear_title()
confirm()
create_confirm_session()
input_dialog()
message_dialog()
print_formatted_text()
progress_dialog()
prompt()
radiolist_dialog()
set_title()
yes_no_dialog()
Bar
Formatter
IterationsPerSecond
Label
Percentage
Progress
Rainbow
SpinningWheel
Text
TimeElapsed
TimeLeft
create_default_formatters()
Validation
ConditionalValidator
DummyValidator
DynamicValidator
ThreadedValidator
ThreadedValidator.validate_async()
ValidationError
Validator
Validator.from_callable()
Validator.validate()
Validator.validate_async()
Auto suggestion
AutoSuggest
AutoSuggest.get_suggestion()
AutoSuggest.get_suggestion_async()
AutoSuggestFromHistory
ConditionalAutoSuggest
DummyAutoSuggest
DynamicAutoSuggest
Suggestion
ThreadedAutoSuggest
ThreadedAutoSuggest.get_suggestion_async()
Renderer
Renderer
Renderer.clear()
Renderer.erase()
Renderer.height_is_known
Renderer.last_rendered_screen
Renderer.render()
Renderer.report_absolute_cursor_row()
Renderer.request_absolute_cursor_position()
Renderer.rows_above_layout
Renderer.wait_for_cpr_responses()
Renderer.waiting_for_cpr
print_formatted_text()
Lexers
DynamicLexer
Lexer
Lexer.invalidation_hash()
Lexer.lex_document()
PygmentsLexer
PygmentsLexer.from_filename()
PygmentsLexer.lex_document()
RegexSync
RegexSync.from_pygments_lexer_cls()
RegexSync.get_sync_start_position()
SimpleLexer
SyncFromStart
SyntaxSync
SyntaxSync.get_sync_start_position()
Layout
Command line layout definitions
The layout class itself
Layout
Layout.buffer_has_focus
Layout.current_buffer
Layout.current_control
Layout.current_window
Layout.find_all_windows()
Layout.focus()
Layout.focus_last()
Layout.focus_next()
Layout.focus_previous()
Layout.get_buffer_by_name()
Layout.get_focusable_windows()
Layout.get_parent()
Layout.get_visible_focusable_windows()
Layout.has_focus()
Layout.is_searching
Layout.previous_control
Layout.search_target_buffer_control
Layout.update_parents_relations()
Layout.walk()
Layout.walk_through_modal_area()
InvalidLayoutError
walk
Containers
Container
Container.get_children()
Container.get_key_bindings()
Container.is_modal()
Container.preferred_height()
Container.preferred_width()
Container.reset()
Container.write_to_screen()
HSplit
HSplit.write_to_screen()
VSplit
VSplit.write_to_screen()
FloatContainer
FloatContainer.preferred_height()
Float
Window
Window.preferred_height()
Window.preferred_width()
Window.write_to_screen()
WindowAlign
ConditionalContainer
DynamicContainer
ScrollablePane
ScrollablePane.write_to_screen()
ScrollOffsets
ColorColumn
to_container
to_window
is_container
HorizontalAlign
VerticalAlign
Controls
BufferControl
BufferControl.create_content()
BufferControl.get_invalidate_events()
BufferControl.get_key_bindings()
BufferControl.mouse_handler()
BufferControl.preferred_width()
BufferControl.search_state
SearchBufferControl
DummyControl
FormattedTextControl
FormattedTextControl.mouse_handler()
FormattedTextControl.preferred_height()
FormattedTextControl.preferred_width()
UIControl
UIControl.create_content()
UIControl.get_invalidate_events()
UIControl.get_key_bindings()
UIControl.is_focusable()
UIControl.mouse_handler()
UIControl.move_cursor_down()
UIControl.move_cursor_up()
UIContent
UIContent.get_height_for_line()
Other
Sizing
Dimension
Dimension.exact()
Dimension.zero()
Margins
Margin
Margin.create_margin()
Margin.get_width()
NumberedMargin
ScrollbarMargin
ConditionalMargin
PromptMargin
PromptMargin.get_width()
Completion Menus
CompletionsMenu
MultiColumnCompletionsMenu
Processors
AfterInput
AppendAutoSuggestion
BeforeInput
ConditionalProcessor
DisplayMultipleCursors
DummyProcessor
DynamicProcessor
HighlightIncrementalSearchProcessor
HighlightMatchingBracketProcessor
HighlightSearchProcessor
HighlightSelectionProcessor
PasswordProcessor
Processor
Processor.apply_transformation()
ReverseSearchProcessor
ShowArg
ShowLeadingWhiteSpaceProcessor
ShowTrailingWhiteSpaceProcessor
TabsProcessor
Transformation
TransformationInput
merge_processors()
Utils
explode_text_fragments()
Screen
Char
Screen
Screen.append_style_to_content()
Screen.cursor_positions
Screen.draw_all_floats()
Screen.draw_with_z_index()
Screen.fill_area()
Screen.get_cursor_position()
Screen.get_menu_position()
Screen.menu_positions
Screen.set_cursor_position()
Screen.set_menu_position()
Screen.show_cursor
Screen.width
Screen.zero_width_escapes
Widgets
Box
Button
Checkbox
Frame
HorizontalLine
Label
MenuContainer
RadioList
SearchToolbar
Shadow
SystemToolbar
TextArea
TextArea.accept_handler
TextArea.document
TextArea.text
VerticalLine
Filters
Always
Condition
Filter
HasFocus()
InEditingMode()
Never
has_focus()
in_editing_mode()
is_true()
to_filter()
is_true()
to_filter()
has_focus()
in_editing_mode()
Key binding
ConditionalKeyBindings
DynamicKeyBindings
KeyBindings
KeyBindings.add()
KeyBindings.add_binding()
KeyBindings.get_bindings_for_keys()
KeyBindings.get_bindings_starting_with_keys()
KeyBindings.remove()
KeyBindings.remove_binding()
KeyBindingsBase
KeyBindingsBase.bindings
KeyBindingsBase.get_bindings_for_keys()
KeyBindingsBase.get_bindings_starting_with_keys()
merge_key_bindings()
load_key_bindings()
ViState
ViState.input_mode
ViState.last_character_find
ViState.named_registers
ViState.reset()
ViState.tilde_operator
ViState.waiting_for_digraph
KeyPress
KeyPressEvent
KeyPressEvent.app
KeyPressEvent.append_to_arg_count()
KeyPressEvent.arg
KeyPressEvent.arg_present
KeyPressEvent.cli
KeyPressEvent.current_buffer
KeyPressEvent.is_repeat
KeyProcessor
KeyProcessor.empty_queue()
KeyProcessor.feed()
KeyProcessor.feed_multiple()
KeyProcessor.process_keys()
KeyProcessor.send_sigint()
Eventloop
call_soon_threadsafe()
get_traceback_from_context()
run_in_executor_with_context()
InputHookContext
InputHookSelector
InputHookSelector.close()
new_eventloop_with_inputhook()
set_eventloop_with_inputhook()
call_soon_threadsafe()
get_traceback_from_context()
run_in_executor_with_context()
Input
DummyInput
Input
Input.attach()
Input.close()
Input.closed
Input.cooked_mode()
Input.detach()
Input.fileno()
Input.flush()
Input.flush_keys()
Input.raw_mode()
Input.read_keys()
Input.typeahead_hash()
create_input()
create_pipe_input()
Vt100Input
Vt100Input.attach()
Vt100Input.detach()
Vt100Input.flush_keys()
Vt100Input.read_keys()
cooked_mode
raw_mode
Vt100Parser
Vt100Parser.feed()
Vt100Parser.feed_and_flush()
Vt100Parser.flush()
Output
ColorDepth
ColorDepth.DEPTH_1_BIT
ColorDepth.DEPTH_24_BIT
ColorDepth.DEPTH_4_BIT
ColorDepth.DEPTH_8_BIT
ColorDepth.default()
ColorDepth.from_env()
DummyOutput
DummyOutput.fileno()
Output
Output.ask_for_cpr()
Output.bell()
Output.clear_title()
Output.cursor_backward()
Output.cursor_down()
Output.cursor_forward()
Output.cursor_goto()
Output.cursor_up()
Output.disable_autowrap()
Output.disable_bracketed_paste()
Output.disable_mouse_support()
Output.enable_autowrap()
Output.enable_bracketed_paste()
Output.enable_mouse_support()
Output.encoding()
Output.enter_alternate_screen()
Output.erase_down()
Output.erase_end_of_line()
Output.erase_screen()
Output.fileno()
Output.flush()
Output.get_default_color_depth()
Output.get_rows_below_cursor_position()
Output.get_size()
Output.hide_cursor()
Output.quit_alternate_screen()
Output.reset_attributes()
Output.reset_cursor_key_mode()
Output.reset_cursor_shape()
Output.responds_to_cpr
Output.scroll_buffer_to_prompt()
Output.set_attributes()
Output.set_cursor_shape()
Output.set_title()
Output.show_cursor()
Output.write()
Output.write_raw()
create_output()
Vt100_Output
Vt100_Output.ask_for_cpr()
Vt100_Output.bell()
Vt100_Output.cursor_goto()
Vt100_Output.encoding()
Vt100_Output.erase_down()
Vt100_Output.erase_end_of_line()
Vt100_Output.erase_screen()
Vt100_Output.fileno()
Vt100_Output.flush()
Vt100_Output.from_pty()
Vt100_Output.get_default_color_depth()
Vt100_Output.reset_cursor_key_mode()
Vt100_Output.reset_cursor_shape()
Vt100_Output.set_attributes()
Vt100_Output.set_title()
Vt100_Output.write()
Vt100_Output.write_raw()
Data structures
WindowRenderInfo
WindowRenderInfo.applied_scroll_offsets
WindowRenderInfo.bottom_visible
WindowRenderInfo.center_visible_line()
WindowRenderInfo.content_height
WindowRenderInfo.cursor_position
WindowRenderInfo.displayed_lines
WindowRenderInfo.first_visible_line()
WindowRenderInfo.full_height_visible
WindowRenderInfo.get_height_for_line()
WindowRenderInfo.input_line_to_visible_line
WindowRenderInfo.last_visible_line()
WindowRenderInfo.top_visible
WindowRenderInfo.vertical_scroll_percentage
Point
Point.x
Point.y
Size
Size.columns
Size.rows
Patch stdout
patch_stdout
StdoutProxy
StdoutProxy.close()
StdoutProxy.flush()
patch_stdout()
Previous
The rendering pipeline
Next
Related projects
Documentation
Package
Repository
Issues
prompt_toolkit
2014-2024, Jonathan Slenders
Built with Sphinx 8.2.3 and Nefertiti 0.8.6
