"""E2: yeni gol modeli adayları, geliştirmede seçim, ayrı liglerde tek sınama (ön kayıt: ON_KAYIT_E2.md).

Kullanım:
  PYTHONPATH=lib python3 -m fi.model.yeni_gol gelistir      # kayıt üretimi + seçim (yalnızca geliştirme ligleri)
  PYTHONPATH=lib python3 -m fi.model.yeni_gol sina          # seçilen adayı sınama liglerinde BİR KEZ değerlendirir
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from .backtest import yuruyen_test
from .degerlendirme import kume_bootstrap
from .goller import GolModeli, skor_matrisi
from .metrikler import kalibrasyon
from .pazar_modelleri import OLAYLAR, MatrisKaydedici, gozlenen, market_olasiliklari, tutarlilik_denetimi

BURASI = Path(__file__).resolve().parent
CIKTI = BURASI.parents[2] / "output" / "model"
KAYIT = CIKTI / "e2_kayit"
GELISTIRME = ("fr.1", "nl.1", "pt.1", "de.2", "es.2")
SINAMA = ("en.2", "at.1", "be.1", "sco.1", "tr.1", "gr.1")
BASLANGIC = "2019-07-01"
CEZALAR = (2.0, 4.0, 8.0, 16.0)
W = tuple(round(0.30 + 0.05 * i, 2) for i in range(15))
B = (-0.06, -0.04, -0.02, 0.0, 0.02, 0.04, 0.06)
R = (5.0, 10.0, 20.0, 40.0)
GOL_MARKETLERI = ("AU0.5_ust", "AU1.5_ust", "AU2.5_ust", "AU3.5_ust", "AU4.5_ust", "KG_var",
                  "aralik_0_1", "aralik_2_3", "aralik_4_5", "aralik_6p")
MS = ("MS_1", "MS_X", "MS_2")
_g = np.arange(11)
_lf = np.array([math.lgamma(k + 1) for k in _g])


def on_kayit_dogrula() -> str:
    oz = hashlib.sha256((BURASI / "ON_KAYIT_E2.md").read_bytes()).hexdigest()
    if oz != (BURASI / "ON_KAYIT_E2.sha256").read_text().strip():
        raise RuntimeError("ön kayıt değişmiş")
    return oz


def _veri(lig: str) -> tuple[list[dict], dict]:
    if lig == "en.2":
        from ..kaynaklar.guncel import lig_guncel
        return lig_guncel(lig)
    from .e_asamasi import lig_verisi
    ms, atlanan = lig_verisi(lig)
    return ms, {"openfootball_atlanan_sezonlar": atlanan}


def kayitlar(lig: str, ceza: float) -> list[dict]:
    """Maç başına maç öncesi λ'lar, ρ, 365 günlük lig ortalaması, frekans tabanı ve gerçekleşen skor (önbellekli)."""
    yol = KAYIT / f"{lig}_c{ceza:g}.json"
    if yol.exists():
        return json.loads(yol.read_text())
    from ..kaynaklar import openfootball as O
    maclar, _ = _veri(lig)
    gm = GolModeli(xi=0.003, pencere_gun=1095, ceza=ceza, yeni_hucum=0.8, yeni_savunma=1.2)
    kay = yuruyen_test(maclar, [MatrisKaydedici(gm, True), MatrisKaydedici(gm, False)], BASLANGIC, None,
                       O.sezon_takimlari(maclar))
    iy = {(m["tarih"], m["ev"], m["dep"]): (m.get("iy_ev"), m.get("iy_dep")) for m in maclar}
    sirali = sorted(maclar, key=lambda m: m["tarih"])
    tarihler = [m["tarih"] for m in sirali]
    toplam = np.cumsum([m["ev_gol"] + m["dep_gol"] for m in sirali])
    say = {a: 0 for a in OLAYLAR}
    out, ix = [], 0
    import bisect
    for k in sorted(kay, key=lambda k: k["tarih"]):
        while ix < len(sirali) and sirali[ix]["tarih"] < k["tarih"]:
            for a, v in gozlenen(sirali[ix]["ev_gol"], sirali[ix]["dep_gol"]).items():
                say[a] += v
            ix += 1
        bas = (date.fromisoformat(k["tarih"]) - timedelta(days=365)).isoformat()
        i0, i1 = bisect.bisect_left(tarihler, bas), bisect.bisect_left(tarihler, k["tarih"])
        n365 = i1 - i0
        mu = float((toplam[i1 - 1] - (toplam[i0 - 1] if i0 else 0)) / n365) if n365 >= 50 else None
        t = k["tahmin"]["dixon_coles"]
        h1, a1 = iy.get((k["tarih"], k["ev"], k["dep"]), (None, None))
        out.append({"lig": lig, "tarih": k["tarih"], "ev_gol": k["ev_gol"], "dep_gol": k["dep_gol"], "iy_ev": h1, "iy_dep": a1,
                    "ev": k["ev"], "dep": k["dep"], "lh": t["lh"],
                    "la": t["la"], "rho": t["rho"], "mu365": mu, "n_once": ix,
                    "taban": {a: (say[a] + 0.5) / (ix + 1) for a in OLAYLAR}})
    KAYIT.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(out))
    return out


