"""D1-D8: model testleri (ağsız, sentetik veri). Gerçek ağ çağrısı test boyunca kilitlidir."""
import json
import math
import random
import shutil
import sys
import tempfile
import unittest
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import numpy as np

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "lib"))

from fi import girdi                                                    # noqa: E402
from fi.kaynaklar import openfootball                                   # noqa: E402
from fi.model import pazar_destegi                                      # noqa: E402
from fi.model.backtest import FrekansModeli, sonuc_kodu, yuruyen_test   # noqa: E402
from fi.model.elo import EloAyar, EloModeli, SiraliLojistik, gol_carpani  # noqa: E402
from fi.model.goller import (GolModeli, PoissonGorunumu, pazarlar, rho_kestir, rho_sinirlari,  # noqa: E402
                             skor_matrisi, tau)
from fi.model.metrikler import auc, bootstrap_ortalama_fark, brier, kalibrasyon, log_loss, rps  # noqa: E402
from fi.model.optim import altin_oran, nelder_mead                      # noqa: E402
from fi.model.surpriz import seri_analizi, surpriz_analizi              # noqa: E402


def _ag_yasak(*a, **k):
    raise AssertionError("Test sırasında gerçek ağ çağrısı yapıldı!")


def sentetik_lig(sezon_sayisi=3, takim=10, tohum=3, hucum=None, savunma=None, ev=0.25):
    """Bilinen parametrelerle çift devreli lig. Döndürür: maçlar, gerçek parametreler."""
    rng = np.random.default_rng(tohum)
    adlar = [f"t{i}" for i in range(takim)]
    hucum = hucum if hucum is not None else rng.normal(0, 0.3, takim)
    savunma = savunma if savunma is not None else rng.normal(0, 0.3, takim)
    hucum, savunma = hucum - hucum.mean(), savunma - savunma.mean()
    maclar, gun = [], date(2015, 8, 1)
    for s in range(sezon_sayisi):
        sezon = f"{2015 + s}-{(16 + s) % 100:02d}"
        eslesmeler = [(i, j) for i in range(takim) for j in range(takim) if i != j]
        random.Random(tohum + s).shuffle(eslesmeler)
        for k, (i, j) in enumerate(eslesmeler):
            t = gun + timedelta(days=k // (takim // 2) * 3)
            lh = math.exp(0.1 + ev + hucum[i] + savunma[j])
            la = math.exp(0.1 + hucum[j] + savunma[i])
            maclar.append({"sezon": sezon, "tarih": t.isoformat(), "saat": None, "ev": adlar[i], "dep": adlar[j],
                           "ev_ad": adlar[i], "dep_ad": adlar[j], "ev_gol": int(rng.poisson(lh)),
                           "dep_gol": int(rng.poisson(la))})
        gun = t + timedelta(days=60)
    return maclar, {"hucum": hucum, "savunma": savunma, "ev": ev}


class Temel(unittest.TestCase):
    def setUp(self):
        self._eski = urllib.request.urlopen
        urllib.request.urlopen = _ag_yasak
        self.tmp = Path(tempfile.mkdtemp(prefix="fi_model_"))

    def tearDown(self):
        urllib.request.urlopen = self._eski
        shutil.rmtree(self.tmp, ignore_errors=True)


class D1OpenFootball(Temel):
    def test_okuyucu_bicimler_ve_normallestirme(self):
        for s, ms in (("2024-25", [{"date": "2024-08-17", "team1": "Arsenal FC", "team2": "Chelsea FC",
                                    "score": {"ft": [2, 1], "ht": [1, 0]}},
                                   {"date": "2024-08-18", "team1": "Aston Villa", "team2": "Arsenal FC", "score": [0, 0]},
                                   {"date": "2024-08-19", "team1": "A", "team2": "B"}]),           # skorsuz -> atlanır
                      ("2025-26", [{"date": "2025-08-16", "team1": "Arsenal", "team2": "Aston Villa FC",
                                    "score": {"ft": [3, 3]}}])):
            (self.tmp / s).mkdir()
            (self.tmp / s / "en.1.json").write_text(json.dumps({"name": "x", "matches": ms}), encoding="utf-8")
        maclar, kaynak = openfootball.lig_oku("en.1", self.tmp)
        self.assertEqual(len(maclar), 3)
        self.assertEqual(kaynak["skorsuz_atlanan"], 1)
        self.assertEqual({m["ev"] for m in maclar} | {m["dep"] for m in maclar}, {"arsenal", "chelsea", "aston villa"})
        self.assertEqual(maclar[0]["iy_ev"], 1)
        self.assertIsNone(maclar[1]["iy_ev"])
        self.assertEqual(set(kaynak["dosya_sha256"]), {"2024-25", "2025-26"})
        self.assertEqual(openfootball.sezon_takimlari(maclar)["2025-26"], {"arsenal", "aston villa"})


class D2Optimizasyon(Temel):
    def test_nelder_mead_ve_altin_oran(self):
        x, f = nelder_mead(lambda p: (p[0] - 1.5) ** 2 + (p[1] + 2) ** 2 + 3, [0.0, 0.0])
        self.assertAlmostEqual(x[0], 1.5, places=3)
        self.assertAlmostEqual(x[1], -2.0, places=3)
        self.assertAlmostEqual(altin_oran(lambda r: (r - 0.07) ** 2, -0.3, 0.3), 0.07, places=4)


class D3Elo(Temel):
    def test_guncelleme_sifir_toplamli_ve_sezon_gecisi(self):
        e = EloModeli(EloAyar(k=20, ev_avantaji=60, sezon_cekimi=0.5))
        e.sezon_basla("2020-21", {"a", "b", "c"})
        m = {"ev": "a", "dep": "b", "ev_gol": 3, "dep_gol": 0}
        once = sum(e.puan.values())
        e.sonuc_isle(m)
        self.assertAlmostEqual(sum(e.puan.values()), once)
        self.assertGreater(e.puan["a"], 1500)
        self.assertEqual(gol_carpani(3), 14 / 8)
        e.puan.update({"a": 1600, "b": 1400, "c": 1500})
        e.sezon_basla("2021-22", {"a", "b", "d"})                          # c düştü, d çıktı
        self.assertAlmostEqual(e.puan["a"], 1550)                           # ortalamaya yarı yarıya
        self.assertAlmostEqual(e.puan["d"], e.puan["c"])                    # yeni takım = düşenin puanı

    def test_sirali_lojistik(self):
        s = SiraliLojistik()
        for x in (-1, 0, 1):
            p = s.olasilik(x)
            self.assertAlmostEqual(sum(p.values()), 1)
            self.assertTrue(all(v > 0 for v in p.values()))
        self.assertGreater(s.olasilik(1)["H"], s.olasilik(-1)["H"])
        rng = np.random.default_rng(1)
        veri = []
        for _ in range(3000):
            x = rng.normal(0, 0.5)
            veri.append((x, rng.choice(["A", "D", "H"], p=list(SiraliLojistik(-0.9, 0.3, 2.0).olasilik(x).values())[::-1])))
        s.kestir(veri)
        self.assertAlmostEqual(s.beta, 2.0, delta=0.3)


class D4GolModelleri(Temel):
    def test_rho_sinirlari_dogru(self):
        lh, la = np.array([2.5, 1.0]), np.array([1.2, 3.0])
        alt, ust = rho_sinirlari(lh, la)
        self.assertAlmostEqual(ust, min(1.0, 1 / 3.0, 1 / 3.0))             # 1/(λhλa) en küçüğü
        self.assertAlmostEqual(alt, max(-1 / 2.5, -1 / 3.0))                # −1/λ en büyüğü
        for r in (alt + 1e-6, ust - 1e-6):
            for x in (0, 1):
                for y in (0, 1):
                    for a, b in zip(lh, la):
                        self.assertGreater(tau(x, y, a, b, r), 0)
        # WIP hatası: 1/λ değerleri üst sınıra karışmamalı -> λ=3 iken üst sınır 1/3'ten küçük olmaz
        self.assertGreaterEqual(rho_sinirlari(np.array([3.0]), np.array([0.1]))[1], 1 / 3.0 - 1e-12)

    def test_skor_matrisi_ve_pazarlar(self):
        m0 = skor_matrisi(1.4, 1.1, 0.0)
        m1 = skor_matrisi(1.4, 1.1, -0.1)
        self.assertAlmostEqual(m0.sum(), 1)
        self.assertAlmostEqual(m1.sum(), 1)
        self.assertGreater(m1[1, 1], m0[1, 1])                              # ρ<0 düşük berabere skorları artırır
        p = pazarlar(m1)
        self.assertAlmostEqual(p["H"] + p["D"] + p["A"], 1)
        self.assertAlmostEqual(p["ust25"] + p["alt25"], 1)
        self.assertAlmostEqual(p["kg_var"] + p["kg_yok"], 1)

    def test_parametre_geri_kazanimi_ve_rho(self):
        maclar, gercek = sentetik_lig(sezon_sayisi=6, takim=10, tohum=5)
        g = GolModeli(xi=0.0, pencere_gun=100000, ceza=0.01)
        g.hazirla(maclar, "2030-01-01", {m["ev"] for m in maclar})
        b, ix, n = g.param["beta"], g.param["ix"], g.param["n"]
        tahmin = np.array([b[2 + ix[f"t{i}"]] for i in range(10)])
        self.assertGreater(np.corrcoef(tahmin, gercek["hucum"])[0, 1], 0.9)
        self.assertAlmostEqual(b[1], gercek["ev"], delta=0.08)
        self.assertLess(abs(g.rho), 0.1)                                     # bağımsız Poisson verisi: ρ≈0
        r = rho_kestir([0, 1, 0, 1], [0, 0, 1, 1], [1.2] * 4, [1.0] * 4, [1.0] * 4)
        alt, ust = rho_sinirlari(np.array([1.2] * 4), np.array([1.0] * 4))
        self.assertTrue(max(alt, -0.35) <= r <= min(ust, 0.35))

    def test_yeni_takim_onseli_ve_poisson_gorunumu(self):
        maclar, _ = sentetik_lig(sezon_sayisi=2, takim=6, tohum=2)
        g = GolModeli(yeni_hucum=0.8, yeni_savunma=1.2)
        g.hazirla(maclar, "2030-01-01", {m["ev"] for m in maclar} | {"yeni"})
        lh, la = g.oranlar("t0", "yeni")
        lh2, la2 = g.oranlar("yeni", "t0")
        self.assertGreater(lh, la2 * 0.9)
        p = PoissonGorunumu(g)
        p.hazirla(maclar, "2030-01-01", set())
        self.assertAlmostEqual(sum(p.tahmin({"ev": "t0", "dep": "t1"})[k] for k in "HDA"), 1)


class D5Backtest(Temel):
    def test_sizinti_korumasi_ve_gelecek_degismezligi(self):
        maclar, _ = sentetik_lig(sezon_sayisi=3, takim=6, tohum=7)
        sezonlar = sorted({m["sezon"] for m in maclar})
        bas = min(m["tarih"] for m in maclar if m["sezon"] == sezonlar[1])
        def calis(ms):
            e, g = EloModeli(), GolModeli(xi=0.002)
            return yuruyen_test(ms, [FrekansModeli(), e, g, PoissonGorunumu(g)], bas)
        k1 = calis(maclar)
        self.assertTrue(all(k["egitim_kesimi"] < k["tarih"] for k in k1))
        self.assertTrue(all(abs(sum(k["tahmin"][md][s] for s in "HDA") - 1) < 1e-9 for k in k1
                            for md in ("taban", "elo", "dixon_coles", "poisson")))
        # son sezonun sonuçlarını tamamen değiştir: daha önceki tahminler AYNI kalmalı
        kesim = min(m["tarih"] for m in maclar if m["sezon"] == sezonlar[2])
        bozuk = [dict(m, ev_gol=m["dep_gol"] + 3, dep_gol=0) if m["tarih"] >= kesim else m for m in maclar]
        k2 = calis(bozuk)
        once1 = [k for k in k1 if k["tarih"] < kesim]
        once2 = [k for k in k2 if k["tarih"] < kesim]
        self.assertEqual(len(once1), len(once2))
        for a, b in zip(once1, once2):
            for md in ("elo", "dixon_coles"):
                for s in "HDA":
                    self.assertAlmostEqual(a["tahmin"][md][s], b["tahmin"][md][s], places=12)

    def test_ayni_gun_sonuclari_birbirini_etkilemez(self):
        e = EloModeli()
        ms = [{"sezon": "2020-21", "tarih": "2020-09-01", "ev": "a", "dep": "b", "ev_gol": 5, "dep_gol": 0},
              {"sezon": "2020-21", "tarih": "2020-09-01", "ev": "a", "dep": "c", "ev_gol": 0, "dep_gol": 0}]
        k = yuruyen_test(ms, [e], "2020-01-01")
        self.assertAlmostEqual(k[0]["tahmin"]["elo"]["H"], k[1]["tahmin"]["elo"]["H"])

    def test_mk1_oran_iceren_girdi_reddedilir(self):
        maclar, _ = sentetik_lig(sezon_sayisi=1, takim=4)
        maclar[0]["oran_ms1"] = 1.85
        with self.assertRaises(girdi.OranSizintisi):
            yuruyen_test(maclar, [FrekansModeli()], "2015-01-01")

    def test_desteklenmeyen_pazarlar_hesaplanamaz(self):
        for p in ("korner", "kart", "oyuncu"):
            self.assertEqual(pazar_destegi(p)["durum"], "hesaplanamaz")
        self.assertEqual(pazar_destegi("ust25")["durum"], "destekleniyor")


class D6Metrikler(Temel):
    def test_bilinen_degerler(self):
        P = [{"H": 0.5, "D": 0.3, "A": 0.2}, {"H": 1.0, "D": 0.0, "A": 0.0}]
        self.assertAlmostEqual(log_loss(P[:1], ["H"]), -math.log(0.5))
        self.assertAlmostEqual(brier(P[1:], ["H"]), 0.0)
        self.assertAlmostEqual(brier(P[:1], ["A"]), 0.25 + 0.09 + 0.64)
        self.assertAlmostEqual(rps(P[:1], ["H"]), ((0.5 - 1) ** 2 + (0.8 - 1) ** 2) / 2)
        self.assertAlmostEqual(kalibrasyon([0.25] * 4, [1, 0, 0, 0])["ece"], 0.0)
        self.assertAlmostEqual(auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]), 1.0)
        self.assertAlmostEqual(auc([0.5, 0.5], [0, 1]), 0.5)
        b = bootstrap_ortalama_fark([1, 1, 1], [0, 0, 0])
        self.assertEqual((b["fark"], b["alt95"], b["ust95"]), (1.0, 1.0, 1.0))


