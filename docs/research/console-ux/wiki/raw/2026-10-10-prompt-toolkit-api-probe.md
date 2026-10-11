Source: Installed prompt_toolkit public API inspection
Fetched: 2026-10-10
Description: Verify project dependency API availability without modifying CTK


Installed version: 3.0.53

PromptSession.bottom_toolbar: available; default=None

PromptSession.refresh_interval: available; default=0

PromptSession.auto_suggest: available; default=None

PromptSession.mouse_support: available; default=False

PromptSession.editing_mode: available; default=<EditingMode.EMACS: 'EMACS'>

Application.full_screen: available; default=False

Application.refresh_interval: available; default=None

Application.mouse_support: available; default=False

MenuContainer: (body: 'AnyContainer', menu_items: 'list[MenuItem]', floats: 'list[Float] | None' = None, key_bindings: 'KeyBindingsBase | None' = None) -> 'None'

MenuItem: (text: 'str' = '', handler: 'Callable[[], None] | None' = None, children: 'list[MenuItem] | None' = None, shortcut: 'Sequence[Keys | str] | None' = None, disabled: 'bool' = False) -> 'None'

TextArea: (text: 'str' = '', multiline: 'FilterOrBool' = True, password: 'FilterOrBool' = False, lexer: 'Lexer | None' = None, auto_suggest: 'AutoSuggest | None' = None, completer: 'Completer | None' = None, complete_while_typing: 'FilterOrBool' = True, validator: 'Validator | None' = None, accept_handler: 'BufferAcceptHandler | None' = None, history: 'History | None' = None, focusable: 'FilterOrBool' = True, focus_on_click: 'FilterOrBool' = False, wrap_lines: 'FilterOrBool' = True, read_only: 'FilterOrBool' = False, width: 'AnyDimension' = None, height: 'AnyDimension' = None, dont_extend_height: 'FilterOrBool' = False, dont_extend_width: 'FilterOrBool' = False, line_numbers: 'bool' = False, get_line_prefix: 'GetLinePrefixCallable | None' = None, scrollbar: 'bool' = False, style: 'str' = '', search_field: 'SearchToolbar | None' = None, preview_search: 'FilterOrBool' = True, prompt: 'AnyFormattedText' = '', input_processors: 'list[Processor] | None' = None, name: 'str' = '') -> 'None'

ConditionalContainer: (content: 'AnyContainer', filter: 'FilterOrBool', alternative_content: 'AnyContainer | None' = None) -> 'None'

patch_stdout: (raw: 'bool' = False) -> 'Generator[None, None, None]'