def _nb(mu: float, r: float) -> np.ndarray:
    lp = (np.array([math.lgamma(k + r) for k in _g]) - _lf - math.lgamma(r) + r * math.log(r / (r + mu))
          + _g * math.log(mu / (r + mu)))
    return np.exp(lp)


def matris(k: dict, spec: dict) -> np.ndarray:
    lh, la = k["lh"], k["la"]
    if spec.get("w") is not None and k["mu365"] is not None:
        T = lh + la
        T2 = max(k["mu365"] * (1 + spec["b"]) + spec["w"] * (T - k["mu365"]), 0.2)
        lh, la = lh * T2 / T, la * T2 / T
    if spec.get("r"):
        m = np.outer(_nb(lh, spec["r"]), _nb(la, spec["r"]))
        return m / m.sum()
    return skor_matrisi(lh, la, k["rho"] if spec.get("dc") else 0.0)


def olasiliklar(kay: list[dict], spec: dict) -> list[dict]:
    return [market_olasiliklari(matris(k, spec)) for k in kay]


def _ll(p, y):
    p = np.clip(np.asarray(p, float), 1e-15, 1 - 1e-15)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def olcut(kay: list[dict], P: list[dict], marketler) -> float:
    Y = [gozlenen(k["ev_gol"], k["dep_gol"]) for k in kay]
    return float(np.mean([_ll([p[a] for p in P], np.array([y[a] for y in Y], float)).mean() for a in marketler]))


