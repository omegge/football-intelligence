import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from fi.model import surpriz_pilot as S


def mac(tarih, ev, dep, skor, ph, pa, sezon="2024-25", lig="en.1"):
    return {"yarisma": lig, "sezon": sezon, "tarih": tarih, "ev": ev, "dep": dep, "skor": skor,
            "P": {"H": ph, "D": 1 - ph - pa, "A": pa}}


class SurprizPilot(unittest.TestCase):
    def test_kategori(self):
        self.assertIsNone(S.kategori(0.49))
        self.assertEqual(S.kategori(0.5), "50-60")
        self.assertEqual(S.kategori(0.6), "60-70")
        self.assertEqual(S.kategori(0.79), "70-80")
        self.assertEqual(S.kategori(0.8), "80+")

    def test_favori_bilgisi(self):
        self.assertIsNone(S.favori_bilgisi(mac("2024-01-01", "A", "B", [1, 0], 0.4, 0.3)))
        f = S.favori_bilgisi(mac("2024-01-01", "A", "B", [0, 2], 0.2, 0.62))
        self.assertEqual((f["favori"], f["favori_saha"], f["etiket"]), ("B", "dep", "favori_kazandi"))
        f = S.favori_bilgisi(mac("2024-01-01", "A", "B", [1, 1], 0.7, 0.1))
        self.assertEqual(f["etiket"], "berabere")

    def havuz(self):
        ham = []
        for i in range(40):
            p = 0.5 + (i % 40) / 85
            skor = [0, 1] if i % 3 == 0 else ([1, 1] if i % 3 == 1 else [2, 0])
            ham.append(mac(f"2024-{1 + i % 12:02d}-{1 + i % 28:02d}", f"T{i}", f"R{i}", skor, p, 0.1))
        return [S.favori_bilgisi(m) for m in ham]

    def test_belirlilik_ve_kontrol(self):
        h = self.havuz()
        a, b = S.sec(h, 123), S.sec(h, 123)
        self.assertEqual([m["ev"] for m in a["surprizler"]], [m["ev"] for m in b["surprizler"]])
        self.assertTrue(all(m["etiket"] != "favori_kazandi" for m in a["surprizler"]))
        for s, k in zip(a["surprizler"], a["kontroller"]):
            if k:
                self.assertEqual(k["etiket"], "favori_kazandi")
                self.assertEqual((k["yarisma"], k["sezon"], k["favori_saha"]), (s["yarisma"], s["sezon"], s["favori_saha"]))
        favs = [m["favori"] for m in a["surprizler"]]
        self.assertEqual(len(favs), len(set(favs)))

    def test_oran_yok(self):
        import ast
        agac = ast.parse(Path(S.__file__).read_text(encoding="utf-8"))
        modul = [n.module or "" for n in ast.walk(agac) if isinstance(n, ast.ImportFrom)]
        modul += [a.name for n in ast.walk(agac) if isinstance(n, ast.Import) for a in n.names]
        for m in modul:
            for t in ("nesine", "pazar", "bulten", "odds", "fiyat"):
                self.assertNotIn(t, m.lower())

if __name__ == "__main__":
    unittest.main()
