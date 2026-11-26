"""Olay uzayı: 90 dakikalık maçın devre skorları ızgarası ve Nesine market kodlarının olay tanımları.

FİYAT İÇERMEZ. Hem olasılık katmanı (fi.model) hem fiyat denetimi (fi.pazar) bu tanımları kullanır; böylece iki katman
aynı olayı konuşur ama olasılık katmanı fiyat modülüne bağımlı olmaz (MK-1, tests/test_mk1_akis.py).
"""
from __future__ import annotations

import os
import re

import numpy as np

UST = int(os.environ.get("FI_PAZAR_UST", "7"))  # takım başına devre üst sınırı (8^4 = 4096 nokta; maçta ≤ 14)
# Sınır testi: FI_PAZAR_UST=9 ile eşdeğerlik grupları değişmemeli (tests/test_izgara_siniri.py).
_r = np.arange(UST + 1)
H1, A1, H2, A2 = (x.ravel() for x in np.meshgrid(_r, _r, _r, _r, indexing="ij"))
H, A = H1 + H2, A1 + A2
TUM = np.ones_like(H1, dtype=bool)
EN_BUYUK_ESIK = UST  # bir devre/takım eşiği bu değeri geçerse eşleme yapılmaz


# ---------------------------------------------------------------------------------------------------------
# Market aileleri -> seçenek adı -> olay
# ---------------------------------------------------------------------------------------------------------
TOPLAM_AU = {11, 12, 13, 155, 207}
EV_AU = {20, 212, 326}
DEP_AU = {29, 256, 328}
ADAY_DEP_AU = {329}            # aday (market_aday_eslemeleri.json): kesin değil
IY_AU = {14, 15, 209}
EV_IY_AU = {455}
DEP_IY_AU = {457}
MS_AU = {272, 342, 343}

_MS = {"1": H > A, "X": H == A, "2": H < A}
_IY = {"1": H1 > A1, "X": H1 == A1, "2": H1 < A1}
_2Y = {"1": H2 > A2, "X": H2 == A2, "2": H2 < A2}
KG = (H > 0) & (A > 0)
KG1 = (H1 > 0) & (A1 > 0)
KG2 = (H2 > 0) & (A2 > 0)


def _yarim_cizgi(c: float) -> bool:
    return abs(c * 2 - round(c * 2)) < 1e-9 and abs(c - round(c)) > 1e-9


def _au(deger: np.ndarray, c: float) -> dict:
    return {"Alt": deger < c, "Üst": deger > c}


