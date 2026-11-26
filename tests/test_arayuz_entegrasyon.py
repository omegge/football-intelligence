"""V1 entegrasyon testleri: gerçek HTTP sunucusu ayrı süreçte, geçici çıktı kökünde (FI_OUTPUT) çalışır.

Kapsam: gece yarısı gün kuralı, MK-1 (oran yalnızca doğrulanmış dondurmadan sonra), dondurma bütünlüğü (SHA-256),
fiyat kilidi, geçersiz işlemler. Gerçek output/ klasörüne dokunulmaz; ağ isteği yapılmaz.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "lib"))
from fi import is_akisi as I  # noqa: E402

ORAN_IZI = "7.77"          # fikstürdeki ayırt edici oran: dondurmadan önce hiçbir sayfada görünmemeli


def _bos_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _mac(kod, baslama):
    return {"kod": kod, "lig": "Test Ligi", "lig_kodu": 9, "lig_ulke": "XX", "ev": f"Ev{kod}", "deplasman": f"Dep{kod}",
            "karsilasma": f"Ev{kod} - Dep{kod}", "baslama_tr": baslama,
            "marketler": [{"market_adi": "Maç Sonucu", "secenekler": [{"secenek_adi": "MS X", "oran": float(ORAN_IZI)}]}]}


def fikstur_kur(kok: Path) -> dict:
    b = kok / "bulten_20261130_120000"
    b.mkdir(parents=True)
    (b / "mac_oncesi.json").write_text(json.dumps({
        "kaynak": {"cekim_utc": "2026-11-30T12:00:00+00:00", "cekim_tr": "2026-11-30T15:00:00+03:00", "sha256": "ab" * 32},
        "pencere_tr": ["2026-12-01T00:00:00+03:00", "2026-12-02T03:00:00+03:00"],
        "futbol": [_mac(1, "2026-12-01T23:59:00+03:00"), _mac(2, "2026-12-02T00:30:00+03:00"),
                   _mac(3, "2026-12-01T00:00:00+03:00")]}), encoding="utf-8")
    mac = {"mac_id": "nesine:1", "karsilasma": "Ev1 - Dep1", "lig": "Test Ligi", "baslama_tr": "2026-12-01T23:59:00+03:00"}
    tahmin = {"durum": "hesaplandi", "veri_kesimi": "2026-11-29", "model_adi": "test", "lambda_ev": 1.2, "lambda_dep": 1.0,
              "olasiliklar": {"MS_X": 0.25}, "hazirlik": []}
    r = I.dondur(mac, tahmin, kok=kok / "tahminler", simdi=datetime.fromisoformat("2026-11-30T10:00:00+00:00"))
    satir = {"market_kodu": 1, "market_adi": "Maç Sonucu", "secenek_adi": "MS X", "oran": float(ORAN_IZI),
             "oynanabilirlik": "oynanabilir", "kesinlik": "kesin", "model_marketi": "MS_X", "bagimsiz_olasilik": 0.25,
             "basabas_esigi": round(1 / float(ORAN_IZI), 4), "beklenen_deger": round(0.25 * float(ORAN_IZI) - 1, 4)}
    (b / "fiyat_karsilastirma_1.json").write_text(json.dumps({
        "donmus_sha256": r["sha256"], "dondurma_utc": "2026-11-30T10:00:00+00:00",
        "karsilastirma_utc": "2026-11-30T12:05:00+00:00", "tahmin_durumu": "hesaplandi", "satirlar": [satir],
        "esdegerlik": {"sayilar": {}, "esdegerlik_gruplari": [{"olay": "beraberlik", "kapsam": "normal_sure",
                                                              "uyeler": [{**satir}]}], "alt_kume_fiyat_tutarsizliklari": []}}),
        encoding="utf-8")
    return r


class Entegrasyon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.donmus = fikstur_kur(cls.tmp)
        cls.port = _bos_port()
        env = {**os.environ, "FI_OUTPUT": str(cls.tmp), "PYTHONPATH": str(KOK / "lib") + os.pathsep + str(KOK)}
        cls.surec = subprocess.Popen([sys.executable, "-m", "uygulama", "--port", str(cls.port)], cwd=KOK, env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{cls.port}/arsiv", timeout=1)
                break
            except Exception:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.surec.terminate()
        cls.surec.wait(5)
        cls.surec.stderr.close()

    def iste(self, yol, veri=None, basliklar=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{yol}", data=veri, headers=basliklar or {},
                                     method="POST" if veri is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    # ------------------------------------------------------------------ gece yarısı
    def test_e1_gece_yarisi_kurali(self):
        k, h = self.iste("/?gun=2026-12-01")
        self.assertEqual(k, 200)
        self.assertIn("/mac/1'", h)           # 23:59 → dahil
        self.assertIn("/mac/3'", h)           # 00:00 → dahil
        self.assertNotIn("/mac/2'", h)        # ertesi gün 00:30 → dahil değil
        self.assertIn("00:00–03:00 arasındaki 1 maç bu güne dahil edilmedi", h)

    def test_e2_kismi_gun_secilemez(self):
        k, h = self.iste("/?gun=2026-12-02")
        self.assertEqual(k, 200)
        self.assertIn("Bu gün seçilemez", h)
        self.assertNotIn("/mac/2'", h)
        _, h = self.iste("/")
        self.assertNotIn("<option>2026-12-02</option>", h)

    # ------------------------------------------------------------------ MK-1 ve fiyat kilidi
    def test_e3_mk1_liste_ve_dondurulmamis_mac_oransiz(self):
        _, liste = self.iste("/?gun=2026-12-01")
        _, mac3 = self.iste("/mac/3")
        for h in (liste, mac3):
            self.assertNotIn(ORAN_IZI, h)
        self.assertIn("kilitli", mac3)
        self.assertNotIn("Başabaş", mac3)

    def test_e4_dondurulmus_macta_fiyat_ayrisma_olarak(self):
        _, h = self.iste("/mac/1")
        self.assertIn("doğrulandı", h)
        self.assertIn(ORAN_IZI, h)
        self.assertIn("model–piyasa ayrışması · doğrulama gerekli", h)
        self.assertNotIn("class='s iyi'", h)  # pozitif EV yeşil avantaj olarak gösterilmez

    # ------------------------------------------------------------------ geçersiz işlemler
    def test_e5_gecersiz_islemler(self):
        durumlar = {
            "yabanci_koken": self.iste("/islem/guncel", b"", {"Origin": "http://kotu.example"}),
            "yeniden_dondur": self.iste("/islem/dondur/1", b""),
            "onaysiz_lig": self.iste("/islem/dondur/3", b""),
            "bilinmeyen_mac": self.iste("/islem/dondur/999", b""),
            "gecersiz_gun": self.iste("/islem/bulten", b"gun=../../x"),
            "fiyat_kilitli": self.iste("/islem/fiyat/3", b""),
            "fiyat_ustune_yazma": self.iste("/islem/fiyat/1", b""),
            "bilinmeyen_islem": self.iste("/islem/sil", b""),
            "bilinmeyen_sayfa": self.iste("/mac/abc"),
        }
        beklenen = {"yabanci_koken": 403, "yeniden_dondur": 409, "onaysiz_lig": 409, "bilinmeyen_mac": 409,
                    "gecersiz_gun": 409, "fiyat_kilitli": 409, "fiyat_ustune_yazma": 409, "bilinmeyen_islem": 404,
                    "bilinmeyen_sayfa": 404}
        self.assertEqual({k: v[0] for k, v in durumlar.items()}, beklenen)
        for k, (_, h) in durumlar.items():
            self.assertNotIn("Traceback", h, k)
        self.assertIn("donmuş tahmin değiştirilmez", durumlar["yeniden_dondur"][1])
        self.assertIn("lig eşlemesi onaylı değil", durumlar["onaysiz_lig"][1])
        self.assertIn("üzerine yazılmaz", durumlar["fiyat_ustune_yazma"][1])
        # hiçbir geçersiz işlem arşive kayıt eklemedi
        self.assertEqual(len((self.tmp / "tahminler" / "kayit.jsonl").read_text().splitlines()), 1)

    # ------------------------------------------------------------------ dondurma bütünlüğü (en son: dosyayı bozar)
    def test_e9_bozulmus_donmus_tahmin(self):
        y = Path(self.donmus["yol"])
        asil = y.read_text()
        try:
            j = json.loads(asil)
            j["tahmin"]["olasiliklar"]["MS_X"] = 0.6
            y.write_text(json.dumps(j))
            _, h = self.iste("/mac/1")
            self.assertIn("Donmuş tahmin bozuk", h)
            self.assertNotIn(ORAN_IZI, h)        # fiyat kilitlenir
            _, a = self.iste("/arsiv")
            self.assertIn("HATA", a)
            k, f = self.iste("/islem/fiyat/1", b"")
            self.assertEqual(k, 409)
        finally:
            y.write_text(asil)


if __name__ == "__main__":
    unittest.main()
