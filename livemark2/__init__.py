#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Livemark2 realtime markdown preview library."""

__author__ = """Hiroyuki Takagi"""
__email__ = 'miyako.dev@gmail.com'
__version__ = '0.0.1'

import json
import asyncio
from typing import Any
from typing import TYPE_CHECKING

from pygments.styles import STYLE_MAP  # type: ignore
from pygments.formatters import HtmlFormatter  # type: ignore

from wdom.options import config, parser, parse_command_line  # noqa: F401
from wdom.themes import default  # noqa: E402
from wdom.themes.default import Div, Style, H2, Script, RawHtmlNode  # noqa
from wdom.document import get_document  # noqa: F401
from wdom.server import start_server, add_static_path  # noqa: F401

from livemark2.converter import convert  # noqa: F401

if TYPE_CHECKING:
    from typing import List  # noqa: F401

parser.add_argument('--vim-port', default=8090, type=int)
parser.add_argument('--highlight-theme', default='default', type=str)
parse_command_line()


class SocketListener(asyncio.Protocol):
    pass


class Preview(Div):
    """Preview Window Class."""

    move_cmd = {
        'top': 'window.scrollTo(0, 0)',
        'bottom': 'window.scrollTo(0, document.body.getClientRects()[0].height)',  # noqa
        'page_up': 'window.scrollBy(0, - window.innerHeight * 0.9)',
        'page_down': 'window.scrollBy(0, window.innerHeight * 0.9)',
        'half_up': 'window.scrollBy(0, - window.innerHeight * 0.45)',
        'half_down': 'window.scrollBy(0, window.innerHeight * 0.45)',
        'up': 'window.scrollBy(0, -50)',
        'down': 'window.scrollBy(0, 50)',
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tlist = []  # type: List[str]
        self.current_view = H2('LiveMark is running...', parent=self)

    def data_received(self, data: dict) -> None:
        line = data['line']
        event = data['event']
        if event == 'update':
            self.tlist = data['text']
            self.update_preview(line)
        elif event == 'move':
            self.move(data['command'].lower())
        else:
            raise ValueError('Get unknown event: {}'.format(event))

    def update_preview(self, line: int) -> None:
        html = self.convert_to_html(self.tlist)
        self.mount_html(html)

    def convert_to_html(self, tlist: list) -> str:
        md = '\n'.join(tlist)
        return convert(md)

    def mount_html(self, html: str) -> None:
        old_view = self.current_view
        self.current_view = RawHtmlNode(html)
        self.replaceChild(self.current_view, old_view)

    def move(self, cmd: str) -> None:  # noqa: C901
        js = self.move_cmd.get(cmd)
        if js is not None:
            self.exec(js)


class SocketServer(object):
    def __init__(self, address: str = 'localhost', port: int = 8090,
                 loop: asyncio.AbstractEventLoop = None,
                 preview: Div = None) -> None:
        self.address = address
        self.port = port
        self.loop = loop or asyncio.get_event_loop()
        self.preview = preview or Preview()

        self.listener = SocketListener
        self.listener.connection_made = self.connection_made  # type: ignore
        self.listener.data_received = self.data_received  # type: ignore

    def start(self) -> asyncio.Future:
        self.coro_server = self.loop.create_server(self.listener, self.address,
                                                   self.port)
        self.server_task = self.loop.run_until_complete(self.coro_server)
        return self.server_task

    def stop(self) -> None:
        self.server_task.close()

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport

    def data_received(self, data: bytes) -> None:
        self.transport.close()
        msg = json.loads(data.decode())[1]
        self.preview.data_received(msg)


def main() -> None:
    doc = get_document()
    doc.register_theme(default)
    doc.title = 'LiveMark'

    # choices arg is better, but detecting error is not easy in livemark.vim
    if config.highlight_theme in STYLE_MAP:
        pygments_style = HtmlFormatter(
            style=config.highlight_theme).get_style_defs()
    else:
        pygments_style = HtmlFormatter('default').get_style_defs()
    doc.head.appendChild(Style(pygments_style))

    preview = Preview(style='padding: 3rem 10vw;')
    doc.body.appendChild(preview)
    web_server = start_server()

    loop = asyncio.get_event_loop()
    sock_server = SocketServer(port=config.vim_port, loop=loop,
                               preview=preview)
    try:
        sock_server.start()
        loop.run_forever()
    except KeyboardInterrupt:
        sock_server.stop()
        web_server.stop()
