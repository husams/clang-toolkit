from __future__ import annotations

from clang_toolkit.cli.highlight import highlight


def styles(text: str) -> dict[str, str]:
    return {frag: style for style, frag in highlight(text) if frag.strip()}


def test_fragments_cover_input():
    text = 'let m = callExpr(hasName("f")).bind("c")'
    assert "".join(frag for _, frag in highlight(text)) == text


def test_token_classes():
    s = styles('match callExpr(hasName("f"), 3).bind("c")')
    assert s["match"] == "class:keyword"
    assert s["callExpr"] == "class:matcher"
    assert s["hasName"] == "class:matcher"
    assert s['"f"'] == "class:string"
    assert s["3"] == "class:number"
    assert s[".bind"] == "class:bind"


def test_reference():
    s = styles("cfg $fn.body")
    assert s["cfg"] == "class:keyword"
    assert s["$"] == s["fn"] == s["."] == s["body"] == "class:reference"


def test_bad_input_marked_as_error():
    frags = highlight("match foo(@bar")
    assert ("class:error", "@") in frags
    assert "".join(fragment for _, fragment in frags) == "match foo(@bar"


def test_partial_quoted_string_keeps_string_colour():
    text = 'match hasName("brackets ([{ and an escaped \\" quote'
    fragments = highlight(text)
    assert fragments[-1] == ("class:string", text[text.index('"') :])
    assert "".join(fragment for _, fragment in fragments) == text


def test_multiline_document_keeps_string_and_reference_context():
    from prompt_toolkit.document import Document
    from clang_toolkit.cli.highlight import ReplLexer

    text = 'match hasName("first\n([{last")'
    get_line = ReplLexer().lex_document(Document(text))
    assert ("class:string", '"first') in get_line(0)
    assert ("class:string", '([{last"') in get_line(1)
    assert get_line(-1) == get_line(2) == []
    assert "\n".join("".join(t for _, t in get_line(i)) for i in range(2)) == text
    get_line = ReplLexer().lex_document(Document("cfg $fn\n .body"))
    assert ("class:reference", "body") in get_line(1)


def test_matcher_name_before_newline_and_parenthesis():
    from prompt_toolkit.document import Document
    from clang_toolkit.cli.highlight import ReplLexer

    get_line = ReplLexer().lex_document(Document("match functionDecl\n()"))
    assert ("class:matcher", "functionDecl") in get_line(0)


def test_distinct_values_and_keyword_boundaries():
    s = styles("let matchFoo = matcher(1e3, '[value]').bind(\"fn\")")
    assert s["matchFoo"] == "class:variable"
    assert s["1e3"] == "class:number"
    assert s["'[value]'"] == "class:string"
    assert s["matcher"] == "class:matcher"


def test_every_console_keyword_is_coloured():
    for word in ("help", "quit", "exit", "traverse", "script", "callgraph"):
        assert styles(word)[word] == "class:keyword"


def test_runtime_keywords_and_boolean_value_colours():
    s = styles("foreach $x in $items do true done")
    assert s["foreach"] == "class:keyword"
    assert s["do"] == "class:keyword"
    assert styles("print true")["print"] == "class:keyword"
    assert s["true"] == "class:value"


def test_multiline_foreach_done_remains_coloured_after_newline_comment():
    text = 'foreach $m in $xs do $m\n# comment\ndone'
    fragments = highlight(text)

    assert "".join(fragment for _, fragment in fragments) == text
    assert ("class:keyword", "done") in fragments
    assert ("", "# comment") in fragments
