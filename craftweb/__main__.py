"""python -m craftweb <command> [options]   (or craft-web-server.exe <command>)"""
import sys

from . import __version__

USAGE = """usage: craft-web-server [serve] [--port N]        run the server (default)
       craft-web-server manager                   open the simple control panel (install, update, check, restart)
       craft-web-server doctor                    check that everything works
       craft-web-server service install|uninstall|start|stop|restart|status
       craft-web-server supervise                 (used by the boot task) keep the server running
       craft-web-server update [options]          install / update apps (see: update --help)
       craft-web-server passwd                    set the dashboard password
       craft-web-server https [--names a,b]       create a local CA + certificate and enable HTTPS
       craft-web-server version"""


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    command = args.pop(0) if args and not args[0].startswith("-") else "serve"
    if command in ("serve", "server"):
        from .server import main as serve
        return serve(args)
    if command == "supervise":
        from .supervisor import main as supervise
        return supervise(args)
    if command == "doctor":
        from .syscheck import main as doctor
        return doctor(args)
    if command == "manager":
        from .manager import main as manager
        return manager(args)
    if command == "service":
        from .manager import service_cli
        return service_cli(args)
    if command in ("update", "updater"):
        from .updater import main as update
        return update(args)
    if command in ("passwd", "set-admin-password"):
        from .server import main as serve
        return serve(["--set-admin-password"])
    if command in ("https", "setup-https"):
        from .pki import main as https
        return https(args)
    if command in ("version", "--version"):
        print(__version__)
        return 0
    print(USAGE)
    return 0 if command in ("help", "-h", "--help") else 2


if __name__ == "__main__":
    sys.exit(main())
