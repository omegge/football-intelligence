"""D aşaması değerlendirmeleri: eşleştirilmiş model karşılaştırması, düşük skor / beraberlik etkisi, yeni takım önseli.

Kümelenmiş bootstrap: aynı gün oynanan maçlar bağımsız değildir (ortak koşullar), bu yüzden yeniden örnekleme
TARİH kümeleri üzerinden yapılır.
"""

from __future__ import annotations

import math

import numpy as np

from .goller import GolModeli
from .metrikler import kalibrasyon, maclik_log_loss

DUSUK_SKORLAR = ("0_0", "1_0", "0_1", "1_1")


def kume_bootstrap(fark: np.ndarray, kumeler: list, n: int = 2000, tohum: int = 11) -> dict:
    fark = np.asarray(fark, float)
    etiket = {k: i for i, k in enumerate(dict.fromkeys(kumeler))}
    idx = np.array([etiket[k] for k in kumeler])
    toplam = np.bincount(idx, weights=fark)
    sayi = np.bincount(idx)
    rng = np.random.default_rng(tohum)
    secim = rng.integers(0, len(toplam), (n, len(toplam)))
    ort = toplam[secim].sum(1) / sayi[secim].sum(1)
    return {"fark": float(fark.mean()), "alt95": float(np.percentile(ort, 2.5)),
            "ust95": float(np.percentile(ort, 97.5)), "n_mac": int(len(fark)), "n_kume": int(len(toplam))}


def eslestirilmis(kayitlar: list[dict], a: str, b: str) -> dict:
    """a − b maç başı log-loss farkı (negatif = a daha iyi); tarih kümeli bootstrap + sezon bazında işaret tutarlılığı."""
    y = [k["sonuc"] for k in kayitlar]
    la = maclik_log_loss([k["tahmin"][a] for k in kayitlar], y)
    lb = maclik_log_loss([k["tahmin"][b] for k in kayitlar], y)
    genel = kume_bootstrap(la - lb, [k["tarih"] for k in kayitlar])
    sezon = {}
    for s in sorted({k["sezon"] for k in kayitlar}):
        i = [j for j, k in enumerate(kayitlar) if k["sezon"] == s]
        sezon[s] = round(float((la[i] - lb[i]).mean()), 5)
    genel["sezon_farklari"] = sezon
    genel["a_iyi_sezon"] = sum(v < 0 for v in sezon.values())
    genel["sezon_sayisi"] = len(sezon)
    return {k: (round(v, 5) if isinstance(v, float) else v) for k, v in genel.items()}


def dusuk_skor_analizi(kayitlar: list[dict], modeller=("poisson", "dixon_coles")) -> dict:
    """Her düşük skor için: toplam tahmin edilen sayı vs gerçekleşen sayı, ikili log-loss; beraberlik kalibrasyonu."""
    out = {}
    for md in modeller:
        r = {}
        for s in DUSUK_SKORLAR:
            e, d = map(int, s.split("_"))
            p = np.array([k["tahmin"][md][f"skor_{s}"] for k in kayitlar])
            o = np.array([k["ev_gol"] == e and k["dep_gol"] == d for k in kayitlar], float)
            pc = np.clip(p, 1e-12, 1 - 1e-12)
            r[s] = {"beklenen": round(float(p.sum()), 1), "gerceklesen": int(o.sum()),
                    "log_loss": round(float(-np.mean(o * np.log(pc) + (1 - o) * np.log(1 - pc))), 5)}
        pd_ = np.array([k["tahmin"][md]["D"] for k in kayitlar])
        od = np.array([k["sonuc"] == "D" for k in kayitlar], float)
        r["beraberlik"] = {"beklenen": round(float(pd_.sum()), 1), "gerceklesen": int(od.sum()),
                           "brier": round(float(np.mean((pd_ - od) ** 2)), 5), "ece": kalibrasyon(pd_, od, 10)["ece"]}
        out[md] = r
    return out


def sezon_ici_parametreler(maclar: list[dict], sezon: str, ceza: float = 0.1) -> dict:
    """Bir sezonun KENDİ maçlarıyla (ağırlıksız) kestirilmiş takım parametreleri, lig ortalamasına göre merkezlenmiş:
    {takım: (log hücum, log savunma)}. Yalnızca önsel kestirimi için geçmiş sezonlarda kullanılır."""
    from datetime import date, timedelta
    ms = [m for m in maclar if m["sezon"] == sezon]
    sonraki = (date.fromisoformat(max(m["tarih"] for m in ms)) + timedelta(days=1)).isoformat()
    g = GolModeli(xi=0.0, pencere_gun=400, ceza=ceza, dixon_coles=False)   # pencere = tam olarak o sezon
    g.hazirla(ms, sonraki, {t for m in ms for t in (m["ev"], m["dep"])})
    if not g.param or not g.kesim:
        raise ValueError(f"{sezon}: sezon içi kestirim verisiz kaldı")
    b, ix, n = g.param["beta"], g.param["ix"], g.param["n"]
    h = {t: b[2 + i] for t, i in ix.items()}
    d = {t: b[2 + n + i] for t, i in ix.items()}
    mh, md = float(np.mean(list(h.values()))), float(np.mean(list(d.values())))
    return {t: (h[t] - mh, d[t] - md) for t in ix}


def yeni_takim_onseli(maclar: list[dict], sezonlar: list[str]) -> dict:
    """Verilen (geçmiş) sezonlarda lige yeni gelen takımların ilk sezon hücum/savunma çarpanlarının ortalaması.
    Dönüş: {'hucum': exp(ort log hücum), 'savunma': exp(ort log savunma), 'n_takim', 'sezonlar'}."""
    takim = {s: {t for m in maclar if m["sezon"] == s for t in (m["ev"], m["dep"])} for s in {m["sezon"] for m in maclar}}
    tum = sorted(takim)
    hs, ds, kullanilan = [], [], []
    for s in sezonlar:
        i = tum.index(s)
        if i == 0:
            continue
        yeni = takim[s] - takim[tum[i - 1]]
        if not yeni:
            continue
        p = sezon_ici_parametreler(maclar, s)
        for t in yeni:
            hs.append(p[t][0])
            ds.append(p[t][1])
        kullanilan.append(s)
    if not hs:
        return {"hucum": 1.0, "savunma": 1.0, "n_takim": 0, "sezonlar": []}
    se_h = float(np.std(hs, ddof=1) / math.sqrt(len(hs))) if len(hs) > 1 else None
    se_d = float(np.std(ds, ddof=1) / math.sqrt(len(ds))) if len(ds) > 1 else None
    return {"hucum": round(math.exp(float(np.mean(hs))), 3), "savunma": round(math.exp(float(np.mean(ds))), 3),
            "log_hucum_se": se_h, "log_savunma_se": se_d, "n_takim": len(hs), "sezonlar": kullanilan}
