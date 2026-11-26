"""Güncel veri birleştirme, eşleme adayları ve kapsam kaydı (GE1–GE6)."""
import json
import tempfile
import unittest
from pathlib import Path

from fi.kaynaklar import guncel as G
from fi.model import kapsam as KP


def of(sezon, tarih, ev, dep, eg, dg, ih=None, ia=None):
    return {"sezon": sezon, "tarih": tarih, "ev": ev.lower(), "dep": dep.lower(), "ev_ad": ev, "dep_ad": dep,
            "ev_gol": eg, "dep_gol": dg, "iy_ev": ih, "iy_dep": ia}


def fd(tarih, ev, dep, eg, dg, ih, ia, durum="FINISHED", sure="REGULAR"):
    return {"kaynak_id": 1, "durum": durum, "utc_baslama": f"{tarih}T15:00:00+00:00", "hafta": 9, "ev": ev, "dep": dep,
            "normal_sure_ev": eg, "normal_sure_dep": dg, "iy_ev": ih, "iy_dep": ia, "sure_turu": sure}


class GE(unittest.TestCase):
    def test_GE1_cakisan_mac_karsilastirilir_yeni_mac_eklenir(self):
        o = [of("2026-27", "2026-09-01", "Alfa FC", "Beta FC", 1, 0, 0, 0)]
        f = [fd("2026-09-01", "Alfa FC", "Beta FC", 1, 0, 0, 0), fd("2026-10-01", "Beta FC", "Alfa FC", 2, 2, 1, 1)]
        tum, r = G.birlestir(o, f, "xx.1")
        self.assertEqual((r["ayni"], len(r["farkli"]), r["eklenen"]), (1, 0, 1))
        yeni = [m for m in tum if m.get("kaynak") == "football-data.org"][0]
        self.assertEqual((yeni["ev"], yeni["ev_gol"], yeni["iy_ev"]), ("beta fc", 2, 1))

    def test_GE2_uyusmazlik_raporlanir_of_kaydi_korunur(self):
        o = [of("2026-27", "2026-09-01", "Alfa FC", "Beta FC", 1, 0, 0, 0)]
        tum, r = G.birlestir(o, [fd("2026-09-01", "Alfa FC", "Beta FC", 2, 0, 0, 0)], "xx.1")
        self.assertEqual(len(r["farkli"]), 1)
        self.assertEqual(len(tum), 1)
        self.assertEqual(tum[0]["ev_gol"], 1)

    def test_GE3_eslenmeyen_takim_maci_eklenmez(self):
        o = [of("2026-27", "2026-09-01", "Alfa FC", "Beta FC", 1, 0)]
        tum, r = G.birlestir(o, [fd("2026-10-01", "Gama Spor Kulübü 1907", "Alfa FC", 1, 1, 0, 0)], "xx.1")
        self.assertEqual(r["eklenen"], 0)
        self.assertEqual(r["esleme_disi_atlanan"], 1)
        self.assertIn("Gama Spor Kulübü 1907", r["eslenmeyen_takim"])

    def test_GE4_uzatmali_ve_bitmemis_mac_eklenmez(self):
        o = [of("2026-27", "2026-09-01", "Alfa FC", "Beta FC", 1, 0)]
        f = [fd("2026-10-01", "Beta FC", "Alfa FC", 1, 1, 0, 0, sure="EXTRA_TIME"),
             fd("2026-10-08", "Beta FC", "Alfa FC", None, None, None, None, durum="SCHEDULED")]
        _, r = G.birlestir(o, f, "xx.1")
        self.assertEqual(r["eklenen"], 0)

    def test_GE5_eslemeler_otomatik_onaylamaz(self):
        d = json.loads(Path(KP.KOK / "veri" / "lig_esleme_adaylari.json").read_text())
        self.assertTrue(all(a["durum"] == "onay_bekliyor" for a in d["adaylar"]))
        onayli = json.loads((KP.KOK / "veri" / "lig_eslemeleri.json").read_text())["eslemeler"]
        # yalnızca kullanıcının açıkça onayladığı ve kanıtlı kayıtlar (26.11: Championship [52] → en.2)
        self.assertTrue(all(e["onaylayan"] == "kullanici" and e["kanit"]["hizali_mac"] for e in onayli))
        self.assertEqual({(e["nesine_lig"], e["nesine_yarisma_kimligi"], e["kaynak_lig"]) for e in onayli},
                         {("İngiltere Championship", 52, "en.2")})
        o = json.loads((KP.KOK / "veri" / "openligadb_takim_adaylari.json").read_text())
        self.assertTrue(all(a["durum"] == "onay_bekliyor" for a in o["adaylar"]))

    def test_GE6_kapsam_kurali(self):
        t = Path(tempfile.mkdtemp())
        v1 = {"birlesik": {"A": {"poisson": {"buyuk_sapmali_kutu": []}}, "B": {"poisson": {"buyuk_sapmali_kutu": []}}}}
        dn = {"E": {"poisson": {
            "A": {"olay_orani": 0.4, "E1_lig_sezon": True, "GA_lig_sezon": [-0.02, -0.01, 30], "ece_havuz": 0.01,
                  "lig_ece": {"x": 0.03}},
            "B": {"olay_orani": 0.4, "E1_lig_sezon": True, "GA_lig_sezon": [-0.02, -0.01, 30], "ece_havuz": 0.01,
                  "lig_ece": {"x": 0.05}}}}}
        (t / "v1.json").write_text(json.dumps(v1)); (t / "dn.json").write_text(json.dumps(dn))
        k = KP.e_poisson_kapsami(t / "v1.json", t / "dn.json")
        self.assertTrue(k["A"]["kapsamda"])
        self.assertFalse(k["B"]["kapsamda"])                    # tek ligde ECE > 0,04 yeterli
        self.assertIn("lig ECE", k["B"]["nedenler"][0])


