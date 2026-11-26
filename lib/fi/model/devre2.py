"""F2: devre bağımlılığı (ilk yarı durumuna bağlı ikinci yarı) — ön kayıt ON_KAYIT_F2.md.

Kullanım: PYTHONPATH=lib python3 -m fi.model.devre2 gelistir | sina
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

from .. import olay_uzayi as OU
from .degerlendirme import kume_bootstrap
from .metrikler import kalibrasyon
from .yeni_gol import CIKTI, SINAMA, kayitlar

BURASI = Path(__file__).resolve().parent
GELISTIRME = ("it.2", "fr.2", "en.3", "en.4")
MARJ = {7: 0.0, 9: 0.0, 209: 0.5, 14: 1.5, 15: 2.5, 452: 0.0, 599: 0.0, 455: 0.5, 457: 0.5}
BIRL = {801: 0.0, 5: 0.0, 48: 0.0, 295: 0.0, 296: 0.0, 528: 0.0, 529: 0.0, 584: 0.0, 585: 0.0, 591: 0.0, 592: 0.0,
        586: 0.0, 587: 0.0}
U = OU.UST
_g = np.arange(U + 1)
_f = np.array([math.factorial(int(k)) for k in _g], float)


def olaylar() -> dict:
    o = {}
    for tur, t in (("marjinal", MARJ), ("birlesik", BIRL)):
        for kod, c in t.items():
            tb, _ = OU._tablo(kod, c, "", None)
            for ad, m in tb.items():
                o[f"{kod}|{ad}"] = (tur, m)
    for ad, (a, b) in {"0:0": (0, 0), "1:0": (1, 0), "0:1": (0, 1), "1:1": (1, 1)}.items():
        o[f"779|{ad}"] = ("marjinal", (OU.H1 == a) & (OU.A1 == b))
    return o


OLAYLAR = olaylar()


def _pmf(l):
    p = np.exp(-l) * l ** _g / _f
    return p / p.sum()


def nokta(k: dict) -> int | None:
    h1, a1 = k["iy_ev"], k["iy_dep"]
    if h1 is None:
        if k["ev_gol"] == 0 and k["dep_gol"] == 0:
            h1, a1 = 0, 0
        else:
            return None
    h2, a2 = k["ev_gol"] - h1, k["dep_gol"] - a1
    if min(h2, a2) < 0 or max(h1, a1, h2, a2) > U:
        return None
    return ((h1 * (U + 1) + a1) * (U + 1) + h2) * (U + 1) + a2


def dagilim(lh, la, s_ev, s_dep, beta=None) -> np.ndarray:
    p1 = np.outer(_pmf(lh * s_ev), _pmf(la * s_dep))                     # (h1, a1)
    if beta is None:
        p2 = np.outer(_pmf(lh * (1 - s_ev)), _pmf(la * (1 - s_dep)))
        return np.einsum("ij,kl->ijkl", p1, p2).ravel()
    bo, bg = beta
    out = np.zeros((U + 1,) * 4)
    for h1 in range(U + 1):
        for a1 in range(U + 1):
            d = np.sign(h1 - a1)
            fe = math.exp(bo if d > 0 else (bg if d < 0 else 0.0))
            fd = math.exp(bo if d < 0 else (bg if d > 0 else 0.0))
            out[h1, a1] = p1[h1, a1] * np.outer(_pmf(lh * (1 - s_ev) * fe), _pmf(la * (1 - s_dep) * fd))
    return (out / out.sum()).ravel()


def _hazirla(ligler) -> list[dict]:
    """Her lig için devre payları (tarih öncesi kayıtlardan) ve gözlenen nokta."""
    out = []
    for lig in ligler:
        ks = kayitlar(lig, 2.0)
        pay = [0, 0, 0, 0]
        say = {a: 0 for a in OLAYLAR}
        n = 0
        i = 0
        ks = sorted(ks, key=lambda k: k["tarih"])
        for k in ks:
            while i < len(ks) and ks[i]["tarih"] < k["tarih"]:
                q = ks[i]
                nk = nokta(q)
                if nk is not None:
                    h1 = q["iy_ev"] or 0
                    a1 = q["iy_dep"] or 0
                    pay[0] += h1; pay[1] += q["ev_gol"]; pay[2] += a1; pay[3] += q["dep_gol"]
                    for a, (_, m) in OLAYLAR.items():
                        say[a] += bool(m[nk])
                    n += 1
                i += 1
            nk = nokta(k)
            if nk is None or n < 200 or not pay[1] or not pay[3]:
                continue
            out.append({**k, "nokta": nk, "s_ev": pay[0] / pay[1], "s_dep": pay[2] / pay[3],
                        "taban": {a: (say[a] + 0.5) / (n + 1) for a in OLAYLAR}})
    return out


def beta_kestir(ks: list[dict]) -> tuple[float, float]:
    """2Y golleri ~ Poisson(λ·(1−s)·exp(β_önde·önde + β_geride·geride)); Newton."""
    X, y, off = [], [], []
    for k in ks:
        h1, a1 = OU.H1[k["nokta"]], OU.A1[k["nokta"]]
        h2, a2 = OU.H2[k["nokta"]], OU.A2[k["nokta"]]
        for g, l, s, ben, o_ in ((h2, k["lh"], k["s_ev"], h1, a1), (a2, k["la"], k["s_dep"], a1, h1)):
            X.append([1.0 if ben > o_ else 0.0, 1.0 if ben < o_ else 0.0]); y.append(g); off.append(math.log(l * (1 - s)))
    X, y, off = np.array(X), np.array(y, float), np.array(off)
    b = np.zeros(2)
    for _ in range(50):
        mu = np.exp(off + X @ b)
        H = X.T @ (mu[:, None] * X)
        gr = X.T @ (y - mu)
        d = np.linalg.solve(H, gr)
        b += d
        if np.abs(d).max() < 1e-10:
            break
    return float(b[0]), float(b[1])


def _ll(p, y):
    p = np.clip(p, 1e-15, 1 - 1e-15)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def _on_kayit():
    oz = hashlib.sha256((BURASI / "ON_KAYIT_F2.md").read_bytes()).hexdigest()
    if oz != (BURASI / "ON_KAYIT_F2.sha256").read_text().strip():
        raise RuntimeError("ön kayıt değişmiş")
    return oz


def gelistir() -> dict:
    oz = _on_kayit()
    ks = _hazirla(GELISTIRME)
    b = beta_kestir(ks)
    r = {"on_kayit_sha256": oz, "n": len(ks), "beta_onde": b[0], "beta_geride": b[1],
         "yorum": "exp(β): öndeki takımın 2Y hız çarpanı / gerideki takımınki (eşit durum = 1)",
         "carpanlar": {"onde": math.exp(b[0]), "geride": math.exp(b[1])}}
    (CIKTI / "f2_gelistirme.json").write_text(json.dumps(r, indent=1))
    return r


def sina() -> dict:
    oz = _on_kayit()
    b = json.loads((CIKTI / "f2_gelistirme.json").read_text())
    beta = (b["beta_onde"], b["beta_geride"])
    ks = _hazirla(SINAMA)
    def sez(t):
        d = date.fromisoformat(t); return str(d.year if d.month >= 7 else d.year - 1)
    kume = [f"{k['lig']}|{sez(k['tarih'])}" for k in ks]
    P0 = [dagilim(k["lh"], k["la"], k["s_ev"], k["s_dep"]) for k in ks]
    P1 = [dagilim(k["lh"], k["la"], k["s_ev"], k["s_dep"], beta) for k in ks]
    out = {}
    for a, (tur, m) in OLAYLAR.items():
        y = np.array([float(m[k["nokta"]]) for k in ks])
        p0 = np.array([p[m].sum() for p in P0]); p1 = np.array([p[m].sum() for p in P1])
        pt = np.array([k["taban"][a] for k in ks])
        kal = kalibrasyon(p1, y, 10)
        sapma = [x for x in kal["kutular"] if x["n"] >= 30 and abs(x["ort_tahmin"] - x["gerceklesen"]) > 0.05]
        kucuk = [x for x in kal["kutular"] if x["n"] < 30]
        lig_ece = {lg: kalibrasyon(p1[np.array([k["lig"] == lg for k in ks])], y[np.array([k["lig"] == lg for k in ks])],
                                   10)["ece"] for lg in SINAMA if any(k["lig"] == lg for k in ks)}
        bt = kume_bootstrap(_ll(p1, y) - _ll(pt, y), kume)
        b0 = kume_bootstrap(_ll(p1, y) - _ll(p0, y), kume)
        g1 = kume_bootstrap(y - p1, kume); g0 = kume_bootstrap(y - p0, kume)
        oran = float(y.mean())
        r = {"tur": tur, "olay_orani": round(oran, 4), "F1_eksi_taban": bt, "F1_eksi_F0": b0,
             "gerceklesen_eksi_tahmin_F1": g1, "gerceklesen_eksi_tahmin_F0": g0, "ece_F1": kal["ece"],
             "ece_F0": kalibrasyon(p0, y, 10)["ece"], "lig_ece_F1": lig_ece, "buyuk_sapma": sapma}
        if 0.02 <= oran <= 0.98:
            r["bilgi_tasiyor"] = bt["ust95"] < 0
            r["kalibre"] = (kal["ece"] <= 0.02 and not sapma and all(v <= 0.04 for v in lig_ece.values())
                            and not (oran < 0.05 and kucuk))
            r["iyilesme_F0"] = b0["ust95"] < 0
            r["bagimlilik_aciklandi"] = (g1["alt95"] <= 0 <= g1["ust95"]) if tur == "birlesik" else None
            r["gunluk_kapsam"] = r["bilgi_tasiyor"] and r["kalibre"] and (tur == "marjinal" or r["bagimlilik_aciklandi"])
        else:
            r["karar"] = "yetersiz olay"
        out[a] = r
    a1 = np.array([bool(OLAYLAR["452|Var"][1][k["nokta"]]) for k in ks]); c1 = np.array([bool(OLAYLAR["599|Var"][1][k["nokta"]]) for k in ks])
    def oo(p11, p10, p01, p00):
        return p11 * p00 / (p10 * p01)
    mm = {x: [float(np.mean([p[OLAYLAR[f"801|{x}"][1]].sum() for p in P])) for P in (P0, P1)] for x in
          ("Evet/Evet", "Evet/Hayır", "Hayır/Evet", "Hayır/Hayır")}
    sonuc = {"asama": "F2-sinama", "on_kayit_sha256": oz, "beta": beta, "mac": len(ks),
             "lig_mac": {lg: sum(1 for k in ks if k["lig"] == lg) for lg in SINAMA},
             "KG1_KG2_olasilik_orani": {"gozlenen": oo((a1 & c1).mean(), (a1 & ~c1).mean(), (~a1 & c1).mean(), (~a1 & ~c1).mean()),
                                        "F0": oo(*[mm[x][0] for x in mm]), "F1": oo(*[mm[x][1] for x in mm])},
             "marketler": out, "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    cik = CIKTI / f"f2_sinama_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    cik.mkdir(parents=True, exist_ok=True)
    (cik / "sonuc.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=float))
    print(cik / "sonuc.json")
    return sonuc


if __name__ == "__main__":
    print(json.dumps(gelistir() if sys.argv[1:] == ["gelistir"] else sina(), indent=1, default=float)[:1500])
