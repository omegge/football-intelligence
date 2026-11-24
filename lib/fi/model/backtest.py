"""Kronolojik (yürüyen) backtest motoru.

Sızıntı korumaları:
1. Maçlar tarih sırasıyla işlenir. Bir tarihteki bütün maçlar önce tahmin edilir; sonuçlar ancak ondan sonra
   modellere verilir (aynı günün sonuçları birbirini etkilemez).
2. Kestirim gerektiren modellere (`hazirla`) yalnızca tahmin tarihinden ÖNCEKİ maçlar verilir; her tahminde eğitim
   kesim tarihi kaydedilir ve `kesim < tahmin tarihi` denetlenir (ihlalde AssertionError).
3. Sezon başında yalnızca o sezonun takım listesi verilir (fikstürle maç öncesinde bilinen bilgi).
4. Girdi maçlarında oran/bahis alanı bulunursa motor çalışmaz (MK-1, `girdi.oransiz_mi`).
"""

from __future__ import annotations

from collections import Counter

from ..girdi import oransiz_mi


def sonuc_kodu(m: dict) -> str:
    return "H" if m["ev_gol"] > m["dep_gol"] else ("D" if m["ev_gol"] == m["dep_gol"] else "A")


class FrekansModeli:
    """Taban model: tahmin tarihinden önceki bütün maçlardaki H/D/A oranları (Laplace düzeltmeli)."""
    ad = "taban"

    def __init__(self):
        self.p = {"H": 1 / 3, "D": 1 / 3, "A": 1 / 3}
        self.kesim = None

    def hazirla(self, gecmis, tarih, takimlar):
        c = Counter(sonuc_kodu(m) for m in gecmis)
        n = sum(c.values())
        self.p = {k: (c[k] + 1) / (n + 3) for k in ("H", "D", "A")}
        self.kesim = gecmis[-1]["tarih"] if gecmis else None
        return self

    def tahmin(self, mac):
        return dict(self.p)


def yuruyen_test(maclar: list[dict], modeller: list, baslangic: str, bitis: str | None = None,
                 sezon_takimlari: dict | None = None, elo_kaydi=None) -> list[dict]:
    """`baslangic` ≤ tarih (≤ `bitis`) aralığındaki maçlar için tahmin kayıtları döndürür. Daha önceki maçlar yalnızca
    ısınma/geçmiş olarak kullanılır. `elo_kaydi` verilirse (EloModeli) her maç için maç öncesi göreli Elo yazılır."""
    oransiz_mi(maclar, "backtest_girdisi")
    maclar = sorted(maclar, key=lambda m: (m["tarih"], m.get("saat") or "", m["ev"]))
    gunler: dict[str, list] = {}
    for m in maclar:
        gunler.setdefault(m["tarih"], []).append(m)
    sezon_takimlari = sezon_takimlari or {}
    cevrimici = [md for md in modeller if hasattr(md, "sonuc_isle")]
    kestirimli = [md for md in modeller if hasattr(md, "hazirla")]
    gecmis: list[dict] = []
    kayitlar: list[dict] = []
    elo_gecmis: list[dict] = []
    aktif_sezon = None
    for tarih in sorted(gunler):
        gunun = gunler[tarih]
        sezon = gunun[0]["sezon"]
        if sezon != aktif_sezon:
            takimlar = sezon_takimlari.get(sezon) or {t for m in maclar if m["sezon"] == sezon for t in (m["ev"], m["dep"])}
            for md in cevrimici + ([elo_kaydi] if elo_kaydi and elo_kaydi not in cevrimici else []):
                md.sezon_basla(sezon, takimlar)
            aktif_sezon = sezon
        if gecmis and gecmis[-1]["tarih"] >= tarih:
            raise AssertionError("sızıntı: geçmiş veri tahmin tarihini aşıyor")
        degerlendir = tarih >= baslangic and (bitis is None or tarih <= bitis)
        if degerlendir:
            for md in kestirimli:
                md.hazirla(gecmis, tarih, sezon_takimlari.get(sezon) or takimlar)
                if md.kesim is not None and md.kesim >= tarih:
                    raise AssertionError(f"sızıntı: {md.ad} eğitim kesimi {md.kesim} ≥ tahmin tarihi {tarih}")
        for m in gunun:
            if elo_kaydi is not None:
                ort = sum(elo_kaydi.puan[t] for t in elo_kaydi.onceki_takimlar) / len(elo_kaydi.onceki_takimlar)
                goreli = {"elo_ev_goreli": elo_kaydi.puan[m["ev"]] - ort, "elo_dep_goreli": elo_kaydi.puan[m["dep"]] - ort}
            else:
                goreli = {}
            if degerlendir:
                kayitlar.append({"tarih": tarih, "sezon": sezon, "ev": m["ev"], "dep": m["dep"],
                                 "ev_ad": m.get("ev_ad"), "dep_ad": m.get("dep_ad"),
                                 "ev_gol": m["ev_gol"], "dep_gol": m["dep_gol"], "sonuc": sonuc_kodu(m),
                                 "kaynak": m.get("kaynak", "openfootball"),
                                 "egitim_kesimi": gecmis[-1]["tarih"] if gecmis else None,
                                 "tahmin": {md.ad: md.tahmin(m) for md in modeller}, **goreli})
            if goreli:
                elo_gecmis.append({"tarih": tarih, "ev": m["ev"], "dep": m["dep"], "sonuc": sonuc_kodu(m), **goreli})
        for m in gunun:                                   # sonuçlar ancak bütün günün tahminlerinden sonra
            for md in cevrimici:
                md.sonuc_isle(m)
            if elo_kaydi is not None and elo_kaydi not in cevrimici:
                elo_kaydi.sonuc_isle(m)
        gecmis.extend(gunun)
    for k in kayitlar:
        if k["egitim_kesimi"] is not None and k["egitim_kesimi"] >= k["tarih"]:
            raise AssertionError("sızıntı denetimi başarısız")
    yuruyen_test.elo_gecmisi = elo_gecmis
    return kayitlar