class D7SurprizVeSeri(Temel):
    def kayit(self, t, ev, dep, sonuc, pH, pA):
        return {"tarih": t, "ev": ev, "dep": dep, "sonuc": sonuc,
                "tahmin": {"m": {"H": pH, "D": 1 - pH - pA, "A": pA}}}

    def test_surpriz_alarm_olcutleri(self):
        k = [self.kayit("2020-01-0%d" % i, "a", "b", s, 0.6, pa) for i, (s, pa) in
             enumerate([("A", 0.3), ("H", 0.3), ("H", 0.1), ("H", 0.1)], 1)]
        r = surpriz_analizi(k, "m", alarm_esikleri=(0.25,))
        a = r["alarmlar"][0]
        self.assertEqual((r["n_favori_maci"], r["surpriz_orani"]), (4, 0.25))
        self.assertEqual((a["alarm"], a["dogru_alarm"], a["isabet"], a["yanlis_alarm_orani"], a["yakalama"]),
                         (2, 1, 0.5, 0.5, 1.0))
        self.assertAlmostEqual(a["yanlis_pozitif_orani"], 1 / 3, places=4)
        self.assertEqual(r["auc_zayif_kazanir"], 0.8333)

    def test_seri_rakip_gucune_gore_gruplanir(self):
        g = [{"tarih": f"2020-01-0{i}", "ev": "a", "dep": f"z{i}", "sonuc": "H", "elo_ev_goreli": 50,
              "elo_dep_goreli": -80} for i in range(1, 4)]
        k = [self.kayit("2020-01-05", "a", "q", "H", 0.7, 0.1), self.kayit("2020-01-05", "b", "c", "A", 0.6, 0.2)]
        r = seri_analizi(k, "m", g)
        self.assertEqual(r["seri_zayif_rakipler"]["n"], 1)
        self.assertEqual(r["seri_yok"]["n"], 1)
        self.assertEqual(r["seri_guclu_rakipler"]["n"], 0)


