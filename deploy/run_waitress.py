import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _setup_logs(repo_root: str) -> None:
    logs_dir = os.path.join(repo_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    server_log = os.path.join(logs_dir, "server.log")
    stdout_log = os.path.join(logs_dir, "server.out.log")
    stderr_log = os.path.join(logs_dir, "server.err.log")

    sys.stdout = open(stdout_log, "a", encoding="utf-8", buffering=1)
    sys.stderr = open(stderr_log, "a", encoding="utf-8", buffering=1)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = RotatingFileHandler(
        server_log,
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)

    logging.captureWarnings(True)


def main() -> int:
    repo_root = _repo_root()
    os.chdir(repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    _setup_logs(repo_root)

    import config
    from app import create_app

    host = getattr(config, "HOST", "0.0.0.0")
    port = int(getattr(config, "PORT", 5000))

    app = create_app()

    from waitress import serve

    threads_env = os.environ.get("WAITRESS_THREADS", "").strip()
    threads = 4
    if threads_env:
        try:
            threads = int(threads_env)
        except ValueError:
            threads = 4
    if threads < 1:
        threads = 1
    if threads > 32:
        threads = 32

    serve(app, host=host, port=port, threads=threads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

