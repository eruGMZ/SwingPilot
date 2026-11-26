"""CR-023 B7.4b — velas sintéticas SELLADAS para la snapshot de evaluación (sin datos reales).

Sustituye al `Fake` de B5 SOLO como fuente de la descarga: las velas atraviesan el constructor real de snapshots
(digest canónico, sellado, manifiesto), el consumo real y `load_final`. No hay sustitución de datos posterior a
la carga. Modo "favorable": ciclos de 2 velas (señal plana + entrada que toca el TP de `Logic`), ~1 operación por
ciclo; modo "calm": todas planas (ninguna operación cerrada → P15 insuficiente)."""
import urllib.parse

import pytest

import test_cr023_b5_evaluation_snapshot as B5
from swingpilot.research.snapshot import interval_ms

TAPE = {"mode": "favorable"}


class TapeFake(B5.Fake):
    def __call__(self, url):
        u = urllib.parse.urlparse(url)
        q = dict(urllib.parse.parse_qsl(u.query))
        if u.path == "/api/v3/time":
            return {"serverTime": self.server}
        self.calls += 1
        step = interval_ms(q["interval"])
        t = max((int(q["startTime"]) + step - 1) // step * step, B5.START)
        end, rows = int(q.get("endTime", self.server)), []
        while t <= min(end, self.server) and len(rows) < int(q["limit"]):
            n = t // step
            if TAPE["mode"] == "favorable" and n % 2 == 1:
                k = n // 2
                o, h, lo, c = 100.0, 104.0 + 2 * (k % 2), (94.0 if k % 5 == 4 else 99.5), 100.0
            else:
                o, h, lo, c = 100.0, 101.0, 99.0, 100.0
            rows.append([t, str(o), str(h), str(lo), str(c), "3.5", t + step - 1, "0", 1, "0", "0", "0"])
            t += step
        return rows


@pytest.fixture(autouse=True)
def favorable_tape(monkeypatch):
    TAPE["mode"] = "favorable"
    monkeypatch.setattr(B5, "Fake", TapeFake)
    yield TAPE
    TAPE["mode"] = "favorable"