def gelistir() -> dict:
    oz = on_kayit_dogrula()
    sonuc = {"asama": "E2-gelistirme", "on_kayit_sha256": oz, "ceza": {}, "uretim_utc": datetime.now(timezone.utc).isoformat()}
    kay_c = {c: [k for lig in GELISTIRME for k in kayitlar(lig, c)] for c in CEZALAR}
    for c, kay in kay_c.items():
        P = olasiliklar(kay, {})
        sonuc["ceza"][str(c)] = {"gol": olcut(kay, P, GOL_MARKETLERI), "ms": olcut(kay, P, MS), "n": len(kay)}
    ms0 = sonuc["ceza"]["2.0"]["ms"]
    uygun = [c for c in CEZALAR if sonuc["ceza"][str(c)]["ms"] <= ms0 + 0.001]
    c_sec = min(uygun, key=lambda c: sonuc["ceza"][str(c)]["gol"])
    kay = [k for k in kay_c[c_sec] if k["mu365"] is not None]
    sonuc["M2_secilen_ceza"] = c_sec
    izgara = []
    for w in W:
        for b in B:
            P = olasiliklar(kay, {"w": w, "b": b})
            izgara.append({"w": w, "b": b, "gol": olcut(kay, P, GOL_MARKETLERI), "ms": olcut(kay, P, MS)})
    ref = olcut(kay, olasiliklar(kay, {}), MS)
    en = min((g for g in izgara if g["ms"] <= ref + 0.001), key=lambda g: g["gol"])
    sonuc["M3"] = {"secilen": en, "izgara_ilk5": sorted(izgara, key=lambda g: g["gol"])[:5],
                   "M2_ayni_kume_gol": olcut(kay, olasiliklar(kay, {}), GOL_MARKETLERI)}
    nb = []
    for r in R:
        P = olasiliklar(kay, {"w": en["w"], "b": en["b"], "r": r})
        nb.append({"r": r, "gol": olcut(kay, P, GOL_MARKETLERI), "ms": olcut(kay, P, MS)})
    sonuc["M4"] = nb
    adaylar = [("M2", {"ceza": c_sec}, sonuc["M3"]["M2_ayni_kume_gol"], ref),
               ("M3", {"ceza": c_sec, "w": en["w"], "b": en["b"]}, en["gol"], en["ms"])] + [
        ("M4", {"ceza": c_sec, "w": en["w"], "b": en["b"], "r": x["r"]}, x["gol"], x["ms"]) for x in nb]
    adaylar = [a for a in adaylar if a[3] <= ref + 0.001]
    secilen = min(adaylar, key=lambda a: a[2])
    sonuc["secilen_aday"] = {"model": secilen[0], "spec": secilen[1], "gelistirme_gol_olcutu": secilen[2]}
    sonuc["M0_gelistirme_gol_olcutu"] = olcut(kay, olasiliklar([k for k in kay_c[2.0] if k["mu365"] is not None], {}),
                                              GOL_MARKETLERI) if c_sec == 2.0 else sonuc["ceza"]["2.0"]["gol"]
    (CIKTI / "e2_secim.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1))
    return sonuc


def sina() -> dict:
    oz = on_kayit_dogrula()
    secim = json.loads((CIKTI / "e2_secim.json").read_text())
    spec = secim["secilen_aday"]["spec"]
    kay_a = [k for lig in SINAMA for k in kayitlar(lig, spec["ceza"])]
    kay_0 = [k for lig in SINAMA for k in kayitlar(lig, 2.0)]
    # aynı maç kümesi (mu365 tanımlı olanlar)
    gecerli = [i for i, k in enumerate(kay_a) if k["mu365"] is not None]
    kay_a = [kay_a[i] for i in gecerli]
    kay_0 = [kay_0[i] for i in gecerli]
    Pa = olasiliklar(kay_a, spec)
    P0 = olasiliklar(kay_0, {})
    Pd = olasiliklar(kay_0, {"dc": True})
    tutarsiz = sum(1 for k in kay_a[:500] if tutarlilik_denetimi(market_olasiliklari(matris(k, spec)), matris(k, spec)))
    Y = [gozlenen(k["ev_gol"], k["dep_gol"]) for k in kay_a]
    def sez(t):
        d = date.fromisoformat(t); y = d.year if d.month >= 7 else d.year - 1
        return f"{y}"
    kume = [f"{k['lig']}|{sez(k['tarih'])}" for k in kay_a]
    out = {}
    for a in OLAYLAR:
        y = np.array([yy[a] for yy in Y], float)
        pa, p0, pd = (np.array([p[a] for p in P]) for P in (Pa, P0, Pd))
        pt = np.array([k["taban"][a] for k in kay_a])
        la, l0, ld, lt = _ll(pa, y), _ll(p0, y), _ll(pd, y), _ll(pt, y)
        kal = kalibrasyon(pa, y, 10)
        sapma = [x for x in kal["kutular"] if x["n"] >= 30 and abs(x["ort_tahmin"] - x["gerceklesen"]) > 0.05]
        lig_ece = {lg: kalibrasyon(pa[np.array([k["lig"] == lg for k in kay_a])],
                                   y[np.array([k["lig"] == lg for k in kay_a])], 10)["ece"] for lg in SINAMA}
        bt = kume_bootstrap(la - lt, kume)
        b0 = kume_bootstrap(la - l0, kume)
        oran = float(y.mean())
        r = {"olay_orani": round(oran, 4), "ll_aday": float(la.mean()), "ll_M0": float(l0.mean()), "ll_DC": float(ld.mean()),
             "ll_taban": float(lt.mean()), "aday_eksi_taban": bt, "aday_eksi_M0": b0,
             "DC_eksi_M0": kume_bootstrap(ld - l0, kume), "M0_eksi_taban": kume_bootstrap(l0 - lt, kume),
             "ece_aday": kal["ece"], "ece_M0": kalibrasyon(p0, y, 10)["ece"], "lig_ece_aday": lig_ece,
             "buyuk_sapmali_kutu": sapma, "ort_tahmin_aday": float(pa.mean()), "ort_tahmin_M0": float(p0.mean())}
        if 0.02 <= oran <= 0.98:
            r["bilgi_tasiyor"] = bt["ust95"] < 0
            r["kalibre"] = kal["ece"] <= 0.02 and not sapma and all(v <= 0.04 for v in lig_ece.values())
            r["iyilesme_M0"] = b0["ust95"] < 0
            r["gunluk_kapsam"] = r["bilgi_tasiyor"] and r["kalibre"]
        else:
            r["karar"] = "yetersiz olay"
        out[a] = r
    sonuc = {"asama": "E2-sinama", "on_kayit_sha256": oz, "secim": secim["secilen_aday"],
             "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "mac": len(kay_a),
             "lig_mac": {lg: sum(1 for k in kay_a if k["lig"] == lg) for lg in SINAMA},
             "tutarlilik_ihlali_ilk500": tutarsiz, "marketler": out}
    cik = CIKTI / f"e2_sinama_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    cik.mkdir(parents=True, exist_ok=True)
    (cik / "sonuc.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=float))
    print(cik / "sonuc.json")
    return sonuc


if __name__ == "__main__":
    if sys.argv[1:] == ["gelistir"]:
        s = gelistir()
        print(json.dumps({k: v for k, v in s.items() if k != "M3"} | {"M3_secilen": s["M3"]["secilen"]}, indent=1))
    elif sys.argv[1:] == ["sina"]:
        sina()
