"""F aşaması: ilk yarı / ikinci yarı marketleri ve devre bağımlılığı testi (ön kayıt: ON_KAYIT_F.md).

Olay tanımları fi.pazar.esdegerlik ile BİREBİR aynıdır (Nesine kodları). Olasılık ızgarası: devre başına takım 0..UST gol.
Kullanım: PYTHONPATH=lib python3 -m fi.model.f_asamasi
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .. import olay_uzayi as ES  # fiyat içermeyen olay uzayı (MK-1)
from .backtest import yuruyen_test
from .degerlendirme import kume_bootstrap
from .e_asamasi import lig_verisi
from .goller import GolModeli
from .metrikler import ikili, kalibrasyon
from .pazar_modelleri import MatrisKaydedici

BURASI = Path(__file__).resolve().parent
ON_KAYIT = BURASI / "ON_KAYIT_F.md"
LIGLER = ("it.2", "fr.2", "en.3", "en.4")
BASLANGIC = "2019-07-01"
XI, PENCERE, CEZA, ONSEL = 0.003, 1095, 2.0, (0.8, 1.2)
MARJINAL = {7: 0.0, 9: 0.0, 209: 0.5, 14: 1.5, 15: 2.5, 452: 0.0, 599: 0.0, 455: 0.5, 457: 0.5}
BIRLESIK = {801: 0.0, 5: 0.0, 48: 0.0, 295: 0.0, 296: 0.0, 528: 0.0, 529: 0.0, 584: 0.0, 585: 0.0, 591: 0.0,
            592: 0.0, 586: 0.0, 587: 0.0}
IY_SKOR = {"0:0": (0, 0), "1:0": (1, 0), "0:1": (0, 1), "1:1": (1, 1)}


def olaylar() -> dict[str, tuple[str, np.ndarray]]:
    """'kod|seçenek' -> (tür, maske). tür: marjinal | birlesik."""
    out = {}
    for tur, tablo in (("marjinal", MARJINAL), ("birlesik", BIRLESIK)):
        for kod, c in tablo.items():
            t, _ = ES._tablo(kod, c, "", None)
            for ad, m in t.items():
                out[f"{kod}|{ad}"] = (tur, m)
    for ad, (a, b) in IY_SKOR.items():
        out[f"779|{ad}"] = ("marjinal", (ES.H1 == a) & (ES.A1 == b))
    return out


OLAYLAR = olaylar()
_g = np.arange(ES.UST + 1)
_fakt = np.array([math.factorial(int(k)) for k in _g], float)


def _pmf(l: float) -> np.ndarray:
    p = np.exp(-l) * l ** _g / _fakt
    return p / p.sum()


def ortak_dagilim(lh: float, la: float, s_ev: float, s_dep: float) -> np.ndarray:
    """ES ızgarası sırasıyla (h1, a1, h2, a2) olasılık vektörü: λ verildiğinde bağımsız dört Poisson."""
    p = np.einsum("i,j,k,l->ijkl", _pmf(lh * s_ev), _pmf(la * s_dep), _pmf(lh * (1 - s_ev)), _pmf(la * (1 - s_dep)))
    return p.ravel()


MANTIKSAL_TAMAMLAMA = True     # ON_KAYIT_F_SAPMA.md: maç sonu 0-0 ise ilk yarı 0-0 (yalnızca bu durum)


def nokta(m: dict, tamamla: bool | None = None) -> int | None:
    tamamla = MANTIKSAL_TAMAMLAMA if tamamla is None else tamamla
    if m.get("iy_ev") is None:
        if tamamla and m["ev_gol"] == 0 and m["dep_gol"] == 0:
            return 0                                 # (0, 0, 0, 0)
        return None
    h1, a1 = m["iy_ev"], m["iy_dep"]
    h2, a2 = m["ev_gol"] - h1, m["dep_gol"] - a1
    if min(h2, a2) < 0:
        return -1                                    # devre skoru maç sonuyla çelişiyor
    u = ES.UST
    if max(h1, a1, h2, a2) > u:
        return -2                                    # ızgara dışı devre skoru: kırpılmaz, değerlendirme dışı (raporlanır)
    return ((h1 * (u + 1) + a1) * (u + 1) + h2) * (u + 1) + a2


def on_kayit_dogrula() -> str:
    oz = hashlib.sha256(ON_KAYIT.read_bytes()).hexdigest()
    if oz != (BURASI / "ON_KAYIT_F.sha256").read_text().strip():
        raise RuntimeError("ön kayıt değişmiş")
    return oz


def lig_kayitlari(lig: str) -> dict:
    maclar, atlanan = lig_verisi(lig)
    from ..kaynaklar import openfootball as O
    takimlar = O.sezon_takimlari(maclar)
    dc = GolModeli(xi=XI, pencere_gun=PENCERE, ceza=CEZA, yeni_hucum=ONSEL[0], yeni_savunma=ONSEL[1], dixon_coles=False)
    kay = yuruyen_test(maclar, [MatrisKaydedici(dc, True)], BASLANGIC, None, takimlar)
    anahtar = {(m["tarih"], m["ev"], m["dep"]): m for m in maclar}
    sirali = sorted(maclar, key=lambda m: m["tarih"])
    say = {k: 0 for k in OLAYLAR}
    n = ix = 0
    pay = [0, 0, 0, 0]                                # ev 1Y, ev toplam, dep 1Y, dep toplam
    satirlar, celiski, eksik = [], 0, {"iy_yok": 0, "iy_yok_gol": [], "iy_var_gol": []}
    for k in sorted(kay, key=lambda k: k["tarih"]):
        while ix < len(sirali) and sirali[ix]["tarih"] < k["tarih"]:
            mm = sirali[ix]
            nk = nokta(mm)
            if nk is not None and nk >= 0:          # ızgara dışı (-2) ve çelişkili (-1) tabana da girmez
                for ad, (_, mask) in OLAYLAR.items():
                    say[ad] += bool(mask[nk])
                n += 1
                pay[0] += mm["iy_ev"] or 0; pay[1] += mm["ev_gol"]; pay[2] += mm["iy_dep"] or 0; pay[3] += mm["dep_gol"]
            ix += 1
        m = anahtar[(k["tarih"], k["ev"], k["dep"])]
        nk = nokta(m)
        if nk is None:
            eksik["iy_yok"] += 1
            eksik["iy_yok_gol"].append(m["ev_gol"] + m["dep_gol"])
            continue
        if nk == -2:
            eksik["izgara_disi"] = eksik.get("izgara_disi", 0) + 1
            continue
        if nk < 0:
            celiski += 1
            continue
        eksik["iy_var_gol"].append(m["ev_gol"] + m["dep_gol"])
        if m.get("iy_ev") is None:
            eksik["mantiksal_0_0"] = eksik.get("mantiksal_0_0", 0) + 1
        if n < 200:
            continue
        s_ev, s_dep = pay[0] / pay[1], pay[2] / pay[3]
        t = k["tahmin"]["dixon_coles"]
        p = ortak_dagilim(t["lh"], t["la"], s_ev, s_dep)
        satirlar.append({"tarih": k["tarih"], "nokta": nk, "s_ev": s_ev, "s_dep": s_dep,
                         "model": {ad: float(p[mask].sum()) for ad, (_, mask) in OLAYLAR.items()},
                         "taban": {ad: (say[ad] + 0.5) / (n + 1) for ad in OLAYLAR}})
    return {"lig": lig, "atlanan_sezonlar": atlanan, "satirlar": satirlar, "celiskili_devre_skoru": celiski,
            "eksik": {"iy_yok": eksik["iy_yok"], "mantiksal_0_0_tamamlanan": eksik.get("mantiksal_0_0", 0),
                      "izgara_disi_devre_skoru": eksik.get("izgara_disi", 0),
                      "iy_yok_ort_gol": round(float(np.mean(eksik["iy_yok_gol"])), 3) if eksik["iy_yok_gol"] else None,
                      "iy_var_ort_gol": round(float(np.mean(eksik["iy_var_gol"])), 3) if eksik["iy_var_gol"] else None}}


def raporla(satirlar: list[dict]) -> dict:
    kume = [s["tarih"] for s in satirlar]
    out = {}
    for ad, (tur, mask) in OLAYLAR.items():
        y = np.array([bool(mask[s["nokta"]]) for s in satirlar], float)
        p = np.clip(np.array([s["model"][ad] for s in satirlar]), 1e-15, 1 - 1e-15)
        b = np.clip(np.array([s["taban"][ad] for s in satirlar]), 1e-15, 1 - 1e-15)
        ll = lambda q: -(y * np.log(q) + (1 - y) * np.log(1 - q))
        fark = kume_bootstrap(ll(p) - ll(b), kume)
        kal = kalibrasyon(p, y, 10)
        sapma = [x for x in kal["kutular"] if x["n"] >= 30 and abs(x["ort_tahmin"] - x["gerceklesen"]) > 0.05]
        r = {"tur": tur, "olay_orani": round(float(y.mean()), 4), "model": ikili(p, y), "taban": ikili(b, y),
             "ece": kal["ece"], "taban_farki": fark, "buyuk_sapmali_kutu": sapma}
        oran = y.mean()
        if not 0.02 <= oran <= 0.98:
            r["karar"] = "yetersiz olay"
        elif tur == "marjinal":
            r["F1_bilgi_tasiyor"] = fark["ust95"] < 0
            r["F1_kalibre"] = kal["ece"] <= 0.02 and not sapma
        else:
            g = kume_bootstrap(y - p, kume)
            r["gerceklesen_eksi_tahmin"] = g
            r["F2_bagimsizlik_reddedildi"] = g["alt95"] > 0 or g["ust95"] < 0
            r["uretim"] = "hesaplanamaz (devre bağımlılığı modellenmedi)" if r["F2_bagimsizlik_reddedildi"] \
                else "bağımsızlık bu testte reddedilmedi (doğrulanmış sayılmaz)"
        out[ad] = r
    # 1Y KG ile 2Y KG arasındaki olasılık oranı: gözlenen vs model
    a = np.array([bool(OLAYLAR["452|Var"][1][s["nokta"]]) for s in satirlar])
    c = np.array([bool(OLAYLAR["599|Var"][1][s["nokta"]]) for s in satirlar])
    def olasilik_orani_hesapla(p11, p10, p01, p00):
        return (p11 * p00) / (p10 * p01) if p10 * p01 > 0 else None
    gz = olasilik_orani_hesapla((a & c).mean(), (a & ~c).mean(), (~a & c).mean(), (~a & ~c).mean())
    pm = {k: float(np.mean([s["model"][f"801|{k}"] for s in satirlar])) for k in ("Evet/Evet", "Evet/Hayır", "Hayır/Evet", "Hayır/Hayır")}
    out["_KG1_KG2_olasilik_orani"] = {"gozlenen": gz, "model_ortalama_dagilimdan": olasilik_orani_hesapla(
        pm["Evet/Evet"], pm["Evet/Hayır"], pm["Hayır/Evet"], pm["Hayır/Hayır"]), "n": len(satirlar),
        "not": "model maç bazında bağımsız; ortalama dağılımdaki bağımlılık yalnızca λ farklılığından gelir"}
    return out


def main(argv=None) -> int:
    oz = on_kayit_dogrula()
    tum, ligler = [], {}
    for lig in LIGLER:
        r = lig_kayitlari(lig)
        tum.extend(r["satirlar"])
        ligler[lig] = {k: v for k, v in r.items() if k != "satirlar"} | {"mac": len(r["satirlar"])}
    sonuc = {"asama": "F-v2 (sapma: ON_KAYIT_F_SAPMA.md)" if MANTIKSAL_TAMAMLAMA else "F", "on_kayit_sha256": oz,
             "sapma_kaydi_sha256": hashlib.sha256((BURASI / "ON_KAYIT_F_SAPMA.md").read_bytes()).hexdigest(), "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "ligler": ligler, "toplam_mac": len(tum), "marketler": raporla(tum)}
    cik = BURASI.parents[2] / "output" / "model" / f"f_asamasi_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    cik.mkdir(parents=True, exist_ok=True)
    (cik / "sonuc.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(cik / "sonuc.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
