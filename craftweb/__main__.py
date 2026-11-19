"""python -m craftweb <serve|update|passwd|version> [options]"""
import sys

from . import __version__

USAGE = """usage: craft-web-server [serve] [--port N]        run the server (default)
       craft-web-server update [options]          install / update apps (see: update --help)
       craft-web-server passwd                    set the dashboard password
       craft-web-server version"""


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    command = args.pop(0) if args and not args[0].startswith("-") else "serve"
    if command in ("serve", "server"):
        from .server import main as serve
        return serve(args)
    if command in ("update", "updater"):
        from .updater import main as update
        return update(args)
    if command in ("passwd", "set-admin-password"):
        from .server import main as serve
        return serve(["--set-admin-password"])
    if command in ("version", "--version"):
        print(__version__)
        return 0
    print(USAGE)
    return 0 if command in ("help", "-h", "--help") else 2


if __name__ == "__main__":
    sys.exit(main())
