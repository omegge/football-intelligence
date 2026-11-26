"""D aşaması: Avrupa kupaları için ligler arası güç karşılaştırması — PROTOTİP.

ÖN KAYIT (kod bu haliyle tek kez çalıştırıldı; parametreler test verisine bakılarak değiştirilmez)
------------------------------------------------------------------------------------------------
Soru: Ligler arası güç farkı, kulüpler arası Avrupa maçlarından öğrenilerek aktarılırsa (M1), ligleri eşit varsayan
ayrı lig Elo'suna (B1) ve sabit taban orana (B0) göre UCL maçlarında daha iyi olasılık verir mi?

Veri: OpenFootball (CC0). Yurt içi: üst ligler (ULKE_LIGI). Avrupa: uefa.cl (yalnızca grup/lig ve eleme turları;
ön eleme YOK; 2020-21…2023-24 kaynakta YOK). Sert tarih tutarsızlığı olan sezonlar okunmaz ve raporlanır.
Takım eşleme: UCL adı 'Ad (ÜLK)' → aynı ülke ve sezonun yurt içi adlarıyla YALNIZCA 'kesin' (normalleştirilmiş birebir)
eşleşme. Eşleşmeyen takım yalnızca Avrupa maçlarıyla puanlanır (M1) ve B1'de "hesaplanamaz"dır.

Modeller (EloAyar varsayılanları: K=20, H=60, sezon çekimi 0.2, başlangıç 1500; değiştirilmedi):
  B0  taban     : geçmiş UCL sezonlarındaki H/D/A sıklıkları.
  B1  ayrı_lig  : her lig kendi havuzu; Avrupa maçı puanı GÜNCELLEMEZ (lig seviyeleri eşit varsayılır).
  M1  ortak_elo : tek havuz; Avrupa maçları da aynı K ile günceller → lig ortalamaları Avrupa sonuçlarıyla kayar.
Her iki Elo modelinde 1X2, sıralı lojistikle YALNIZCA geçmiş UCL sezonlarının maç öncesi farklarından kestirilir.
Final tarafsız sahada: ev avantajı 0. Isınma: ilk iki UCL sezonu (2011-12, 2012-13) değerlendirilmez.
Ölçüt: log loss (birincil), Brier, RPS; tarih kümeli bootstrap ile fark güven aralığı. Alt gruplar: büyük-5 lig takımı ile
diğer lig takımı karşılaşmaları (ligler arası dengesizlik), aynı-büyük-5, ikisi de diğer.

MK-1: bahis oranı hiçbir yerde okunmaz; olasılıklar yalnızca sonuçlardan.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict

import numpy as np

from ..kaynaklar import openfootball as O
from ..takim_adlari import TakimEslestirici
from .elo import EloAyar, SiraliLojistik, gol_carpani
from .degerlendirme import kume_bootstrap
from . import metrikler as M

SURUM = "ligler-arasi-0.1"
ULKE_LIGI = {"ENG": "en.1", "ESP": "es.1", "GER": "de.1", "ITA": "it.1", "FRA": "fr.1", "NED": "nl.1", "POR": "pt.1",
             "TUR": "tr.1", "BEL": "be.1", "SCO": "sco.1", "AUT": "at.1", "SUI": "ch.1", "GRE": "gr.1", "RUS": "ru.1",
             "CZE": "cz.1", "HUN": "hu.1"}
BUYUK5 = {"en.1", "es.1", "de.1", "it.1", "fr.1"}
ISINMA = {"2011-12", "2012-13"}
UCL_AD = re.compile(r"^(.*)\s+\(([A-Z]{3})\)$")


def _sezon_sezon_oku(lig: str) -> tuple[list[dict], list[dict]]:
    """Ligi sezon sezon okur; sert tutarsızlığı olan sezonu atlar ve nedenini döndürür."""
    maclar, atlanan = [], []
    sezonlar = sorted(p.name for p in O.KOK.iterdir() if p.is_dir() and O.SEZON_DESENI.fullmatch(p.name)
                      and (p / f"{lig}.json").exists())
    for s in sezonlar:
        try:
            ms, _ = O.lig_oku(lig, sezonlar=[s])
        except O.VeriTutarsizligi as e:
            atlanan.append({"lig": lig, "sezon": s, "neden": str(e)[:300]})
            continue
        for m in ms:
            m["lig"] = lig
        maclar.extend(ms)
    return maclar, atlanan


def veri_yukle() -> dict:
    yurt_ici, atlanan = [], []
    for lig in ULKE_LIGI.values():
        ms, a = _sezon_sezon_oku(lig)
        yurt_ici.extend(ms)
        atlanan.extend(a)
    ucl, _ = O.lig_oku("uefa.cl")
    adlar = defaultdict(set)  # (ülke, sezon) -> yurt içi ham adlar
    anahtar = {}
    for m in yurt_ici:
        u = next(k for k, v in ULKE_LIGI.items() if v == m["lig"])
        for ad, k in ((m["ev_ad"], m["ev"]), (m["dep_ad"], m["dep"])):
            adlar[(u, m["sezon"])].add(ad)
            anahtar[(u, ad)] = k
    E = TakimEslestirici()
    esleme_durumu = defaultdict(int)
    eslenmeyen = set()
    for m in ucl:
        m["lig"] = "uefa.cl"
        for taraf in ("ev", "dep"):
            ham = m[f"{taraf}_ad"]
            mm = UCL_AD.match(ham)
            ulke = mm.group(2) if mm else None
            ad = mm.group(1) if mm else ham
            m[f"{taraf}_ulke"] = ulke
            m[f"{taraf}_yurt_ici_lig"] = None
            aday = sorted(adlar.get((ulke, m["sezon"]), ()))
            if ulke in ULKE_LIGI and aday:
                e = E.eslestir(ad, "openfootball", aday)
                if e.durum in ("kesin", "onayli"):
                    m[taraf] = anahtar[(ulke, e.kaynak_adi)]
                    m[f"{taraf}_yurt_ici_lig"] = ULKE_LIGI[ulke]
                    esleme_durumu["kesin"] += 1
                    continue
                esleme_durumu[e.durum] += 1
            else:
                esleme_durumu["ulke_ya_da_sezon_verisi_yok"] += 1
            m[taraf] = "avrupa:" + m[taraf]
            eslenmeyen.add((ham, m["sezon"]))
    return {"yurt_ici": yurt_ici, "ucl": ucl, "atlanan_sezonlar": atlanan,
            "esleme_durumu": dict(esleme_durumu), "eslenmeyen_takim_sezon": sorted(eslenmeyen)}


class GenelElo:
    """Lig havuzlu Elo. aktarim=True ise Avrupa maçları da günceller (M1); False ise güncellemez (B1)."""

    def __init__(self, aktarim: bool, ayar: EloAyar | None = None):
        self.aktarim = aktarim
        self.a = ayar or EloAyar()
        self.puan: dict[str, float] = {}
        self.lig_takimlari: dict[str, set] = {}   # lig -> son sezon takımları
        self.lig_sezonu: dict[str, str] = {}

    def lig_sezon_basla(self, lig: str, sezon: str, takimlar: set):
        once = self.lig_takimlari.get(lig, set())
        if once:
            ort = sum(self.puan[t] for t in once) / len(once)
            for t in once:
                self.puan[t] = ort + (1 - self.a.sezon_cekimi) * (self.puan[t] - ort)
            ayrilan = once - takimlar
            yeni = sum(self.puan[t] for t in ayrilan) / len(ayrilan) if ayrilan else ort
        else:
            yeni = self.a.baslangic
        for t in takimlar:
            if t not in once:
                self.puan[t] = yeni
        self.lig_takimlari[lig] = set(takimlar)
        self.lig_sezonu[lig] = sezon

    def x(self, ev: str, dep: str, tarafsiz: bool) -> float | None:
        if ev not in self.puan or dep not in self.puan:
            return None
        h = 0.0 if tarafsiz else self.a.ev_avantaji
        return (self.puan[ev] + h - self.puan[dep]) / 400.0

    def isle(self, m: dict, avrupa: bool, tarafsiz: bool = False):
        if avrupa:
            if not self.aktarim:
                return
            for t in (m["ev"], m["dep"]):
                self.puan.setdefault(t, self.a.baslangic)   # yalnızca Avrupa'dan bilinen takım (varsayım; raporlanır)
        x = self.x(m["ev"], m["dep"], tarafsiz)
        e = 1 / (1 + 10 ** (-x))
        g = m["ev_gol"] - m["dep_gol"]
        s = 1.0 if g > 0 else (0.5 if g == 0 else 0.0)
        d = self.a.k * gol_carpani(g) * (s - e)
        self.puan[m["ev"]] += d
        self.puan[m["dep"]] -= d


def _sonuc(m) -> str:
    g = m["ev_gol"] - m["dep_gol"]
    return "H" if g > 0 else ("D" if g == 0 else "A")


def _tarafsiz(m) -> bool:
    t = (m.get("tur") or "").strip().casefold()
    return t == "final" or t.endswith(", final")


def calistir(veri: dict | None = None) -> dict:
    veri = veri or veri_yukle()
    olaylar = [(m["tarih"], 0, m) for m in veri["yurt_ici"]] + [(m["tarih"], 1, m) for m in veri["ucl"]]
    olaylar.sort(key=lambda t: (t[0], t[1]))
    modeller = {"B1_ayri_lig": GenelElo(False), "M1_ortak_elo": GenelElo(True)}
    sezon_takim = defaultdict(set)
    for m in veri["yurt_ici"]:
        sezon_takim[(m["lig"], m["sezon"])].update((m["ev"], m["dep"]))
    baslamis = set()
    gecmis = {k: [] for k in modeller}       # (x, sonuç, sezon) — yalnızca UCL
    gecmis_sonuc = []                         # (sonuç, sezon) — B0
    donusum = {k: SiraliLojistik() for k in modeller}
    ucl_sezon = None
    kayitlar = []
    for tarih, tur, m in olaylar:
        if tur == 0:
            key = (m["lig"], m["sezon"])
            if key not in baslamis:
                for mod in modeller.values():
                    mod.lig_sezon_basla(m["lig"], m["sezon"], sezon_takim[key])
                baslamis.add(key)
            for mod in modeller.values():
                mod.isle(m, avrupa=False)
            continue
        # UCL maçı
        if m["sezon"] != ucl_sezon:
            ucl_sezon = m["sezon"]
            for k in modeller:
                donusum[k] = SiraliLojistik().kestir([(x, y) for x, y, s in gecmis[k] if s != ucl_sezon])
        taraf = _tarafsiz(m)
        y = _sonuc(m)
        kayit = {"sezon": m["sezon"], "tarih": m["tarih"], "tur": m.get("tur"), "ev_ad": m["ev_ad"],
                 "dep_ad": m["dep_ad"], "sonuc": y, "tarafsiz": taraf,
                 "ev_lig": m.get("ev_yurt_ici_lig"), "dep_lig": m.get("dep_yurt_ici_lig")}
        onceki = [s for s, sz in gecmis_sonuc if sz != m["sezon"]]
        if len(onceki) >= 100:
            n = len(onceki)
            kayit["B0_taban"] = {r: onceki.count(r) / n for r in M.SONUCLAR}
        for k, mod in modeller.items():
            x = mod.x(m["ev"], m["dep"], taraf)
            yurt_ici_ikisi = kayit["ev_lig"] is not None and kayit["dep_lig"] is not None
            if x is None or (k == "B1_ayri_lig" and not yurt_ici_ikisi):
                kayit[k] = None              # hesaplanamaz
            else:
                kayit[k] = donusum[k].olasilik(x)
                kayit[k + "_x"] = x
                gecmis[k].append((x, y, m["sezon"]))
        kayitlar.append(kayit)
        gecmis_sonuc.append((y, m["sezon"]))
        for mod in modeller.values():
            mod.isle(m, avrupa=True, tarafsiz=taraf)
    return {"veri": {k: v for k, v in veri.items() if k not in ("yurt_ici", "ucl")} | {
        "yurt_ici_mac": len(veri["yurt_ici"]), "ucl_mac": len(veri["ucl"])},
            "kayitlar": kayitlar, "modeller": modeller}


def _grup(k: dict) -> str:
    a, b = k["ev_lig"], k["dep_lig"]
    if a is None or b is None:
        return "en_az_biri_yurt_ici_verisiz"
    if (a in BUYUK5) != (b in BUYUK5):
        return "buyuk5_vs_diger"
    if a in BUYUK5:
        return "buyuk5_vs_buyuk5"
    return "diger_vs_diger"


def degerlendir(sonuc: dict) -> dict:
    ks = [k for k in sonuc["kayitlar"] if k["sezon"] not in ISINMA]
    modeller = ["B0_taban", "B1_ayri_lig", "M1_ortak_elo"]
    rapor = {"degerlendirme_maci": len(ks), "kapsam": {}, "ortak_kume": {}, "alt_gruplar": {}, "farklar": {}}
    for md in modeller:
        rapor["kapsam"][md] = sum(1 for k in ks if k.get(md))
    ortak = [k for k in ks if all(k.get(md) for md in modeller)]

    def olc(kume, md):
        p = [k[md] for k in kume]
        y = [k["sonuc"] for k in kume]
        return {"n": len(kume), "log_loss": round(M.log_loss(p, y), 4), "brier": round(M.brier(p, y), 4),
                "rps": round(M.rps(p, y), 4)}
    rapor["ortak_kume"] = {md: olc(ortak, md) for md in modeller}
    for g in ("buyuk5_vs_diger", "buyuk5_vs_buyuk5", "diger_vs_diger"):
        kume = [k for k in ortak if _grup(k) == g]
        if len(kume) >= 30:
            rapor["alt_gruplar"][g] = {md: olc(kume, md) for md in modeller}
        else:
            rapor["alt_gruplar"][g] = {"n": len(kume), "not": "örneklem < 30: ölçüm raporlanmaz"}
    yalniz_m1 = [k for k in ks if k.get("M1_ortak_elo") and not k.get("B1_ayri_lig") and k.get("B0_taban")]
    rapor["yalniz_M1_tanimli"] = {md: olc(yalniz_m1, md) for md in ("B0_taban", "M1_ortak_elo")} if len(yalniz_m1) >= 30 \
        else {"n": len(yalniz_m1)}
    kume_ids = [k["tarih"] for k in ortak]
    y = [k["sonuc"] for k in ortak]
    for a, b in (("M1_ortak_elo", "B1_ayri_lig"), ("M1_ortak_elo", "B0_taban"), ("B1_ayri_lig", "B0_taban")):
        fa = M.maclik_log_loss([k[a] for k in ortak], y)
        fb = M.maclik_log_loss([k[b] for k in ortak], y)
        rapor["farklar"][f"{a} - {b} (log loss)"] = kume_bootstrap(fa - fb, kume_ids)
    # Kalibrasyon: güçlü tarafın (M1'e göre) kazanma olasılığı vs gözlenen, büyük5_vs_diger dahil
    for md in ("B1_ayri_lig", "M1_ortak_elo"):
        p = [k[md]["H"] for k in ortak]
        rapor.setdefault("kalibrasyon_ev_galibiyeti", {})[md] = M.kalibrasyon(np.array(p),
                                                                              np.array([k["sonuc"] == "H" for k in ortak]),
                                                                              kutu=5)
    # Ligler arası dengesizlik: büyük5 takımının diğer lig takımına karşı gözlenen ve modelin verdiği puan ortalaması
    bd = [k for k in ortak if _grup(k) == "buyuk5_vs_diger"]
    if bd:
        def b5_puan(k, p=None):
            ev_b5 = k["ev_lig"] in BUYUK5
            if p is None:
                s = {"H": 1.0, "D": 0.5, "A": 0.0}[k["sonuc"]]
            else:
                s = p["H"] + 0.5 * p["D"]
            return s if ev_b5 else 1 - s
        rapor["buyuk5_beklenen_puan"] = {"gozlenen": round(float(np.mean([b5_puan(k) for k in bd])), 4),
                                         **{md: round(float(np.mean([b5_puan(k, k[md]) for k in bd])), 4)
                                            for md in modeller}, "n": len(bd)}
    return rapor


def lig_seviyeleri(model: GenelElo) -> dict:
    """Son sezon takımlarının ortalama puanı (M1'de Avrupa sonuçlarıyla kayan lig seviyesi)."""
    return {lig: {"ortalama": round(float(np.mean([model.puan[t] for t in ts])), 1), "takim": len(ts),
                  "sezon": model.lig_sezonu.get(lig)}
            for lig, ts in sorted(model.lig_takimlari.items())}