class D8Bagimsizlik(Temel):
    def test_model_kodu_nesine_okumaz(self):
        kaynak = "".join(p.read_text(encoding="utf-8") for p in (KOK / "lib/fi/model").glob("*.py"))
        for yasak in ("nesine_bulletin", "getprebultenfull", "mac_oncesi.json", "oran_ham", "odds"):
            self.assertNotIn(yasak, kaynak)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class D9DegerlendirmeVeOnKayit(Temel):
    """D aşaması yardımcıları: kümeli bootstrap, eşleştirilmiş karşılaştırma, düşük skor sayımı, yeni takım önseli,
    önceden kayıt (SHA-256) kilidi ve Elo dönüşümünün yalnızca geçmiş sezonlarla kestirilmesi."""

    def test_kume_bootstrap_ve_eslestirilmis(self):
        from fi.model.degerlendirme import eslestirilmis, kume_bootstrap
        r = kume_bootstrap(np.full(40, 0.25), [f"g{i // 4}" for i in range(40)])
        self.assertEqual((r["n_mac"], r["n_kume"]), (40, 10))
        self.assertAlmostEqual(r["alt95"], 0.25)
        self.assertAlmostEqual(r["ust95"], 0.25)
        iyi, kotu = {"H": 0.8, "D": 0.1, "A": 0.1}, {"H": 0.4, "D": 0.3, "A": 0.3}
        kay = [{"sonuc": "H", "tarih": f"2020-01-{i % 9 + 1:02d}", "sezon": "2019-20" if i < 10 else "2020-21",
                "tahmin": {"a": iyi, "b": kotu}} for i in range(20)]
        e = eslestirilmis(kay, "a", "b")
        self.assertLess(e["ust95"], 0)
        self.assertEqual((e["a_iyi_sezon"], e["sezon_sayisi"]), (2, 2))

    def test_dusuk_skor_sayimi(self):
        from fi.model.degerlendirme import dusuk_skor_analizi
        p = pazarlar(skor_matrisi(1.2, 1.0, -0.1))
        kay = [{"ev_gol": e, "dep_gol": d, "sonuc": sonuc_kodu({"ev_gol": e, "dep_gol": d}),
                "tahmin": {"poisson": p, "dixon_coles": p}} for e, d in ((0, 0), (1, 1), (2, 0), (0, 1))]
        r = dusuk_skor_analizi(kay)["poisson"]
        self.assertEqual((r["0_0"]["gerceklesen"], r["1_1"]["gerceklesen"], r["0_1"]["gerceklesen"]), (1, 1, 1))
        self.assertAlmostEqual(r["0_0"]["beklenen"], round(4 * p["skor_0_0"], 1))
        self.assertEqual(r["beraberlik"]["gerceklesen"], 2)

    def test_yeni_takim_onseli_yalnizca_verilen_sezonlar(self):
        from fi.model.degerlendirme import yeni_takim_onseli
        maclar, _ = sentetik_lig(sezon_sayisi=2, takim=8, tohum=4)
        s1, s2 = sorted({m["sezon"] for m in maclar})
        # 2. sezonda t0 ligden çıkar, zayıf "yeni" takımı gelir (çok az atar, çok yer)
        rng = np.random.default_rng(9)
        for m in maclar:
            if m["sezon"] == s2 and "t0" in (m["ev"], m["dep"]):
                yeni_ev = m["ev"] == "t0"
                m["ev" if yeni_ev else "dep"] = "yeni"
                m["ev_gol" if yeni_ev else "dep_gol"] = int(rng.poisson(0.5))
                m["dep_gol" if yeni_ev else "ev_gol"] = int(rng.poisson(2.5))
        r = yeni_takim_onseli(maclar, [s2])
        self.assertEqual((r["n_takim"], r["sezonlar"]), (1, [s2]))
        self.assertLess(r["hucum"], 1.0)
        self.assertGreater(r["savunma"], 1.0)
        self.assertEqual(yeni_takim_onseli(maclar, [s1])["n_takim"], 0)   # ilk sezonun öncesi yok → önsel kestirilmez

    def test_on_kayit_ozeti_tutmazsa_dogrulama_calismaz(self):
        from fi.model import d_asamasi
        eski = (d_asamasi.ON_KAYIT, d_asamasi.ON_KAYIT_OZET)
        try:
            d_asamasi.ON_KAYIT, d_asamasi.ON_KAYIT_OZET = self.tmp / "k.md", self.tmp / "k.sha256"
            with self.assertRaises(SystemExit):                          # kayıt yok
                d_asamasi.main(["dogrulama"])
            d_asamasi.ON_KAYIT.write_text("- Seçilen önsel varyantı: `V0_sabit`\n", encoding="utf-8")
            d_asamasi.ON_KAYIT_OZET.write_text("0" * 64 + "  k.md\n", encoding="utf-8")
            with self.assertRaises(SystemExit) as cm:                    # özet tutmuyor
                d_asamasi.main(["dogrulama"])
            self.assertIn("SHA-256", str(cm.exception))
        finally:
            d_asamasi.ON_KAYIT, d_asamasi.ON_KAYIT_OZET = eski

    def test_elo_donusumu_yalnizca_gecmis_sezonlardan(self):
        maclar, _ = sentetik_lig(sezon_sayisi=3, takim=16, tohum=2)
        sezonlar = sorted({m["sezon"] for m in maclar})
        e = EloModeli()
        for s in sezonlar:
            e.sezon_basla(s, {t for m in maclar if m["sezon"] == s for t in (m["ev"], m["dep"])})
            gecmis_n = sum(1 for m in maclar if m["sezon"] < s)
            self.assertEqual(e.donusum.ornek if gecmis_n >= 200 else 0, gecmis_n if gecmis_n >= 200 else 0)
            for m in sorted((m for m in maclar if m["sezon"] == s), key=lambda m: m["tarih"]):
                e.sonuc_isle(m)
