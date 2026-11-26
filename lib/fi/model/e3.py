"""E3: E2 üstüne zaman sıralı güç farkı (A) ve sezon içi toplam gol (B) düzeltmesi (ön kayıt: ON_KAYIT_E3.md).

Her maçın düzeltmesi YALNIZCA aynı ligde o maçın tarihinden ÖNCEKİ kayıtlarla hesaplanır (aynı gün dahil değil).
Oran kullanılmaz (MK-1). E2 kayıtları (yeni_gol.kayitlar, ceza 16) ve E2 M3 büzülmesi değiştirilmeden kullanılır.

Kullanım:
  PYTHONPATH=lib python3 -m fi.model.e3 gelistir     # yalnızca geliştirme ligleri: K, s ve A seçimi
  PYTHONPATH=lib python3 -m fi.model.e3 sina         # seçileni asıl sınama liglerinde BİR KEZ değerlendirir
"""
from __future__ import annotations

import bisect
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from . import yeni_gol as Y
from .degerlendirme import kume_bootstrap
from .goller import skor_matrisi
from .metrikler import kalibrasyon
from .pazar_modelleri import OLAYLAR, gozlenen, market_olasiliklari, tutarlilik_denetimi

BURASI = Path(__file__).resolve().parent
CIKTI = Y.CIKTI / "e3"
E2_SPEC = {"ceza": 16.0, "w": 0.65, "b": 0.0}
GELISTIRME = Y.GELISTIRME
ASIL_SINAMA = ("en.1", "de.1", "it.1", "es.1", "en.3", "en.4", "fr.2", "it.2")
IKINCIL = Y.SINAMA
GAMMA = tuple(round(0.80 + 0.05 * i, 2) for i in range(17))
DELTA = tuple(round(-0.20 + 0.05 * i, 2) for i in range(9))
PENCERE_A_GUN = 730
EN_AZ_A = 300
KLER = (100, 150, 250)
SLER = (0.0, 0.25, 0.5, 0.75, 1.0)
_g = np.arange(11)
_lf = np.cumsum(np.r_[0.0, np.log(np.arange(1, 11))])          # log k!


def on_kayit_dogrula() -> str:
    oz = hashlib.sha256((BURASI / "ON_KAYIT_E3.md").read_bytes()).hexdigest()
    if oz != (BURASI / "ON_KAYIT_E3.sha256").read_text().strip():
        raise RuntimeError("E3 ön kaydı değişmiş")
    return oz


# ------------------------------------------------------------------------------------------------ temel λ (E2 M3)
def e2_lambdalar(k: dict) -> tuple[float, float]:
    lh, la = k["lh"], k["la"]
    T = lh + la
    T2 = max(k["mu365"] * (1 + E2_SPEC["b"]) + E2_SPEC["w"] * (T - k["mu365"]), 0.2)
    return lh * T2 / T, la * T2 / T


def ms_olasiliklari(lh: np.ndarray, la: np.ndarray) -> np.ndarray:
    """Bağımsız Poisson (0–10, normalize) 1X2 olasılıkları; vektörel. Dönüş (n, 3)."""
    ph = np.exp(-lh[:, None] + np.log(lh[:, None]) * _g - _lf)
    pa = np.exp(-la[:, None] + np.log(la[:, None]) * _g - _lf)
    m = ph[:, :, None] * pa[:, None, :]
    m /= m.sum(axis=(1, 2), keepdims=True)
    alt = np.tril(np.ones((11, 11), bool), -1)          # ev > dep
    return np.stack([(m * alt).sum((1, 2)), np.trace(m, axis1=1, axis2=2), (m * alt.T).sum((1, 2))], axis=1)


def _donustur(lh, la, gamma, delta):
    T = lh + la
    d = gamma * np.log(lh / la) + delta
    e = np.exp(d)
    return T * e / (1 + e), T / (1 + e)


