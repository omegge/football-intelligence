"""D aşaması (model güvenilirliği) çalıştırıcısı.

    PYTHONPATH=lib python3 -m fi.model.d_asamasi gelistirme
    PYTHONPATH=lib python3 -m fi.model.d_asamasi on_kayit --gelistirme-raporu <json>
    PYTHONPATH=lib python3 -m fi.model.d_asamasi dogrulama

Veri ayrımı (kullanıcı kuralı 5: sonuçlarını gördüğümüz dönemler kör test sayılmaz):
- GELİŞTİRME (karar verisi, kör DEĞİL): en.1 2016-17 … 2021-22.
- ÖNSEL KESTİRİMİ: her lig için yalnızca değerlendirme başlangıcından ÖNCEKİ sezonlar.
- DOĞRULAMA (daha önce hiç değerlendirilmemiş, önceden kayıtlı): de.1, es.1, it.1 2022-23 … 2025-26.
  `dogrulama` yalnızca `ON_KAYIT_D.md` var ve SHA-256 özeti `ON_KAYIT_D.sha256` ile tutuyorsa çalışır.
- en.1 2022-23 … 2026-27 bu aşamada HİÇ kullanılmaz (önceden görüldü).
MK-1: girdiler yalnızca OpenFootball skorları; oran yok.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .backtest import yuruyen_test
from .degerlendirme import dusuk_skor_analizi, eslestirilmis, kume_bootstrap, yeni_takim_onseli
from .goller import GolModeli, PoissonGorunumu
from .metrikler import log_loss, maclik_log_loss
from ..kaynaklar import openfootball

BURASI = Path(__file__).resolve().parent
ON_KAYIT = BURASI / "ON_KAYIT_D.md"
ON_KAYIT_OZET = BURASI / "ON_KAYIT_D.sha256"
CIKTI_KOK = BURASI.parents[2] / "output" / "model"
XI = 0.003                                     # önceki ayar döneminde (2016-17…2018-19) seçildi
GELISTIRME = {"lig": "en.1", "sezonlar": ["2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22"]}
DOGRULAMA = {"ligler": ["de.1", "es.1", "it.1"], "sezonlar": ["2022-23", "2023-24", "2024-25", "2025-26"]}
SABIT_ONSEL = (0.8, 1.2)


def _calis(maclar, takimlar, bas, bit, onsel):
    dc = GolModeli(xi=XI, yeni_hucum=onsel[0], yeni_savunma=onsel[1])
    kay = yuruyen_test(maclar, [dc, PoissonGorunumu(dc)], bas, bit, takimlar)
    assert all(k["egitim_kesimi"] is None or k["egitim_kesimi"] < k["tarih"] for k in kay)
    return kay


def _yeni_takim_maclari(kay, takimlar, ilk_n=10):
    sezonlar = sorted(takimlar)
    yeni = {s: takimlar[s] - takimlar[sezonlar[i - 1]] for i, s in enumerate(sezonlar) if i}
    sayac: dict = {}
    tum, ilk = [], []
    for i, k in enumerate(kay):
        ys = yeni.get(k["sezon"], set())
        ilgili = [t for t in (k["ev"], k["dep"]) if t in ys]
        if not ilgili:
            continue
        tum.append(i)
        erken = False
        for t in ilgili:
            sayac[(k["sezon"], t)] = sayac.get((k["sezon"], t), 0) + 1
            erken |= sayac[(k["sezon"], t)] <= ilk_n
        if erken:
            ilk.append(i)
    return tum, ilk


def _onsel_karsilastir(kay_a, kay_b, idx, model="dixon_coles"):
    if not idx:
        return {"n_mac": 0}
    a = [kay_a[i] for i in idx]
    b = [kay_b[i] for i in idx]
    y = [k["sonuc"] for k in a]
    la = maclik_log_loss([k["tahmin"][model] for k in a], y)
    lb = maclik_log_loss([k["tahmin"][model] for k in b], y)
    r = kume_bootstrap(la - lb, [k["tarih"] for k in a])
    return {k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()}


def lig_degerlendir(lig: str, sezonlar: list[str], onsel_secimi: str = "hepsi") -> dict:
    maclar, kaynak = openfootball.lig_oku(lig)
    takimlar = openfootball.sezon_takimlari(maclar)
    bas = min(m["tarih"] for m in maclar if m["sezon"] == sezonlar[0])
    bit = max(m["tarih"] for m in maclar if m["sezon"] == sezonlar[-1])
    onceki = [s for s in sorted(takimlar) if s < sezonlar[0]]
    tahmini = yeni_takim_onseli(maclar, onceki)                   # yalnızca değerlendirmeden ÖNCEKİ sezonlar
    varyant = {"V0_sabit": SABIT_ONSEL, "V1_gecmisten": (tahmini["hucum"], tahmini["savunma"]), "V2_notr": (1.0, 1.0)}
    if onsel_secimi != "hepsi":
        varyant = {k: v for k, v in varyant.items() if k in ("V0_sabit", onsel_secimi)}
    kay = {ad: _calis(maclar, takimlar, bas, bit, o) for ad, o in varyant.items()}
    k0 = kay["V0_sabit"]
    y = [k["sonuc"] for k in k0]
    tum, ilk = _yeni_takim_maclari(k0, takimlar)
    sonuc = {"lig": lig, "veri_commit": kaynak["commit"], "sezonlar": sezonlar, "n_mac": len(k0),
             "onsel_kestirimi": tahmini, "varyantlar": {k: list(v) for k, v in varyant.items()},
             "log_loss": {ad: {md: round(log_loss([k["tahmin"][md] for k in kk], y), 5) for md in ("poisson", "dixon_coles")}
                          for ad, kk in kay.items()},
             "dc_eksi_poisson": eslestirilmis(k0, "dixon_coles", "poisson"),
             "dusuk_skor": dusuk_skor_analizi(k0),
             "yeni_takim": {"n_mac_tum": len(tum), "n_mac_ilk10": len(ilk),
                            **{f"{ad}_eksi_V0": {"tum_sezon": _onsel_karsilastir(kk, k0, tum),
                                                 "ilk10_mac": _onsel_karsilastir(kk, k0, ilk)}
                               for ad, kk in kay.items() if ad != "V0_sabit"}},
             "sizinti_denetimi": {"egitim_kesimi_tahminden_once": True,
                                  "onsel_kaynak_sezonlari_degerlendirmeden_once": all(s < sezonlar[0] for s in tahmini["sezonlar"])}}
    return sonuc


def _yaz(ad: str, veri: dict) -> Path:
    d = CIKTI_KOK / f"d_asamasi_{ad}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "rapor.json").write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def on_kayit_ozeti() -> str:
    return hashlib.sha256(ON_KAYIT.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("gelistirme")
    alt.add_parser("dogrulama")
    a = ap.parse_args(argv)
    if a.komut == "gelistirme":
        r = lig_degerlendir(GELISTIRME["lig"], GELISTIRME["sezonlar"])
        r["etiket"] = "GELİŞTİRME VERİSİ — kör test değildir"
        print(json.dumps({"cikti": str(_yaz("gelistirme", r))}, ensure_ascii=False))
        return 0
    if not ON_KAYIT.exists() or not ON_KAYIT_OZET.exists():
        raise SystemExit("Önceden kayıt (ON_KAYIT_D.md + .sha256) yok; doğrulama çalıştırılmaz.")
    kayitli = ON_KAYIT_OZET.read_text(encoding="utf-8").split()[0]
    if kayitli != on_kayit_ozeti():
        raise SystemExit("ON_KAYIT_D.md değişmiş (SHA-256 tutmuyor); doğrulama çalıştırılmaz.")
    secim = next((l.split("`")[1] for l in ON_KAYIT.read_text(encoding="utf-8").splitlines()
                  if l.startswith("- Seçilen önsel varyantı:")), "V0_sabit")
    r = {"on_kayit_sha256": kayitli, "etiket": "DOĞRULAMA — önceden kayıtlı, ilk kez değerlendiriliyor",
         "ligler": {lig: lig_degerlendir(lig, DOGRULAMA["sezonlar"], secim) for lig in DOGRULAMA["ligler"]}}
    print(json.dumps({"cikti": str(_yaz("dogrulama", r))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
