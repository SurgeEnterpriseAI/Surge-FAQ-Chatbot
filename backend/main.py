from backend.bootstrap import bootstrap

bootstrap()

import os
import socket
import sys
import time

import uvicorn

# Command-line fragments that identify another run of *this* server. Used to
# decide whether a process squatting on our port is ours to reclaim.
_OWN_SERVER_MARKERS = ("backend.main", "backend.app")


def _port_is_free(host: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("" if host == "0.0.0.0" else host, port))
        except OSError:
            return False
    return True


def _listener_on(port: int):
    """Return the psutil.Process listening on ``port``, or None.

    Returns None rather than raising when psutil is unavailable or the platform
    withholds connection details — the caller then just reports the conflict.
    """
    try:
        import psutil
    except ImportError:
        return None

    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.status != psutil.CONN_LISTEN or conn.laddr.port != port:
                continue
            if conn.pid in (None, os.getpid()):
                continue
            try:
                return psutil.Process(conn.pid)
            except psutil.NoSuchProcess:
                return None
    except (psutil.AccessDenied, OSError):
        return None
    return None


def _is_our_server(proc) -> bool:
    """True when ``proc`` is another instance of this application.

    Deliberately strict: an unrelated program on the port must never be killed,
    so both the interpreter and the module being run have to match.
    """
    try:
        name = (proc.name() or "").lower()
        cmdline = " ".join(proc.cmdline())
    except Exception:
        return False

    if "python" not in name:
        return False
    return any(marker in cmdline for marker in _OWN_SERVER_MARKERS)


def _reclaim_port(host: str, port: int) -> bool:
    """Stop an orphaned copy of this server that still holds ``port``.

    Closing the terminal without Ctrl+C leaves the previous run alive and bound,
    so the next start fails with WinError 10048. Returns True when the port was
    freed.
    """
    proc = _listener_on(port)
    if proc is None:
        print(
            f"ERROR: port {port} is in use and the owning process could not be identified.\n"
            f"  Find it:  netstat -ano | findstr :{port}\n"
            f"  Stop it:  taskkill /PID <pid> /F\n"
            f"  Or pick another port:  $env:API_PORT={port + 1}",
            file=sys.stderr,
        )
        return False

    if not _is_our_server(proc):
        print(
            f"ERROR: port {port} is held by PID {proc.pid} ({proc.name()}), which is not this server.\n"
            f"  Stop that program, or start on another port:  $env:API_PORT={port + 1}",
            file=sys.stderr,
        )
        return False

    print(f"Port {port} is held by an earlier run of this server (PID {proc.pid}); stopping it.")
    try:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
            proc.wait(timeout=5)
    except Exception as e:
        print(f"ERROR: could not stop PID {proc.pid}: {e}", file=sys.stderr)
        return False

    # The socket lingers briefly after the process dies.
    for _ in range(20):
        if _port_is_free(host, port):
            return True
        time.sleep(0.25)

    print(f"ERROR: PID {proc.pid} was stopped but port {port} is still busy.", file=sys.stderr)
    return False


def main() -> None:
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8001"))
    reclaim = os.environ.get("API_PORT_RECLAIM", "0").lower() not in ("0", "false", "no")

    if not _port_is_free(host, port):
        if not reclaim:
            print(
                f"ERROR: port {port} is already in use.\n"
                f"  If this is an orphaned run of this server (terminal closed without Ctrl+C), "
                f"opt in to auto-reclaim:  $env:API_PORT_RECLAIM=1\n"
                f"  Otherwise, stop the process holding the port or pick another one:  $env:API_PORT={port + 1}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        if not _reclaim_port(host, port):
            raise SystemExit(1)

    # On Windows uvicorn would otherwise build a ProactorEventLoop, which
    # psycopg cannot use — see backend.bootstrap.selector_event_loop.
    loop = "backend.bootstrap:selector_event_loop" if sys.platform == "win32" else "asyncio"

    uvicorn.run("backend.app:app", host=host, port=port, loop=loop)


if __name__ == "__main__":
    main()
