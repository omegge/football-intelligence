"""V1-V3: OpenFootball tarih bütünlüğü — kayıtlı düzeltmeler (okuyucu katmanında, kanıtlı, tekil) ve tutarsızlık
denetimi. Ağsız; gerçek veri testi yalnızca yerel klon varsa çalışır."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "lib"))

from fi.kaynaklar import openfootball                                   # noqa: E402
from fi.kaynaklar.openfootball import VeriTutarsizligi, lig_oku, tarih_denetimi  # noqa: E402


def _mac(tur, tarih, ev, dep, ft, ht=None):
    return {"round": f"Matchday {tur}", "date": tarih, "team1": ev, "team2": dep,
            "score": {"ft": ft, **({"ht": ht} if ht else {})}}


SEZON = [_mac(1, "2019-08-10", "A FC", "B FC", [1, 0], [0, 0]), _mac(1, "2019-08-10", "C FC", "D FC", [2, 2]),
         _mac(2, "2019-08-17", "B FC", "C FC", [0, 1]), _mac(2, "2019-08-17", "D FC", "A FC", [3, 1], [1, 1]),
         _mac(3, "2019-07-01", "A FC", "C FC", [1, 4], [0, 2])]          # Temmuz 2020'de oynanmış, yılı hatalı


class Ortak(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fi_veri_"))
        (self.tmp / "kaynak" / "2019-20").mkdir(parents=True)
        self.yaz(SEZON)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def yaz(self, maclar):
        (self.tmp / "kaynak" / "2019-20" / "en.1.json").write_text(json.dumps({"matches": maclar}), encoding="utf-8")

    def duzeltme(self, **degis):
        k = {"lig": "en.1", "sezon": "2019-20", "ev_ad": "A FC", "dep_ad": "C FC", "skor": [1, 4], "ilk_yari": [0, 2],
             "kaynak_tarih": "2019-07-01", "duzeltilmis_tarih": "2020-07-01", "kanit": {"gun_metni": "Wed Jul 1"}}
        k.update(degis)
        yol = self.tmp / "duz.json"
        yol.write_text(json.dumps({"duzeltmeler": [k]}), encoding="utf-8")
        return yol


class V1Denetim(Ortak):
    def test_yili_kaymis_mac_duzeltmesiz_okunmaz(self):
        with self.assertRaises(VeriTutarsizligi) as cm:
            lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=None)
        self.assertIn("1. haftanın ilk maçından", str(cm.exception))

    def test_sezon_yillari_disi_ve_mukerrer(self):
        self.yaz(SEZON[:4] + [_mac(3, "2021-03-01", "A FC", "C FC", [0, 0])])
        with self.assertRaises(VeriTutarsizligi) as cm:
            lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=None)
        self.assertIn("sezon yılları dışında", str(cm.exception))
        self.yaz(SEZON[:4] + [_mac(3, "2019-08-24", "A FC", "B FC", [0, 0])])
        with self.assertRaises(VeriTutarsizligi) as cm:
            lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=None)
        self.assertIn("mükerrer", str(cm.exception))

    def test_hafta_sirasi_tersligi_yalnizca_uyari(self):
        ms = [{"sezon": "2020-21", "tarih": t, "tur": f"Matchday {h}", "ev": e, "dep": d, "ev_ad": e, "dep_ad": d}
              for h, t, e, d in ((1, "2020-09-12", "a", "b"), (2, "2020-12-01", "b", "a"), (3, "2020-09-26", "a", "c"))]
        sert, uyari = tarih_denetimi(ms)
        self.assertEqual(sert, [])
        self.assertEqual(len(uyari), 1)


class V2KayitliDuzeltme(Ortak):
    def test_tam_eslesmeyle_uygulanir_ve_kaydedilir(self):
        maclar, kaynak = lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=self.duzeltme())
        self.assertEqual(maclar[-1]["tarih"], "2020-07-01")             # artık sezonun sonunda
        self.assertEqual(kaynak["tarih_duzeltmeleri"], [{"sezon": "2019-20", "ev_ad": "A FC", "dep_ad": "C FC",
                                                         "kaynak_tarih": "2019-07-01", "duzeltilmis_tarih": "2020-07-01"}])
        self.assertIsNotNone(kaynak["duzeltme_dosyasi_sha256"])
        # kaynak dosya değişmedi
        ham = json.loads((self.tmp / "kaynak" / "2019-20" / "en.1.json").read_text(encoding="utf-8"))
        self.assertEqual(ham["matches"][4]["date"], "2019-07-01")

    def test_genel_yil_kurali_yok_eslesmeyen_kayit_hata(self):
        with self.assertRaises(VeriTutarsizligi):                         # skor farklı → kayıt bulunamaz
            lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=self.duzeltme(skor=[1, 3]))
        with self.assertRaises(VeriTutarsizligi):                         # kaynak tarih farklı → tutmuyor
            lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=self.duzeltme(kaynak_tarih="2019-07-02"))
        with self.assertRaises(VeriTutarsizligi):                         # ilk yarı farklı → kayıt bulunamaz
            lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=self.duzeltme(ilk_yari=[1, 2]))

    def test_kaynakta_duzelmisse_ikinci_kez_uygulanmaz(self):
        self.yaz(SEZON[:4] + [_mac(3, "2020-07-01", "A FC", "C FC", [1, 4], [0, 2])])
        maclar, kaynak = lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=self.duzeltme())
        self.assertEqual(kaynak["tarih_duzeltmeleri"], [])
        self.assertEqual(kaynak["kaynakta_duzelmis_kayit"], 1)
        self.assertEqual(maclar[-1]["tarih"], "2020-07-01")


class V4SkorTamamlama(Ortak):
    def kayit(self, **degis):
        k = {"lig": "en.1", "sezon": "2019-20", "tarih": "2019-08-24", "ev_ad": "B FC", "dep_ad": "A FC",
             "skor": [2, 1], "ilk_yari": [1, 0], "kanit": {"kaynak_1": {}, "kaynak_2": {}}}
        k.update(degis)
        yol = self.tmp / "skor.json"
        yol.write_text(json.dumps({"tamamlamalar": [k]}), encoding="utf-8")
        return yol

    def skorsuz(self, skor=None):
        m = {"round": "Matchday 3", "date": "2019-08-24", "team1": "B FC", "team2": "A FC"}
        if skor:
            m["score"] = {"ft": skor}
        self.yaz(SEZON[:4] + [m])

    def test_yalnizca_bos_skor_tam_eslesmeyle_tamamlanir(self):
        self.skorsuz()
        maclar, kaynak = lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=None, skor_tamamlamalari=None)
        self.assertEqual((len(maclar), kaynak["skorsuz_atlanan"]), (4, 1))   # kayıtsız: atlanır, uydurulmaz
        maclar, kaynak = lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=None, skor_tamamlamalari=self.kayit())
        son = maclar[-1]
        self.assertEqual((son["ev_gol"], son["dep_gol"], son["iy_ev"]), (2, 1, 1))
        self.assertEqual(len(kaynak["skor_tamamlamalari"]), 1)
        self.assertEqual(kaynak["skorsuz_atlanan"], 0)

    def test_celiskili_ya_da_bulunamayan_kayit_durdurur(self):
        self.skorsuz(skor=[0, 0])
        with self.assertRaises(VeriTutarsizligi):                         # kaynakta farklı skor var
            lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=None, skor_tamamlamalari=self.kayit())
        self.skorsuz()
        with self.assertRaises(VeriTutarsizligi):                         # tarih tutmuyor → kayıt bulunamaz
            lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=None, skor_tamamlamalari=self.kayit(tarih="2019-08-25"))

    def test_kaynakta_ayni_skor_varsa_ikinci_kez_uygulanmaz(self):
        self.skorsuz(skor=[2, 1])
        _, kaynak = lig_oku("en.1", self.tmp / "kaynak", duzeltmeler=None, skor_tamamlamalari=self.kayit())
        self.assertEqual((kaynak["skor_tamamlamalari"], kaynak["kaynakta_skorlu_kayit"]), ([], 1))


@unittest.skipUnless((openfootball.KOK / "2019-20" / "en.1.json").exists(), "yerel OpenFootball klonu yok")
class V3GercekVeri(unittest.TestCase):
    def test_kayitli_duzeltmeler_kanitli_ve_dort_lig_temiz(self):
        d = json.loads(openfootball.DUZELTME_DOSYASI.read_text(encoding="utf-8"))
        self.assertEqual(len(d["duzeltmeler"]), 66)
        for k in d["duzeltmeler"]:
            self.assertTrue(k["kanit"]["gun_metni"] and k["kanit"]["commit"] and k["kanit"]["mac_satiri"])
            self.assertEqual(k["duzeltilmis_tarih"][4:], k["kaynak_tarih"][4:])   # yalnızca yıl farklı, gün/ay aynı
            self.assertEqual(k["bagimsiz_dogrulama"]["durum"], "dogrulandi")      # ikinci kaynak (Wikipedia)
            self.assertTrue(k["bagimsiz_dogrulama"]["maddeler"])
        for lig in ("en.1", "de.1", "es.1", "it.1"):
            maclar, kaynak = lig_oku(lig)                                # sert tutarsızlık kalırsa hata verir
            self.assertEqual(len(kaynak["tarih_duzeltmeleri"]), 66 if lig == "en.1" else 0)
            self.assertEqual(len(kaynak["skor_tamamlamalari"]), 10 if lig in ("es.1", "it.1") else 0)
            bitmis = {s for s in {m["sezon"] for m in maclar} if s <= "2025-26"}
            for s in bitmis:                                             # bitmiş sezonlar tam çift devre
                n = len({t for m in maclar if m["sezon"] == s for t in (m["ev"], m["dep"])})
                self.assertEqual(sum(1 for m in maclar if m["sezon"] == s), n * (n - 1), f"{lig} {s}")
        sk = json.loads(openfootball.SKOR_DOSYASI.read_text(encoding="utf-8"))["tamamlamalar"]
        self.assertEqual(len(sk), 20)
        for k in sk:                                                     # iki kaynak kanıtı zorunlu
            self.assertTrue(k["kanit"]["kaynak_1"]["mac_id"] and k["kanit"]["kaynak_2"]["satir"])
            for s in {m["sezon"] for m in maclar}:
                ms = sorted(m["tarih"] for m in maclar if m["sezon"] == s)
                self.assertGreaterEqual(ms[0][:4], s[:4])


if __name__ == "__main__":
    unittest.main()
