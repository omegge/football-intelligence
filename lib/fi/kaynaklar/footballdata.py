"""football-data.co.uk okuyucusu (sonuçlar ve maç istatistikleri).

Beklenen biçim (ilk gerçek erişimde doğrulanacak; DOGRULANMIS_BICIM = False):
  Ana ligler : https://www.football-data.co.uk/mmz4281/<SEZON>/<LIG>.csv   (SEZON ör. 2526, LIG ör. E0, T1)
               Sütunlar: Div, Date, Time, HomeTeam, AwayTeam, FTHG, FTAG, FTR, HTHG, HTAG, HTR, Referee,
                         HS, AS, HST, AST, HF, AF, HC, AC, HY, AY, HR, AR … + bahis oranları
  Ek ligler  : https://www.football-data.co.uk/new/<ULKE>.csv
               Sütunlar: Country, League, Season, Date, Time, Home, Away, HG, AG, Res … + bahis oranları
Dosyalardaki BÜTÜN bahis oranı sütunları atılır (beyaz liste); atılan sütunlar yalnızca sayılır.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime

TABAN = "https://www.football-data.co.uk"
DOGRULANMIS_BICIM = False

# İzinli (oran olmayan) sütunlar -> standart ad
ANA = {"Div": "lig", "Date": "tarih", "Time": "saat", "HomeTeam": "ev", "AwayTeam": "deplasman",
       "FTHG": "ev_gol", "FTAG": "dep_gol", "FTR": "sonuc", "HTHG": "iy_ev_gol", "HTAG": "iy_dep_gol", "HTR": "iy_sonuc",
       "Referee": "hakem", "HS": "ev_sut", "AS": "dep_sut", "HST": "ev_isabetli", "AST": "dep_isabetli",
       "HF": "ev_faul", "AF": "dep_faul", "HC": "ev_korner", "AC": "dep_korner", "HY": "ev_sari", "AY": "dep_sari",
       "HR": "ev_kirmizi", "AR": "dep_kirmizi", "HO": "ev_ofsayt", "AO": "dep_ofsayt", "HHW": "ev_direk", "AHW": "dep_direk",
       "HBP": "ev_kart_puani", "ABP": "dep_kart_puani", "Attendance": "seyirci"}
EK = {"Country": "ulke", "League": "lig", "Season": "sezon", "Date": "tarih", "Time": "saat", "Home": "ev",
      "Away": "deplasman", "HG": "ev_gol", "AG": "dep_gol", "Res": "sonuc"}
SAYISAL = {"ev_gol", "dep_gol", "iy_ev_gol", "iy_dep_gol", "ev_sut", "dep_sut", "ev_isabetli", "dep_isabetli",
           "ev_faul", "dep_faul", "ev_korner", "dep_korner", "ev_sari", "dep_sari", "ev_kirmizi", "dep_kirmizi",
           "ev_ofsayt", "dep_ofsayt", "ev_direk", "dep_direk", "ev_kart_puani", "dep_kart_puani", "seyirci"}
# Bilinen oran sütunu desenleri: yalnızca atılan sütunların doğru sınıflandığını raporlamak için
ORAN_DESENI = re.compile(r"^(B365|BW|IW|PS|WH|VC|LB|SJ|GB|BS|SB|SY|Max|Avg|Bb|BF|1XB|CL|P>|P<|AH|B365>|B365<|PSC|"
                         r"Max>|Max<|Avg>|Avg<)|(H|D|A|>2\.5|<2\.5|CH|CD|CA|AHH|AHA)$")


class BicimHatasi(ValueError):
    pass


def ana_url(sezon: str, lig: str) -> str:
    if not re.fullmatch(r"\d{4}", sezon) or not re.fullmatch(r"[A-Z]{1,3}\d?", lig):
        raise ValueError(f"geçersiz sezon/lig: {sezon}/{lig}")
    return f"{TABAN}/mmz4281/{sezon}/{lig}.csv"


def ek_url(ulke_kodu: str) -> str:
    if not re.fullmatch(r"[A-Z]{3}", ulke_kodu):
        raise ValueError(f"geçersiz ülke kodu: {ulke_kodu}")
    return f"{TABAN}/new/{ulke_kodu}.csv"


def _tarih(s: str) -> str | None:
    s = (s or "").strip()
    for b in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, b).date().isoformat()
        except ValueError:
            continue
    return None


def _sayi(x):
    x = (x or "").strip()
    if x == "":
        return None
    try:
        return int(x)
    except ValueError:
        try:
            return float(x)
        except ValueError:
            return None


def ayristir(metin: str) -> dict:
    """Dönüş: {'bicim': 'ana'|'ek', 'maclar': [...], 'atilan_sutunlar': [...], 'tanimsiz_atilan': [...]}.
    Oran sütunları hiçbir zaman 'maclar' içine girmez."""
    satirlar = list(csv.reader(io.StringIO(metin.lstrip("﻿"))))
    if not satirlar:
        raise BicimHatasi("boş dosya")
    baslik = [b.strip() for b in satirlar[0]]
    if {"HomeTeam", "AwayTeam", "FTHG", "FTAG"} <= set(baslik):
        bicim, harita = "ana", ANA
    elif {"Home", "Away", "HG", "AG"} <= set(baslik):
        bicim, harita = "ek", EK
    else:
        raise BicimHatasi(f"football-data biçimi tanınmadı; başlık: {baslik[:12]}")
    alinan = {i: harita[b] for i, b in enumerate(baslik) if b in harita}
    atilan = [b for b in baslik if b and b not in harita]
    maclar = []
    for n, r in enumerate(satirlar[1:], 2):
        if not any(c.strip() for c in r):
            continue
        m = {"satir": n}
        for i, ad in alinan.items():
            v = r[i] if i < len(r) else ""
            m[ad] = _sayi(v) if ad in SAYISAL else (v.strip() or None)
        m["tarih"] = _tarih(m.get("tarih") or "")
        if not (m.get("ev") and m.get("deplasman") and m["tarih"]):
            continue
        maclar.append(m)
    return {"bicim": bicim, "maclar": maclar, "atilan_sutunlar": atilan,
            "tanimsiz_atilan": [b for b in atilan if not ORAN_DESENI.search(b)]}


def takim_maclari(maclar: list[dict], takim: str, once: str | None = None, adet: int | None = None) -> list[dict]:
    """Bir takımın (kaynaktaki adıyla) maçları, tarihe göre yeniden eskiye; 'once' tarihinden (dahil değil) önceki."""
    s = [m for m in maclar if takim in (m["ev"], m["deplasman"]) and (once is None or m["tarih"] < once)
         and m.get("ev_gol") is not None]
    s.sort(key=lambda m: (m["tarih"], m.get("saat") or ""), reverse=True)
    return s[:adet] if adet else s


def takim_adlari(maclar: list[dict]) -> list[str]:
    return sorted({m["ev"] for m in maclar} | {m["deplasman"] for m in maclar})
