"""Ortak skor dağılımından market olasılıkları ve tutarlılık denetimi (E aşaması).

Bütün marketler AYNI skor matrisinden türetilir; matris dışı ek varsayım yoktur. Devre (1Y/2Y) marketleri burada YOKTUR:
maç sonu skor matrisi devre dağılımını belirlemez (F aşaması ayrı veri ve model gerektirir).
"""
from __future__ import annotations

import numpy as np

from .goller import GolModeli, skor_matrisi

AU_CIZGILERI = (0.5, 1.5, 2.5, 3.5, 4.5)
TAKIM_CIZGILERI = (0.5, 1.5, 2.5)
DOGRU_SKORLAR = ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (0, 2), (2, 1), (1, 2), (2, 2))


def olaylar(maks: int = 10) -> dict[str, np.ndarray]:
    """Market adı -> (maks+1)x(maks+1) boolean maske (i = ev golü, j = deplasman golü)."""
    i, j = np.indices((maks + 1, maks + 1))
    return olay_maskeleri(i, j)


def olay_maskeleri(i: np.ndarray, j: np.ndarray) -> dict[str, np.ndarray]:
    """Aynı market tanımları herhangi bir (ev golü, deplasman golü) dizisi üzerinde (ör. fi.pazar ızgarası)."""
    t = i + j
    o = {"MS_1": i > j, "MS_X": i == j, "MS_2": i < j,
         "CS_1X": i >= j, "CS_12": i != j, "CS_X2": i <= j,
         "KG_var": (i > 0) & (j > 0), "KG_yok": ~((i > 0) & (j > 0)),
         "tek": t % 2 == 1, "cift": t % 2 == 0,
         "aralik_0_1": t <= 1, "aralik_2_3": (t >= 2) & (t <= 3), "aralik_4_5": (t >= 4) & (t <= 5), "aralik_6p": t >= 6,
         "H-1_1": i - j > 1, "H-1_X": i - j == 1, "H-1_2": i - j < 1}
    for c in AU_CIZGILERI:
        o[f"AU{c}_alt"] = t < c
        o[f"AU{c}_ust"] = t > c
    for c in TAKIM_CIZGILERI:
        o[f"ev{c}_alt"], o[f"ev{c}_ust"] = i < c, i > c
        o[f"dep{c}_alt"], o[f"dep{c}_ust"] = j < c, j > c
    for s, m in (("1", i > j), ("X", i == j), ("2", i < j)):
        o[f"MS{s}_AU2.5_alt"] = m & (t < 2.5)
        o[f"MS{s}_AU2.5_ust"] = m & (t > 2.5)
        o[f"MS{s}_KG_var"] = m & (i > 0) & (j > 0)
        o[f"MS{s}_KG_yok"] = m & ~((i > 0) & (j > 0))
    for a, b in DOGRU_SKORLAR:
        o[f"skor_{a}_{b}"] = (i == a) & (j == b)
    return o


OLAYLAR = olaylar()
# Bölümleme aileleri (her biri ayrık ve kapsayıcı olmalı)
BOLUMLER = {"MS": ["MS_1", "MS_X", "MS_2"], "KG": ["KG_var", "KG_yok"], "tek_cift": ["tek", "cift"],
            "aralik": ["aralik_0_1", "aralik_2_3", "aralik_4_5", "aralik_6p"], "H-1": ["H-1_1", "H-1_X", "H-1_2"],
            "MS_AU2.5": [f"MS{s}_AU2.5_{y}" for s in "1X2" for y in ("alt", "ust")],
            "MS_KG": [f"MS{s}_KG_{y}" for s in "1X2" for y in ("var", "yok")],
            **{f"AU{c}": [f"AU{c}_alt", f"AU{c}_ust"] for c in AU_CIZGILERI}}


def market_olasiliklari(matris: np.ndarray) -> dict[str, float]:
    return {ad: float(matris[m].sum()) for ad, m in OLAYLAR.items()}


def tutarlilik_denetimi(p: dict[str, float], matris: np.ndarray, tol: float = 1e-9) -> list[str]:
    """Ortak dağılım kimlikleri. Boş liste = tutarlı."""
    hata = []
    if abs(matris.sum() - 1.0) > 1e-6:
        hata.append(f"matris toplamı {matris.sum():.8f} (kesik kuyruk > 1e-6)")
    if (matris < -tol).any():
        hata.append("negatif olasılık")
    for ad, uyeler in BOLUMLER.items():
        s = sum(p[u] for u in uyeler)
        if abs(s - matris.sum()) > tol:
            hata.append(f"{ad}: bölüm toplamı {s:.12f} ≠ {matris.sum():.12f}")
    for a, b, c in (("CS_1X", "MS_1", "MS_X"), ("CS_12", "MS_1", "MS_2"), ("CS_X2", "MS_X", "MS_2")):
        if abs(p[a] - p[b] - p[c]) > tol:
            hata.append(f"{a} ≠ {b}+{c}")
    altlar = [p[f"AU{c}_alt"] for c in AU_CIZGILERI]
    if any(x > y + tol for x, y in zip(altlar, altlar[1:])):
        hata.append("alt(c) çizgiyle artan değil")
    for s in "1X2":
        if abs(p[f"MS{s}_AU2.5_alt"] + p[f"MS{s}_AU2.5_ust"] - p[f"MS_{s}"]) > tol:
            hata.append(f"MS{s}&AÜ bileşenleri MS_{s} toplamını vermiyor")
        if abs(p[f"MS{s}_KG_var"] + p[f"MS{s}_KG_yok"] - p[f"MS_{s}"]) > tol:
            hata.append(f"MS{s}&KG bileşenleri MS_{s} toplamını vermiyor")
    if abs(p["skor_0_0"] - p["AU0.5_alt"]) > tol:
        hata.append("0-0 ≠ 0,5 alt")
    if abs(p["skor_1_1"] - (p["MSX_AU2.5_alt"] - p["skor_0_0"])) > tol:
        hata.append("1-1 ≠ (MS X & 2,5 alt) − 0-0")
    return hata


def gozlenen(ev_gol: int, dep_gol: int) -> dict[str, bool]:
    """Gerçekleşen olaylar, KIRPMA YAPILMADAN (v1'de 10'a kırpma vardı: 0-13 maçında tek/çift yanlış çıkıyordu)."""
    o = olay_maskeleri(np.array([int(ev_gol)]), np.array([int(dep_gol)]))
    return {ad: bool(mask[0]) for ad, mask in o.items()}


class MatrisKaydedici:
    """GolModeli'nin maç öncesi λ'larını ve ρ'sunu kaydeder (market türetimi kayıttan sonra yapılır)."""

    def __init__(self, kaynak: GolModeli, dixon_coles: bool):
        self.kaynak = kaynak
        self.dc = dixon_coles
        self.ad = "dixon_coles" if dixon_coles else "poisson"
        self.kesim = None

    def hazirla(self, gecmis, tarih, takimlar):
        if self.dc:
            self.kaynak.hazirla(gecmis, tarih, takimlar)
        self.kesim = self.kaynak.kesim
        return self

    def tahmin(self, mac: dict) -> dict:
        lh, la = self.kaynak.oranlar(mac["ev"], mac["dep"])
        return {"lh": lh, "la": la, "rho": self.kaynak.rho if self.dc else 0.0}


def matris_kayittan(t: dict, maks: int = 10) -> np.ndarray:
    return skor_matrisi(t["lh"], t["la"], t["rho"], maks)