def _skor(metin: str):
    m = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)\s*", metin)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _tablo(kod: int, cizgi: float, market_adi: str, handikap: dict | None):
    """(ad->maske sözlüğü, kesinlik, neden) ya da None. Beklenen adlar sözlükteki adlardır."""
    c = cizgi
    if kod in TOPLAM_AU | EV_AU | DEP_AU | ADAY_DEP_AU | IY_AU | EV_IY_AU | DEP_IY_AU | MS_AU or kod == 446 or kod == 459:
        if not _yarim_cizgi(c):
            return None, "tam ya da sıfır çizgi: iade olasılığı var, ikili olay değil"
        # Izgara sınırı: tek devre/takım değeri UST ile, maç değeri 2·UST ile sınırlı. Sınırdaki değeri kullanan olay
        # ("≥ 14" ile "= 14" gibi) ızgarada ayırt edilemez → çizgi sınırdan en az 1,5 uzak olmalı.
        sinir = (EN_BUYUK_ESIK - 1.5) if kod in IY_AU | EV_IY_AU | DEP_IY_AU or kod == 459 else (2 * EN_BUYUK_ESIK - 1.5)
        if c > sinir:
            return None, "çizgi ızgara sınırına çok yakın"
    if kod in TOPLAM_AU:
        return _au(H + A, c), None
    if kod in EV_AU:
        return _au(H, c), None
    if kod in DEP_AU:
        return _au(A, c), None
    if kod in ADAY_DEP_AU:
        return ({k: v for k, v in _au(A, c).items()},
                "aday ad (market_aday_eslemeleri.json, 1/2 bağımsız doğrulama); seçenek adları 'seçenek 1/2'")
    if kod in IY_AU:
        return _au(H1 + A1, c), None
    if kod in EV_IY_AU:
        return _au(H1, c), None
    if kod in DEP_IY_AU:
        return _au(A1, c), None
    if kod == 1:
        return {"MS 1": _MS["1"], "MS X": _MS["X"], "MS 2": _MS["2"]}, None
    if kod == 3:
        return {"ÇŞ 1-X": H >= A, "ÇŞ 1-2": H != A, "ÇŞ X-2": H <= A}, None
    if kod == 7:
        return {"1.Y 1": _IY["1"], "1.Y X": _IY["X"], "1.Y 2": _IY["2"]}, None
    if kod == 8:
        return {"1.Y 1-X": H1 >= A1, "1.Y 1-2": H1 != A1, "1.Y X-2": H1 <= A1}, None
    if kod == 9:
        return {"2.Y 1": _2Y["1"], "2.Y X": _2Y["X"], "2.Y 2": _2Y["2"]}, None
    if kod == 38:
        return {"Var": KG, "Yok": ~KG}, None
    if kod == 452:
        return {"Var": KG1, "Yok": ~KG1}, None
    if kod == 599:
        return {"Var": KG2, "Yok": ~KG2}, None
    if kod == 801:
        return {"Evet/Evet": KG1 & KG2, "Evet/Hayır": KG1 & ~KG2, "Hayır/Evet": ~KG1 & KG2,
                "Hayır/Hayır": ~KG1 & ~KG2}, None
    if kod in MS_AU:
        alt, ust = H + A < c, H + A > c
        t = {}
        for s, m in _MS.items():
            t[f"MS{s} & Alt"] = m & alt
            t[f"MS{s} & Üst"] = m & ust
        return t, None
    if kod == 414:
        t = {}
        for s, m in _MS.items():
            t[f"MS{s} & Var"] = m & KG
            t[f"MS{s} & Yok"] = m & ~KG
        return t, None
    if kod == 446:
        alt, ust = H + A < c, H + A > c
        return {"Alt & Var": alt & KG, "Üst & Var": ust & KG, "Alt & Yok": alt & ~KG, "Üst & Yok": ust & ~KG}, None
    if kod == 459:
        alt, ust = H1 + A1 < c, H1 + A1 > c
        t = {}
        for s, m in _IY.items():
            t[f"1.Y {s} & Alt"] = m & alt
            t[f"1.Y {s} & Üst"] = m & ust
        return t, None
    if kod == 416:
        t = {}
        for s, m in _IY.items():
            t[f"1.Y {s} & Var"] = m & KG1
            t[f"1.Y {s} & Yok"] = m & ~KG1
        return t, None
    if kod == 43:
        T = H + A
        return {"0-1 Gol": T <= 1, "2-3 Gol": (T >= 2) & (T <= 3), "4-5 Gol": (T >= 4) & (T <= 5),
                "6+ Gol": T >= 6}, None
    if kod == 49:
        return {"Tek": (H + A) % 2 == 1, "Çift": (H + A) % 2 == 0}, None
    if kod == 450:
        return {"Tek": (H1 + A1) % 2 == 1, "Çift": (H1 + A1) % 2 == 0}, None
    if kod == 48:
        a, b = H1 + A1, H2 + A2
        return {"1. Y": a > b, "Eşit": a == b, "2. Y": a < b}, None
    if kod == 586:
        return {"1.": H1 > H2, "Eşit": H1 == H2, "2.": H1 < H2}, None
    if kod == 587:
        return {"1.": A1 > A2, "Eşit": A1 == A2, "2.": A1 < A2}, None
    if kod == 584:
        m = (H1 > A1) | (H2 > A2)
        return {"Evet": m, "Hayır": ~m}, None
    if kod == 585:
        m = (A1 > H1) | (A2 > H2)
        return {"Evet": m, "Hayır": ~m}, None
    if kod == 591:
        m = (H1 > A1) & (H2 > A2)
        return {"Evet": m, "Hayır": ~m}, None
    if kod == 592:
        m = (A1 > H1) & (A2 > H2)
        return {"Evet": m, "Hayır": ~m}, None
    if kod == 295:
        m = (H1 > 0) & (H2 > 0)
        return {"Atar": m, "Atamaz": ~m}, None
    if kod == 296:
        m = (A1 > 0) & (A2 > 0)
        return {"Atar": m, "Atamaz": ~m}, None
    if kod == 528:
        m = (H1 + A1 < 1.5) & (H2 + A2 < 1.5)
        return {"Evet": m, "Hayır": ~m}, None
    if kod == 529:
        m = (H1 + A1 > 1.5) & (H2 + A2 > 1.5)
        return {"Evet": m, "Hayır": ~m}, None
    if kod == 588:
        d = H - A
        return {"Ev. 3+": d >= 3, "Ev. 2": d == 2, "Ev. 1": d == 1, "0": d == 0, "Dep. 1": d == -1,
                "Dep. 2": d == -2, "Dep. 3+": d <= -3}, None
    if kod == 5:
        t = {}
        for i, mi in _IY.items():
            for s, ms in _MS.items():
                t[f"{i}/{s}"] = mi & ms
        return t, None
    if kod == 268:
        if not handikap or not handikap.get("cizgi_isaretiyle_tutarli"):
            return None, "handikap yönü addan doğrulanamadı"
        hc = float(handikap["cizgi"])
        if abs(hc - round(hc)) > 1e-9:
            return None, "yarım handikap çizgisi: 3 yollu HMS biçimiyle uyuşmuyor"
        d = H - A + hc
        return {"HMS 1": d > 0, "HMS X": d == 0, "HMS 2": d < 0}, None
    return None, None


def _skor_olayi(kod: int, ad: str):
    """777/779/571 seçenekleri. (maske, kesinlik_nedeni) ya da (None, eşlenmeme nedeni)."""
    if kod == 777:
        s = _skor(ad)
        if s:
            if max(s) > 2 * UST - 1:
                return None, "skor ızgara sınırında ya da dışında"
            return (H == s[0]) & (A == s[1]), None
    elif kod == 779:
        s = _skor(ad)
        if s:
            if max(s) > UST - 1:
                return None, "devre skoru ızgara sınırında ya da dışında"
            return (H1 == s[0]) & (A1 == s[1]), None
    elif kod == 571:
        p = [x.strip() for x in ad.split("/")]
        if len(p) == 2:
            a, b = _skor(p[0]), _skor(p[1])
            if a and b:
                if max(a) > UST - 1 or max(b) > 2 * UST - 1 or b[0] - a[0] > UST - 1 or b[1] - a[1] > UST - 1:
                    return None, "skor ızgara sınırında ya da dışında"
                return (H1 == a[0]) & (A1 == a[1]) & (H == b[0]) & (A == b[1]), None
            return None, f"'{ad}': ikinci kısım skor değil ('4+' anlamı market kuralına bağlı)"
    return None, f"'{ad}' skor olarak çözümlenemedi"


SKOR_KODLARI = {777, 779, 571}