if __name__ == "__main__":
    unittest.main()


class Butunluk(unittest.TestCase):
    def m(self, i, h, ev, dep, durum="FINISHED", g=(1, 0), iy=(0, 0)):
        return {"kaynak_id": i, "hafta": h, "asama": "REGULAR_SEASON", "ev": ev, "dep": dep, "durum": durum,
                "utc_baslama": "2026-09-01T15:00:00+00:00", "normal_sure_ev": g[0] if durum == "FINISHED" else None,
                "normal_sure_dep": g[1] if durum == "FINISHED" else None, "iy_ev": iy[0], "iy_dep": iy[1]}

    def test_BT1_ertelenen_eksik_sayilmaz_kayip_sayilir(self):
        a = [self.m(1, 1, "A", "B"), self.m(2, 1, "C", "D"), self.m(3, 2, "A", "C"), self.m(4, 2, "B", "D", "TIMED")]
        b = G.butunluk(a)
        self.assertEqual(b["sorunlar"], [])
        self.assertEqual(len(b["ertelenen_bilgi"]), 0)        # 2. hafta tam değil (son tam hafta 1)
        a2 = [self.m(1, 1, "A", "B"), self.m(3, 2, "A", "C"), self.m(5, 2, "B", "D")]     # 1. haftada kayıt yok
        self.assertIn("son_tam_haftadan_once_eksik", G.butunluk(a2)["sorunlar"])

    def test_BT2_onceki_cekimle_karsilastirma(self):
        once = [self.m(1, 1, "A", "B"), self.m(2, 1, "C", "D")]
        simdi = [self.m(1, 1, "A", "B", g=(2, 0)), ]
        b = G.butunluk(simdi, once)
        self.assertEqual(b["kaybolan_biten"], [2])
        self.assertEqual(b["skoru_degisen"], [1])
        self.assertIn("skoru_degisen", b["sorunlar"])


class Hizalama(unittest.TestCase):
    def fd(self, ev, dep, utc, i=1):
        return {"ev": ev, "dep": dep, "utc_baslama": utc, "kaynak_id": i, "durum": "SCHEDULED"}

    def nes(self, ev, dep, tr, kod=52):
        return {"ev": ev, "deplasman": dep, "karsilasma": f"{ev} - {dep}", "baslama_tr": tr, "kod": 1, "lig_kodu": kod}

    def test_HZ1_ayni_dakika_ve_iki_takim(self):
        from fi.eslemeler import fikstur_hizalama
        h = fikstur_hizalama([self.nes("Southampton", "Middlesbrough", "2026-11-27T23:00:00+03:00")],
                             [self.fd("Southampton FC", "Middlesbrough FC", "2026-11-27T20:00:00+00:00")])
        self.assertEqual(len(h["hizali"]), 1)
        self.assertEqual(h["hizali"][0]["takim_eslesmesi"], ["kesin", "kesin"])

    def test_HZ2_farkli_dakika_hizalanmaz(self):
        from fi.eslemeler import fikstur_hizalama
        h = fikstur_hizalama([self.nes("Southampton", "Middlesbrough", "2026-11-27T22:00:00+03:00")],
                             [self.fd("Southampton FC", "Middlesbrough FC", "2026-11-27T20:00:00+00:00")])
        self.assertEqual((len(h["hizali"]), len(h["hizasiz"])), (0, 1))

    def test_HZ3_tek_aday_ad_onayi_gerekli_paris_ornegi(self):
        from fi.eslemeler import fikstur_hizalama
        h = fikstur_hizalama([self.nes("Brest", "Paris", "2026-11-27T22:45:00+03:00")],
                             [self.fd("Stade Brestois 29", "Paris FC", "2026-11-27T19:45:00+00:00")])
        self.assertEqual(len(h["tek_aday_dakika"]), 1)
        self.assertIn("ad_onayi_gerekli", h["tek_aday_dakika"][0]["takim_eslesmesi"])
        self.assertEqual(h["tek_aday_dakika"][0]["tek_aday"], "Stade Brestois 29 - Paris FC")   # PSG değil

    def test_HZ4_iki_takim_da_tutmazsa_aday_yok(self):
        from fi.eslemeler import fikstur_hizalama
        h = fikstur_hizalama([self.nes("VVV Venlo", "Waalwijk", "2026-11-27T22:00:00+03:00")],
                             [self.fd("FC Groningen", "Willem II Tilburg", "2026-11-27T19:00:00+00:00")])
        self.assertEqual((len(h["hizali"]), len(h["tek_aday_dakika"]), len(h["hizasiz"])), (0, 0, 1))
