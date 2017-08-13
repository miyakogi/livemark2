#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import misaka as m
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, PythonLexer


class HighlighterRenderer(m.HtmlRenderer):
    """Highlight fenced-code block."""

    def blockcode(self, text: str, lang: str) -> str:
        if not lang:
            return '\n<pre><code>{}</code></pre>\n'.format(text)
        else:
            lexer = get_lexer_by_name(lang, stripall=True)
            lexer = PythonLexer()
            formatter = HtmlFormatter()
            html = highlight(text, lexer, formatter)
            return html


convert = m.Markdown(HighlighterRenderer(), extensions=(
    'fenced-code', 'tables',
))
