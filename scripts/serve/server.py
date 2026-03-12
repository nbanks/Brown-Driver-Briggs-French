#!/usr/bin/env python3
"""BDB Review Server — lightweight review UI for BDB French translations."""

import argparse
import os
import socket
import sys
from http.server import HTTPServer

# Ensure project root is on path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts'))

from serve.handler import ReviewHandler


class DualStackHTTPServer(HTTPServer):
    """HTTPServer that picks AF_INET6 for IPv6 addresses like '::'."""

    def server_bind(self):
        # Enable dual-stack (IPv4+IPv6) when binding to ::
        if self.address_family == socket.AF_INET6:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def _make_server(host, port, handler):
    """Create an HTTPServer, using AF_INET6 when the host is an IPv6 address."""
    # Resolve the address family from the host string
    infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    if not infos:
        raise ValueError(f'Cannot resolve host: {host}')
    family = infos[0][0]
    DualStackHTTPServer.address_family = family
    return DualStackHTTPServer((host, port), handler)


def main():
    parser = argparse.ArgumentParser(description='BDB Review Server')
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='Port to listen on (default: 8080)')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Host to bind to (default: 127.0.0.1). '
                             'Use 0.0.0.0 for all IPv4, :: for all IPv4+IPv6')
    args = parser.parse_args()

    # Store project root on the handler class so all instances can access it
    ReviewHandler.project_root = PROJECT_ROOT

    server = _make_server(args.host, args.port, ReviewHandler)
    if args.host in ('127.0.0.1', '::1'):
        display_host = 'localhost'
    elif ':' in args.host:
        display_host = f'[{args.host}]'
    else:
        display_host = args.host
    print(f'BDB Review Server running at http://{display_host}:{args.port}/')
    print(f'Project root: {PROJECT_ROOT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down.')
        server.server_close()


if __name__ == '__main__':
    main()
