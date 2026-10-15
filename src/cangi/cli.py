import argparse
import logging
import signal
import sys
import threading

from .app import Pipeline
from .demo import demo_diagnoser


def _chat_client():
    from .guide import LLMConfig, LLMError, OpenAICompatClient
    try:
        config = LLMConfig.from_env()
    except LLMError as exc:
        sys.exit("error: %s" % exc)
    logging.getLogger("cangi").info("guide enabled, model %s", config.model)
    return OpenAICompatClient(config)


def _run(args) -> None:
    pipeline = Pipeline(
        host=args.host, port=args.port,
        qcad_in=args.qcad_in, qcad_out=args.qcad_out,
        chat=_chat_client() if args.guide else None,
        diagnoser=demo_diagnoser if args.demo else None,
        on_event=(lambda e: print(e.to_json(), flush=True)) if args.echo else None)
    pipeline.start()
    host, port = pipeline.hub.address
    logging.getLogger("cangi").info("listening on %s:%d", host, port)
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    stop.wait()
    pipeline.stop()


def _bench(_args) -> None:
    from .bench import main
    main()


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="cangi")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="receive plugin events and send overlay frames")
    r.add_argument("--host", default="127.0.0.1")
    r.add_argument("--port", type=int, default=8765)
    r.add_argument("--qcad-in", help="JSONL file written by the QCAD plugin")
    r.add_argument("--qcad-out", help="frame file read by the QCAD plugin")
    r.add_argument("--demo", action="store_true", help="show a fixed overlay on every object change")
    r.add_argument("--guide", action="store_true", help="enable the LLM guide (needs CANGI_LLM_API_KEY)")
    r.add_argument("--echo", action="store_true", help="print normalized events")
    r.add_argument("--log-level", default="INFO")
    r.set_defaults(func=_run)

    b = sub.add_parser("bench", help="measure bus latency")
    b.set_defaults(func=_bench)

    args = p.parse_args(argv)
    logging.basicConfig(level=getattr(args, "log_level", "INFO"), format="%(levelname)s %(name)s: %(message)s")
    args.func(args)
