import argparse
import time

from cangi.bus import EventBus
from cangi.ingest import FileTailIngest, TcpIngest

p = argparse.ArgumentParser()
p.add_argument("--port", type=int, default=8765)
p.add_argument("--qcad-file", default="/tmp/cangi_qcad.jsonl")
args = p.parse_args()

bus = EventBus()
bus.subscribe(lambda e: print(e.to_json(), flush=True))
bus.start()
TcpIngest(bus, port=args.port).start()
FileTailIngest(bus, "qcad", args.qcad_file).start()
print("listening on tcp %d, tailing %s" % (args.port, args.qcad_file), flush=True)
while True:
    time.sleep(1)
