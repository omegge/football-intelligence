"""Prototip backtest: tek lig (varsayılan İngiltere Premier Lig, OpenFootball `en.1`).

    PYTHONPATH=lib python3 -m fi.model.calistir [--fdorg] [--cikti output/model]

Dönemler (yalnızca geçmiş sezonlar, hiperparametreler YALNIZCA ayar döneminde seçilir):
  ısınma     : 2010-11 … 2015-16 (Elo; gol modeli penceresi için de geçmiş veri)
  ayar       : 2016-17 … 2018-19
  doğrulama  : 2019-20 … 2021-22
  test       : 2022-23 … 2025-26
  ek test    : 2026-27 (OpenFootball 20.09.2026'ya kadar; `--fdorg` ile sonrası football-data.org ücretsiz plandan)
MK-1: hiçbir girdi Nesine oranı içermez; korner/kart/oyuncu pazarları hesaplanmaz.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from . import pazar_destegi
from .backtest import FrekansModeli, yuruyen_test
from .elo import EloAyar, EloModeli
from .goller import GolModeli, PoissonGorunumu
from .metrikler import (bootstrap_ortalama_fark, brier, ikili, log_loss, maclik_log_loss, rps, sonuc_kalibrasyonu)
from .surpriz import seri_analizi, surpriz_analizi
from ..kaynaklar import openfootball
from ..takim_adlari import TakimEslestirici, normallestir

DONEM = {"ayar": ("2016-17", "2017-18", "2018-19"), "dogrulama": ("2019-20", "2020-21", "2021-22"),
         "test": ("2022-23", "2023-24", "2024-25", "2025-26"), "ek_test": ("2026-27",)}


def _ilk_tarih(maclar, sezon):
    return min(m["tarih"] for m in maclar if m["sezon"] == sezon)


def _son_tarih(maclar, sezon):
    return max(m["tarih"] for m in maclar if m["sezon"] == sezon)


def fdorg_ekle(maclar: list[dict], kaynak: dict) -> tuple[list[dict], dict]:
    """2026-27: OpenFootball'un son tarihinden SONRAKİ bitmiş maçları football-data.org'dan ekler; çakışan dönemde
    skorları karşılaştırır. Takım eşleşmesi yalnızca 'kesin/onaylı' ise kabul edilir."""
    from ..kaynaklar.footballdataorg import ATIF, FdorgIstemcisi, yarisma_maclari
    of_son = max(m["tarih"] for m in maclar)
    fd, meta = yarisma_maclari(FdorgIstemcisi(), "PL", "2026-08-01", datetime.now(timezone.utc).date().isoformat(),
                               status="FINISHED")
    adaylar = sorted({m["ev_ad"] for m in maclar if m["sezon"] in ("2025-26", "2026-27")} |
                     {m["dep_ad"] for m in maclar if m["sezon"] in ("2025-26", "2026-27")})
    es = TakimEslestirici()
    harita, esmeyen = {}, set()
    for ad in {m["ev"] for m in fd} | {m["dep"] for m in fd}:
        r = es.eslestir(ad, "openfootball", adaylar)
        if r.kullanilabilir:
            harita[ad] = normallestir(r.kaynak_adi)
        else:
            esmeyen.add(ad)
    of_2627 = {(m["ev"], m["dep"]): m for m in maclar if m["sezon"] == "2026-27"}
    ayni = farkli = eklenen = atlanan = 0
    for m in fd:
        if m["ev"] not in harita or m["dep"] not in harita or m["normal_sure_ev"] is None:
            atlanan += 1
            continue
        ev, dep = harita[m["ev"]], harita[m["dep"]]
        tarih = m["utc_baslama"][:10]
        o = of_2627.get((ev, dep))
        if o is not None:
            if (o["ev_gol"], o["dep_gol"]) == (m["normal_sure_ev"], m["normal_sure_dep"]):
                ayni += 1
            else:
                farkli += 1
            continue
        if tarih <= of_son:
            atlanan += 1
            continue
        maclar.append({"sezon": "2026-27", "tarih": tarih, "saat": m["utc_baslama"][11:16], "tur": m["hafta"],
                       "ev": ev, "dep": dep, "ev_ad": m["ev"], "dep_ad": m["dep"], "ev_gol": m["normal_sure_ev"],
                       "dep_gol": m["normal_sure_dep"], "iy_ev": m["iy_ev"], "iy_dep": m["iy_dep"],
                       "kaynak": "football-data.org"})
        eklenen += 1
    maclar.sort(key=lambda m: (m["tarih"], m.get("saat") or "", m["ev"]))
    return maclar, {"istek_url": meta["url"], "erisim_utc": meta["erisim_utc"], "onbellekten": meta.get("onbellekten"),
                    "sha256": meta.get("sha256"), "fdorg_bitmis_mac": len(fd), "cakisan_ayni_skor": ayni,
                    "cakisan_farkli_skor": farkli, "eklenen": eklenen, "atlanan": atlanan,
                    "eslesmeyen_takimlar": sorted(esmeyen), "openfootball_son_tarih": of_son, "atif": ATIF}


def ozet(kayitlar: list[dict], modeller: list[str], taban: str = "taban") -> dict:
    out = {"n": len(kayitlar)}
    if not kayitlar:
        return out
    y = [k["sonuc"] for k in kayitlar]
    ll_taban = maclik_log_loss([k["tahmin"][taban] for k in kayitlar], y)
    for md in modeller:
        P = [k["tahmin"][md] for k in kayitlar]
        r = {"log_loss": round(log_loss(P, y), 4), "brier": round(brier(P, y), 4), "rps": round(rps(P, y), 4),
             "kalibrasyon_ece": {k: v["ece"] for k, v in sonuc_kalibrasyonu(P, y).items()}}
        if md != taban:
            b = bootstrap_ortalama_fark(maclik_log_loss(P, y), ll_taban)
            r["log_loss_fark_tabana_gore"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in b.items()}
        if "ust25" in P[0]:
            r["ust25"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in
                          ikili([p["ust25"] for p in P], [k["ev_gol"] + k["dep_gol"] >= 3 for k in kayitlar]).items()}
            r["kg_var"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in
                           ikili([p["kg_var"] for p in P], [k["ev_gol"] > 0 and k["dep_gol"] > 0 for k in kayitlar]).items()}
        r["beraberlik"] = {"ort_tahmin": round(sum(p["D"] for p in P) / len(P), 4),
                           "gerceklesen": round(sum(1 for s in y if s == "D") / len(y), 4),
                           "en_olasi_sonuc_beraberlik_sayisi": sum(1 for p in P if p["D"] >= max(p["H"], p["A"]))}
        out[md] = r
    return out


def ayar_yap(maclar, takimlar, bas, bit) -> dict:
    sonuc = {"elo": [], "gol": []}
    for k in (15, 20, 30):
        for h in (50, 70):
            for c in (0.15, 0.3):
                e = EloModeli(EloAyar(k=k, ev_avantaji=h, sezon_cekimi=c))
                kay = yuruyen_test(maclar, [e], bas, bit, takimlar)
                sonuc["elo"].append({"k": k, "ev_avantaji": h, "sezon_cekimi": c,
                                     "log_loss": round(log_loss([x["tahmin"]["elo"] for x in kay], [x["sonuc"] for x in kay]), 5)})
    for xi in (0.0015, 0.003):
        g = GolModeli(xi=xi)
        kay = yuruyen_test(maclar, [g], bas, bit, takimlar)
        sonuc["gol"].append({"xi": xi, "log_loss": round(log_loss([x["tahmin"]["dixon_coles"] for x in kay],
                                                                   [x["sonuc"] for x in kay]), 5)})
    sonuc["elo_secilen"] = min(sonuc["elo"], key=lambda r: r["log_loss"])
    sonuc["gol_secilen"] = min(sonuc["gol"], key=lambda r: r["log_loss"])
    return sonuc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lig", default="en.1")
    ap.add_argument("--fdorg", action="store_true", help="2026-27 için football-data.org ücretsiz plan (tek istek, önbellekli)")
    ap.add_argument("--cikti", default=str(Path(__file__).resolve().parents[3] / "output" / "model"))
    a = ap.parse_args(argv)
    t0 = time.time()
    maclar, kaynak = openfootball.lig_oku(a.lig)
    fd_bilgi = None
    if a.fdorg:
        maclar, fd_bilgi = fdorg_ekle(maclar, kaynak)
    takimlar = openfootball.sezon_takimlari(maclar)
    sezonlar = sorted(takimlar)
    ayar = ayar_yap(maclar, takimlar, _ilk_tarih(maclar, DONEM["ayar"][0]), _son_tarih(maclar, DONEM["ayar"][-1]))
    es, gs = ayar["elo_secilen"], ayar["gol_secilen"]
    elo = EloModeli(EloAyar(k=es["k"], ev_avantaji=es["ev_avantaji"], sezon_cekimi=es["sezon_cekimi"]))
    dc = GolModeli(xi=gs["xi"])
    modeller = [FrekansModeli(), elo, dc, PoissonGorunumu(dc)]
    kay = yuruyen_test(maclar, modeller, _ilk_tarih(maclar, DONEM["dogrulama"][0]), None, takimlar, elo_kaydi=elo)
    elo_gecmis = yuruyen_test.elo_gecmisi
    adlar = ["taban", "elo", "poisson", "dixon_coles"]
    rapor = {"olusturma_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "lig": a.lig,
             "veri": {k: v for k, v in kaynak.items() if k != "dosya_sha256"}, "fdorg": fd_bilgi,
             "sezonlar": sezonlar, "donemler": DONEM, "ayar": ayar,
             "desteklenmeyen_pazarlar": [pazar_destegi(p) for p in ("korner", "kart", "oyuncu")],
             "sure_sn": None, "donem_sonuclari": {}, "sezon_log_loss": {}}
    for ad, ss in DONEM.items():
        if ad == "ayar":
            continue
        rapor["donem_sonuclari"][ad] = ozet([k for k in kay if k["sezon"] in ss], adlar)
    for s in sorted({k["sezon"] for k in kay}):
        ks = [k for k in kay if k["sezon"] == s]
        rapor["sezon_log_loss"][s] = {md: round(log_loss([k["tahmin"][md] for k in ks], [k["sonuc"] for k in ks]), 4)
                                      for md in adlar} | {"n": len(ks)}
    test = [k for k in kay if k["sezon"] in DONEM["test"] + DONEM["ek_test"]]
    rapor["test_kalibrasyon"] = {md: sonuc_kalibrasyonu([k["tahmin"][md] for k in test], [k["sonuc"] for k in test])
                                 for md in ("elo", "dixon_coles")}
    rapor["surpriz"] = {md: surpriz_analizi(test, md) for md in ("elo", "dixon_coles")}
    rapor["seri"] = {md: seri_analizi(test, md, elo_gecmis) for md in ("elo", "dixon_coles")}
    yeni = {s: takimlar[s] - takimlar[o] for o, s in zip(sezonlar, sezonlar[1:])}
    yk = [k for k in test if k["ev"] in yeni.get(k["sezon"], set()) or k["dep"] in yeni.get(k["sezon"], set())]
    dk = [k for k in test if k not in yk]
    rapor["yeni_takim_etkisi"] = {grup: {md: round(log_loss([k["tahmin"][md] for k in g], [k["sonuc"] for k in g]), 4)
                                         for md in adlar} | {"n": len(g)} for grup, g in (("yeni_takimli", yk), ("digerleri", dk))}
    ll = maclik_log_loss([k["tahmin"]["dixon_coles"] for k in test], [k["sonuc"] for k in test])
    en_kotu = sorted(range(len(test)), key=lambda i: -ll[i])[:12]
    rapor["en_buyuk_hatalar"] = [{"tarih": test[i]["tarih"], "mac": f"{test[i]['ev_ad']} {test[i]['ev_gol']}-{test[i]['dep_gol']} {test[i]['dep_ad']}",
                                  "dixon_coles": {s: round(test[i]["tahmin"]["dixon_coles"][s], 3) for s in "HDA"},
                                  "elo": {s: round(test[i]["tahmin"]["elo"][s], 3) for s in "HDA"},
                                  "kaynak": test[i]["kaynak"]} for i in en_kotu]
    rapor["sure_sn"] = round(time.time() - t0, 1)
    cikti = Path(a.cikti) / f"{a.lig.replace('.', '')}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
    cikti.mkdir(parents=True, exist_ok=True)
    (cikti / "rapor.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(cikti / "tahminler.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tarih", "sezon", "ev", "dep", "ev_gol", "dep_gol", "sonuc", "kaynak", "egitim_kesimi"] +
                   [f"{md}_{s}" for md in adlar for s in "HDA"] + ["dc_ust25", "dc_kg_var"])
        for k in kay:
            w.writerow([k["tarih"], k["sezon"], k["ev_ad"], k["dep_ad"], k["ev_gol"], k["dep_gol"], k["sonuc"], k["kaynak"],
                        k["egitim_kesimi"]] + [round(k["tahmin"][md][s], 4) for md in adlar for s in "HDA"] +
                       [round(k["tahmin"]["dixon_coles"]["ust25"], 4), round(k["tahmin"]["dixon_coles"]["kg_var"], 4)])
    print(json.dumps({"cikti": str(cikti), "sure_sn": rapor["sure_sn"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