def gamma_delta_kestir(lh: np.ndarray, la: np.ndarray, sonuc: np.ndarray) -> tuple[float, float, float]:
    """1X2 log-olabilirliğini en büyükleyen (γ, δ) ızgara değeri. sonuc: 0=ev, 1=beraberlik, 2=dep."""
    en = (1.0, 0.0, -np.inf)
    for g in GAMMA:
        for dl in DELTA:
            p = ms_olasiliklari(*_donustur(lh, la, g, dl))
            ll = float(np.log(np.clip(p[np.arange(len(sonuc)), sonuc], 1e-15, 1)).sum())
            if ll > en[2]:
                en = (g, dl, ll)
    return en


# ------------------------------------------------------------------------------------------------ çevrimiçi düzeltme
def duzeltmeler(kay: list[dict], A: bool, K: int | None, s: float) -> list[dict]:
    """Her kayıt için (lh', la', γ, δ, κ). kay: tek lig ya da çok lig; lig içinde tarih sırasıyla işlenir."""
    out = [None] * len(kay)
    ligler: dict[str, list[int]] = {}
    for i, k in enumerate(kay):
        ligler.setdefault(k["lig"], []).append(i)
    for lig, ix in ligler.items():
        ix = sorted(ix, key=lambda i: kay[i]["tarih"])
        tarih = [kay[i]["tarih"] for i in ix]
        base = np.array([e2_lambdalar(kay[i]) for i in ix])
        sonuc = np.array([0 if kay[i]["ev_gol"] > kay[i]["dep_gol"] else 1 if kay[i]["ev_gol"] == kay[i]["dep_gol"] else 2
                          for i in ix])
        gol = np.array([kay[i]["ev_gol"] + kay[i]["dep_gol"] for i in ix], float)
        T = base.sum(1)
        cum_g, cum_t = np.r_[0, np.cumsum(gol)], np.r_[0, np.cumsum(T)]
        ay, gd = None, (1.0, 0.0)
        for j, i in enumerate(ix):
            once = bisect.bisect_left(tarih, tarih[j])                  # aynı gün ve sonrası hariç
            if A and tarih[j][:7] != ay:
                ay = tarih[j][:7]
                bas = bisect.bisect_left(tarih, (date.fromisoformat(tarih[j]) - timedelta(days=PENCERE_A_GUN)).isoformat())
                if once - bas >= EN_AZ_A:
                    g, d, _ = gamma_delta_kestir(base[bas:once, 0], base[bas:once, 1], sonuc[bas:once])
                    gd = (g, d)
                else:
                    gd = (1.0, 0.0)
            gamma, delta = gd if A else (1.0, 0.0)
            lh, la = _donustur(base[j, 0], base[j, 1], gamma, delta)
            kappa = 1.0
            if K and once >= K and s:
                G = cum_g[once] - cum_g[once - K]
                P = cum_t[once] - cum_t[once - K]
                kappa = 1.0 + s * (G / P - 1.0)
            out[i] = {"lh": float(lh * kappa), "la": float(la * kappa), "gamma": gamma, "delta": delta, "kappa": float(kappa)}
    return out


def canli_gamma_delta(lig: str, tarih: str) -> dict:
    """Günlük kullanım: [tarih − 730 gün, tarih) aralığındaki E2 kayıtlarından γ, δ (sınamadaki aylık yeniden kestirimle
    aynı ızgara ve ölçüt). Kayıtlar yerel geçmiş veriyle sınırlıdır; pencerenin son kayıt tarihi raporlanır."""
    bas = (date.fromisoformat(tarih) - timedelta(days=PENCERE_A_GUN)).isoformat()
    kay = [k for k in Y.kayitlar(lig, E2_SPEC["ceza"]) if k["mu365"] is not None and bas <= k["tarih"] < tarih]
    if len(kay) < EN_AZ_A:
        return {"gamma": 1.0, "delta": 0.0, "pencere_mac": len(kay), "pencere_son": kay[-1]["tarih"] if kay else None,
                "not": f"pencerede {len(kay)} < {EN_AZ_A} maç: düzeltme uygulanmadı"}
    base = np.array([e2_lambdalar(k) for k in kay])
    sonuc = np.array([0 if k["ev_gol"] > k["dep_gol"] else 1 if k["ev_gol"] == k["dep_gol"] else 2 for k in kay])
    g, d, _ = gamma_delta_kestir(base[:, 0], base[:, 1], sonuc)
    return {"gamma": g, "delta": d, "pencere_mac": len(kay), "pencere_bas": kay[0]["tarih"], "pencere_son": kay[-1]["tarih"]}


