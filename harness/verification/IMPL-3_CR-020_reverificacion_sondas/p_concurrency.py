"""Concurrency: unlocked readers vs locked appenders; 6-process start race; dedup recheck. argv: workroot"""
import multiprocessing as mp
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

ROOT = Path(sys.argv[1])
LINE = int(sys.argv[2]) if len(sys.argv) > 2 else 5000     # tamaño del relleno (5000 = líneas grandes; 150 = realistas)
NLINES = int(sys.argv[3]) if len(sys.argv) > 3 else 300


def writer(path, dec, n, stop):
    reg = C.ExperimentRegistry(path, dec)
    for i in range(n):
        reg.create(f"EXP-{2000 + i:04d}", "t" * LINE, actor="o")    # ~5 KB lines: cross page boundaries
    stop.value = 1


def reader(path, dec, stop, q, work):
    reg = C.ExperimentRegistry(path, dec)
    reads = corrupt = denied = delivered = 0
    msgs = set()
    while not stop.value:
        try:
            reg.records()
            reads += 1
        except C.X.RegistryCorruptError as exc:
            corrupt += 1
            msgs.add(str(exc)[:400])
        res = C.gate(reg, work, "EXP-0101", "A")[0]
        if res == "DELIVERED":
            delivered += 1
        else:
            denied += 1
            msgs.add(res[:600])
    q.put((reads, corrupt, delivered, denied, sorted(msgs)[:4]))


if __name__ == "__main__":
    w = ROOT / "torn"
    reg = C.new_reg(w)
    fz = C.D.frozen(reg)
    fz.begin_evaluation("A", registry=reg)              # certified pair: gate should always deliver
    stop, q = mp.Value("i", 0), mp.Queue()
    rs = [mp.Process(target=reader, args=(reg.path, reg.decisions_dir, stop, q, w)) for _ in range(3)]
    for p in rs:
        p.start()
    t0 = time.time()
    wp = mp.Process(target=writer, args=(reg.path, reg.decisions_dir, NLINES, stop))
    wp.start(); wp.join()
    for p in rs:
        p.join()
    print(f"writer appended {NLINES} lines in {time.time() - t0:.1f}s")
    for _ in rs:
        print("reader: reads=%d corrupt=%d gate delivered=%d denied=%d msgs=%s" % q.get())
    print("final registry readable:", len(reg.records()), "records; gate:", C.gate(reg, w)[0])
