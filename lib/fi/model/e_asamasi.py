"""E aşaması: market bazında zaman sıralı değerlendirme (ön kayıt: ON_KAYIT_E.md; SHA-256 ON_KAYIT_E.sha256).

Kullanım: PYTHONPATH=lib python3 -m fi.model.e_asamasi [lig ...]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..kaynaklar import openfootball as O
from .backtest import yuruyen_test
from .degerlendirme import kume_bootstrap
from .goller import GolModeli
from .metrikler import ikili, kalibrasyon
from .pazar_modelleri import OLAYLAR, gozlenen, market_olasiliklari, matris_kayittan, tutarlilik_denetimi

BURASI = Path(__file__).resolve().parent
ON_KAYIT = BURASI / "ON_KAYIT_E.md"
LIGLER = ("fr.1", "nl.1", "pt.1", "de.2", "es.2")
BASLANGIC = "2019-07-01"
XI, PENCERE, CEZA, ONSEL = 0.003, 1095, 2.0, (0.8, 1.2)


def on_kayit_dogrula() -> str:
    oz = hashlib.sha256(ON_KAYIT.read_bytes()).hexdigest()
    beklenen = (BURASI / "ON_KAYIT_E.sha256").read_text().strip()
    if oz != beklenen:
        raise RuntimeError(f"ön kayıt değişmiş: {oz} ≠ {beklenen}")
    return oz


def lig_verisi(lig: str) -> tuple[list[dict], list[dict]]:
    maclar, atlanan = [], []
    for d in sorted(p for p in O.KOK.iterdir() if p.is_dir() and O.SEZON_DESENI.fullmatch(p.name)):
        if not (d / f"{lig}.json").exists():
            continue
        try:
            ms, _ = O.lig_oku(lig, sezonlar=[d.name])
            maclar.extend(ms)
        except O.VeriTutarsizligi as e:
            atlanan.append({"sezon": d.name, "neden": str(e)[:200]})
    return maclar, atlanan


def lig_kayitlari(lig: str) -> dict:
    maclar, atlanan = lig_verisi(lig)
    takimlar = O.sezon_takimlari(maclar)
    dc = GolModeli(xi=XI, pencere_gun=PENCERE, ceza=CEZA, yeni_hucum=ONSEL[0], yeni_savunma=ONSEL[1])
    from .pazar_modelleri import MatrisKaydedici
    kay = yuruyen_test(maclar, [MatrisKaydedici(dc, True), MatrisKaydedici(dc, False)], BASLANGIC, None, takimlar)
    assert all(k["egitim_kesimi"] is None or k["egitim_kesimi"] < k["tarih"] for k in kay)
    # taban: aynı ligde tahmin tarihinden önceki bütün maçlarda olay sıklığı
    sirali = sorted(maclar, key=lambda m: m["tarih"])
    say = {ad: 0 for ad in OLAYLAR}
    n, ix = 0, 0
    tutarsiz = []
    satirlar = []
    for k in sorted(kay, key=lambda k: k["tarih"]):
        while ix < len(sirali) and sirali[ix]["tarih"] < k["tarih"]:
            for ad, v in gozlenen(sirali[ix]["ev_gol"], sirali[ix]["dep_gol"]).items():
                say[ad] += v
            n += 1
            ix += 1
        y = gozlenen(k["ev_gol"], k["dep_gol"])
        satir = {"tarih": k["tarih"], "sezon": k["sezon"], "y": y,
                 "taban": {ad: (say[ad] + 0.5) / (n + 1) for ad in OLAYLAR}}
        for md in ("dixon_coles", "poisson"):
            m = matris_kayittan(k["tahmin"][md])
            p = market_olasiliklari(m)
            h = tutarlilik_denetimi(p, m)
            if h:
                tutarsiz.append({"tarih": k["tarih"], "ev": k["ev"], "dep": k["dep"], "model": md, "hata": h})
            satir[md] = p
        satirlar.append(satir)
    return {"lig": lig, "atlanan_sezonlar": atlanan, "mac": len(satirlar), "satirlar": satirlar,
            "tutarsizlik": tutarsiz, "son_tarih": max((s["tarih"] for s in satirlar), default=None)}


def market_raporu(satirlar: list[dict]) -> dict:
    kume = [s["tarih"] for s in satirlar]
    out = {}
    for ad in OLAYLAR:
        y = np.array([s["y"][ad] for s in satirlar], float)
        oran = float(y.mean())
        r = {"olay_orani": round(oran, 4), "n": len(y)}
        def ll(p):
            p = np.clip(np.asarray(p, float), 1e-15, 1 - 1e-15)
            return -(y * np.log(p) + (1 - y) * np.log(1 - p))
        lt = ll([s["taban"][ad] for s in satirlar])
        r["taban"] = {k: round(v, 5) for k, v in ikili([s["taban"][ad] for s in satirlar], y).items() if k != "n"}
        for md in ("dixon_coles", "poisson"):
            p = np.array([s[md][ad] for s in satirlar])
            lm = ll(p)
            kal = kalibrasyon(p, y, 10)
            buyuk_sapma = [b for b in kal["kutular"] if b["n"] >= 30 and abs(b["ort_tahmin"] - b["gerceklesen"]) > 0.05]
            fark = kume_bootstrap(lm - lt, kume)
            r[md] = {**{k: round(v, 5) for k, v in ikili(p, y).items() if k != "n"}, "ece": kal["ece"],
                     "taban_farki_log_loss": {k: (round(v, 5) if isinstance(v, float) else v) for k, v in fark.items()},
                     "buyuk_sapmali_kutu": buyuk_sapma}
            if 0.02 <= oran <= 0.98:
                r[md]["E1_bilgi_tasiyor"] = fark["ust95"] < 0
                r[md]["E2_kalibre"] = kal["ece"] <= 0.02 and not buyuk_sapma
            else:
                r[md]["karar"] = "yetersiz olay (<%2 ya da >%98)"
        dc = ll([s["dixon_coles"][ad] for s in satirlar]) - ll([s["poisson"][ad] for s in satirlar])
        r["DC_eksi_Poisson"] = {k: (round(v, 5) if isinstance(v, float) else v) for k, v in kume_bootstrap(dc, kume).items()}
        out[ad] = r
    return out


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    oz = on_kayit_dogrula()
    ligler = argv or list(LIGLER)
    tum, lig_ozet = [], {}
    for lig in ligler:
        r = lig_kayitlari(lig)
        tum.extend(r["satirlar"])
        lig_ozet[lig] = {"mac": r["mac"], "son_tarih": r["son_tarih"], "atlanan_sezonlar": r["atlanan_sezonlar"],
                         "tutarsizlik_sayisi": len(r["tutarsizlik"]), "tutarsizlik_ornek": r["tutarsizlik"][:3],
                         "marketler": market_raporu(r["satirlar"])}
    sonuc = {"asama": "E", "on_kayit_sha256": oz, "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "ligler": lig_ozet, "birlesik": market_raporu(tum), "toplam_mac": len(tum)}
    cik = BURASI.parents[2] / "output" / "model" / f"e_asamasi_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    cik.mkdir(parents=True, exist_ok=True)
    (cik / "sonuc.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(cik / "sonuc.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