def donustur(lh: float, la: float, gamma: float, delta: float) -> tuple[float, float]:
    a, b = _donustur(np.array([lh]), np.array([la]), gamma, delta)
    return float(a[0]), float(b[0])


def olasiliklar(kay: list[dict], A: bool, K: int | None, s: float) -> list[dict]:
    return [market_olasiliklari(skor_matrisi(d["lh"], d["la"], 0.0)) for d in duzeltmeler(kay, A, K, s)]


def _kayitlar(ligler) -> list[dict]:
    return [k for lig in ligler for k in Y.kayitlar(lig, E2_SPEC["ceza"]) if k["mu365"] is not None]


# ------------------------------------------------------------------------------------------------ geliştirme
def gelistir() -> dict:
    oz = on_kayit_dogrula()
    kay = _kayitlar(GELISTIRME)
    E2P = Y.olasiliklar(kay, {"w": E2_SPEC["w"], "b": E2_SPEC["b"]})
    ref = {"gol": Y.olcut(kay, E2P, Y.GOL_MARKETLERI), "ms": Y.olcut(kay, E2P, Y.MS)}
    adaylar = [{"ad": "E2", "A": False, "K": None, "s": 0.0, **ref}]
    PA = olasiliklar(kay, True, None, 0.0)
    adaylar.append({"ad": "E2+A", "A": True, "K": None, "s": 0.0,
                    "gol": Y.olcut(kay, PA, Y.GOL_MARKETLERI), "ms": Y.olcut(kay, PA, Y.MS)})
    for A in (False, True):
        for K in KLER:
            for s in SLER[1:]:
                P = olasiliklar(kay, A, K, s)
                adaylar.append({"ad": ("E2+A+B" if A else "E2+B"), "A": A, "K": K, "s": s,
                                "gol": Y.olcut(kay, P, Y.GOL_MARKETLERI), "ms": Y.olcut(kay, P, Y.MS)})
    for a in adaylar:
        a["olcut"] = (a["gol"] + a["ms"]) / 2
        a["uygun"] = a["gol"] <= ref["gol"] + 0.001 and a["ms"] <= ref["ms"] + 0.001
    sec = min((a for a in adaylar if a["uygun"]), key=lambda a: a["olcut"])
    sonuc = {"asama": "E3-gelistirme", "on_kayit_sha256": oz, "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "mac": len(kay), "E2": ref, "adaylar": adaylar, "secilen": sec}
    CIKTI.mkdir(parents=True, exist_ok=True)
    (CIKTI / "e3_secim.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1))
    return sonuc


# ------------------------------------------------------------------------------------------------ sınama
def _sezon(t: str) -> str:
    d = date.fromisoformat(t)
    return str(d.year if d.month >= 7 else d.year - 1)


def degerlendir(kay: list[dict], sec: dict, lig_listesi) -> dict:
    P3 = olasiliklar(kay, sec["A"], sec["K"], sec["s"])
    P2 = Y.olasiliklar(kay, {"w": E2_SPEC["w"], "b": E2_SPEC["b"]})
    Yg = [gozlenen(k["ev_gol"], k["dep_gol"]) for k in kay]
    kume = [f"{k['lig']}|{_sezon(k['tarih'])}" for k in kay]
    ligvek = np.array([k["lig"] for k in kay])
    out = {}
    for a in OLAYLAR:
        y = np.array([yy[a] for yy in Yg], float)
        p3, p2 = np.array([p[a] for p in P3]), np.array([p[a] for p in P2])
        pt = np.array([k["taban"][a] for k in kay])
        l3, l2, lt = Y._ll(p3, y), Y._ll(p2, y), Y._ll(pt, y)
        kal = kalibrasyon(p3, y, 10)
        sapma = [x for x in kal["kutular"] if x["n"] >= 30 and abs(x["ort_tahmin"] - x["gerceklesen"]) > 0.05]
        lig_ece = {lg: kalibrasyon(p3[ligvek == lg], y[ligvek == lg], 10)["ece"] for lg in lig_listesi if (ligvek == lg).any()}
        bt, b2 = kume_bootstrap(l3 - lt, kume), kume_bootstrap(l3 - l2, kume)
        oran = float(y.mean())
        r = {"olay_orani": round(oran, 4), "ll_E3": float(l3.mean()), "ll_E2": float(l2.mean()), "ll_taban": float(lt.mean()),
             "E3_eksi_taban": bt, "E3_eksi_E2": b2, "ece_E3": kal["ece"], "ece_E2": kalibrasyon(p2, y, 10)["ece"],
             "lig_ece_E3": lig_ece, "buyuk_sapmali_kutu": sapma}
        if 0.02 <= oran <= 0.98:
            r["bilgi_tasiyor"] = bt["ust95"] < 0
            r["kalibre"] = kal["ece"] <= 0.02 and not sapma and all(v <= 0.04 for v in lig_ece.values())
            r["E2_ye_gore_iyilesme"] = b2["ust95"] < 0
            r["gunluk_kapsam"] = r["bilgi_tasiyor"] and r["kalibre"]
        else:
            r["karar"] = "yetersiz olay"
        out[a] = r
    tutarsiz = sum(1 for d in duzeltmeler(kay[:400], sec["A"], sec["K"], sec["s"])
                   if tutarlilik_denetimi(market_olasiliklari(skor_matrisi(d["lh"], d["la"], 0.0)),
                                          skor_matrisi(d["lh"], d["la"], 0.0)))
    return {"mac": len(kay), "lig_mac": {lg: int((ligvek == lg).sum()) for lg in lig_listesi},
            "tutarlilik_ihlali_ilk400": tutarsiz, "marketler": out}


def sina() -> dict:
    oz = on_kayit_dogrula()
    secim = json.loads((CIKTI / "e3_secim.json").read_text())
    sec = secim["secilen"]
    if sec["ad"] == "E2":
        return {"asama": "E3-sinama", "durum": "geliştirmede E2 seçildi; E3 yok, sınama yapılmadı"}
    asil = degerlendir(_kayitlar(ASIL_SINAMA), sec, ASIL_SINAMA)
    ikincil = degerlendir(_kayitlar(IKINCIL), sec, IKINCIL)
    sonuc = {"asama": "E3-sinama", "on_kayit_sha256": oz, "secilen": sec,
             "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "asil": asil, "ikincil_gorulmus": ikincil}
    cik = CIKTI / f"e3_sinama_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    cik.mkdir(parents=True, exist_ok=True)
    (cik / "sonuc.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=float))
    print(cik / "sonuc.json")
    return sonuc


if __name__ == "__main__":
    if sys.argv[1:] == ["gelistir"]:
        s = gelistir()
        print(json.dumps({"E2": s["E2"], "secilen": s["secilen"],
                          "ilk5": sorted(s["adaylar"], key=lambda a: a["olcut"])[:5]}, ensure_ascii=False, indent=1))
    elif sys.argv[1:] == ["sina"]:
        sina()
