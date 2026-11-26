"""MK-1 yapısal denetimi (kelime taramasının ötesi): içe aktarma grafiği, çalışma anında açılan dosyalar,
dondurulmuş olasılığın fiyat karşılaştırmasından etkilenmemesi (MK1–MK5)."""
import ast
import builtins
import hashlib
import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
LIB = KOK / "lib"
FIYAT_MODULLERI = {"fi.pazar", "fi.pazar.esdegerlik", "nesine_bulletin", "bulten_dogrulama"}
# Olasılık üreten ya da olasılığa veri taşıyan modüller
OLASILIK_KOKLERI = ("fi.model", "fi.kaynaklar", "fi.haber", "fi.girdi", "fi.takim_adlari", "fi.kanit", "fi.http",
                    "fi.eslemeler")


def _modul_adi(yol: Path) -> str:
    parca = list(yol.relative_to(LIB).with_suffix("").parts)
    if parca[-1] == "__init__":
        parca = parca[:-1]
    return ".".join(parca)


def ice_aktarma_grafigi() -> dict[str, set]:
    g = {}
    for f in LIB.rglob("*.py"):
        ad = _modul_adi(f)
        paket = ad if f.name == "__init__.py" else ad.rsplit(".", 1)[0]
        hedef = set()
        for dugum in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(dugum, ast.Import):
                hedef |= {a.name for a in dugum.names}
            elif isinstance(dugum, ast.ImportFrom):
                if dugum.level:
                    taban = paket.split(".")[: len(paket.split(".")) - dugum.level + 1]
                    mod = ".".join(taban + ([dugum.module] if dugum.module else []))
                else:
                    mod = dugum.module or ""
                hedef.add(mod)
                hedef |= {f"{mod}.{a.name}" for a in dugum.names}
        g[ad] = hedef
    return g


def gecisli(g: dict, bas: str) -> set:
    gor, yigin = set(), [bas]
    while yigin:
        m = yigin.pop()
        for h in g.get(m, ()):
            if h not in gor:
                gor.add(h)
                yigin.append(h)
    return gor


class MK(unittest.TestCase):
    def test_MK1_olasilik_modulleri_fiyat_modulune_bagli_degil(self):
        g = ice_aktarma_grafigi()
        for m in g:
            if m.startswith(OLASILIK_KOKLERI):
                kotu = gecisli(g, m) & FIYAT_MODULLERI
                self.assertFalse(kotu, f"{m} → {kotu}")

    def test_MK2_tahmin_fonksiyonu_fiyat_modulu_yuklemez(self):
        """is_akisi.bagimsiz_tahmin gövdesindeki içe aktarmalar fiyat modülü içermez (fiyat yalnızca fiyat_karsilastir'da)."""
        agac = ast.parse((LIB / "fi" / "is_akisi.py").read_text(encoding="utf-8"))
        fonk = {d.name: d for d in agac.body if isinstance(d, ast.FunctionDef)}
        for ad in ("bagimsiz_tahmin", "dondur", "gunun_maclari", "lig_eslemesi"):
            for d in ast.walk(fonk[ad]):
                if isinstance(d, ast.ImportFrom):
                    # 'model.pazar_modelleri' olasılık katmanıdır; fiyat paketi 'fi.pazar' (göreli: 'pazar') yasak
                    self.assertFalse((d.module or "") in ("pazar", "pazar.esdegerlik", "fi.pazar"), ad)
        ust = [d for d in agac.body if isinstance(d, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any((getattr(d, "module", "") or "") in ("pazar", "fi.pazar") for d in ust))

    def test_MK3_tahmin_sirasinda_bulten_dosyasi_acilmaz(self):
        import sys
        sys.path.insert(0, str(KOK / "tests"))
        import test_is_akisi as T
        from fi import is_akisi as K
        acilan = []
        asil_open, asil_io = builtins.open, io.open

        def izle(dosya, *a, **k):
            acilan.append(str(dosya))
            return asil_open(dosya, *a, **k)
        builtins.open = io.open = izle
        try:
            t = K.bagimsiz_tahmin(T.fikstur()["maclar"][0], T.lig_verisi(), "xx.1", kapsam=T.KAPSAM)
        finally:
            builtins.open, io.open = asil_open, asil_io
        self.assertEqual(t["durum"], "hesaplandi")
        self.assertFalse([p for p in acilan if "bulten_" in p or "nesine" in p.lower()], acilan)

    def test_MK4_fiyat_karsilastirmasi_donmus_kaydi_degistirmez(self):
        import sys
        sys.path.insert(0, str(KOK / "tests"))
        import test_is_akisi as T
        from fi import is_akisi as K
        d = Path(tempfile.mkdtemp())
        mac = T.fikstur()["maclar"][0]
        t = K.bagimsiz_tahmin(mac, T.lig_verisi(), "xx.1", kapsam=T.KAPSAM)
        z = K.dondur(mac, t, d, simdi=datetime(2026, 11, 26, 10, tzinfo=timezone.utc))
        once = hashlib.sha256(Path(z["yol"]).read_bytes()).hexdigest()
        nes = {"mac_kodu": 1, "marketler": [{"market_kodu": 1, "market_adi": "Maç Sonucu", "cizgi": 0.0,
               "market_durumu_MS": 1, "adsiz": False, "handikap": None, "secenekler": [
                   {"secenek_no": 1, "secenek_adi": "MS 1", "oran": 1.01, "oynanabilirlik": "oynanabilir"}]}]}
        k = K.fiyat_karsilastir(Path(z["yol"]), nes, simdi=datetime(2026, 11, 26, 11, tzinfo=timezone.utc))
        self.assertEqual(once, hashlib.sha256(Path(z["yol"]).read_bytes()).hexdigest())
        self.assertAlmostEqual(k["satirlar"][0]["bagimsiz_olasilik"], round(t["olasiliklar"]["MS_1"], 4))

    def test_MK5_degerlendirme_kosuculari_yalniz_sportif_kaynak_okur(self):
        g = ice_aktarma_grafigi()
        for m in ("fi.model.e_asamasi", "fi.model.f_asamasi", "fi.model.h_asamasi", "fi.model.ligler_arasi",
                  "fi.model.yeni_gol"):
            if m not in g:
                continue
            kaynaklar = {x for x in gecisli(g, m) if x.startswith("fi.kaynaklar.")}
            self.assertTrue(kaynaklar <= {"fi.kaynaklar.openfootball", "fi.kaynaklar.openfootball.KOK",
                                          "fi.kaynaklar.guncel", "fi.kaynaklar.footballdataorg"} | {
                x for x in kaynaklar if x.split(".")[2] in ("openfootball", "guncel", "footballdataorg")}, kaynaklar)


if __name__ == "__main__":
    unittest.main()
