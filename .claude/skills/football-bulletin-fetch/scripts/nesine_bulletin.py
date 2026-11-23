#!/usr/bin/env python3
"""Football Intelligence - Nesine futbol bülteni çekici ve işleyicisi.

Kaynak: kullanıcının Colab not defteri nesine_gunluk_(3).ipynb (kaynak/ klasöründe). Bu modül onun
çalışan mantığını (bülten adresi, düzleştirme, 104 marketlik sözlükle isimlendirme, çizgi/handikap
adları, Türkiye saati) korur ve şu düzeltmeleri yapar:

  1. Canlı maçlar, maç öncesi bültende OLMAMALARINA bakılarak değil, geldikleri canlı akışa göre
     sınıflandırılır. Maç öncesi ve canlı veri ayrı dosyalara yazılır.
  2. Market adları önce JSON'un kendi alanından (MN / ON), yoksa sözlükten gelir. Maça özel
     marketlerin (oyuncu, kaleci, takım istatistiği, kombo) seçenek etiketleri ASLA sözlükten
     alınmaz: başka maçtan kalmış oyuncu adları taşınamaz.
  3. Türkiye saatine göre isteğe bağlı tarih filtresi.
  4. API yapısı doğrulaması ve eksik veri raporu; hiçbir seçenek sessizce düşmez.

Ağ: yalnızca cdnbulten.nesine.com ve bulten.nesine.com, her akış için tek GET, dürüst User-Agent.
401/403/429 ya da HTML yanıtı erişim engeli sayılır; aşılmaya çalışılmaz, rapor edilir.
Bahis oranlarından olasılık üretmez. Futbol analiz becerilerinden bağımsızdır.

Kullanım:
  python3 nesine_bulletin.py cek  [--akis hepsi|mac-oncesi|canli] [--tarih GG.AA.YYYY | --bugun |
                                   --baslangic "YYYY-AA-GG SS:DD" --bitis "..."] [--cikti KLASOR]
  python3 nesine_bulletin.py isle [--mac-oncesi-ham DOSYA] [--canli-ham DOSYA] [filtreler] [--cikti KLASOR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SURUM = "0.2.0"
TR = ZoneInfo("Europe/Istanbul")
BURASI = Path(__file__).resolve().parent
SOZLUK_DOSYASI = BURASI.parent / "data" / "market_sozlugu_v3.json"

AKISLAR = {
    "mac_oncesi": {"url": "https://cdnbulten.nesine.com/api/bulten/getprebultenfull", "yol": ("sg", "EA")},
    "canli": {"url": "https://bulten.nesine.com/api/bulten/getlivebultenv3?eventVersion=0&oddVersion=0", "yol": ("sg", "EA")},
}
IZINLI_HOSTLAR = ("cdnbulten.nesine.com", "bulten.nesine.com")
USER_AGENT = f"FootballIntelligence/{SURUM} (kisisel arastirma; istek uzerine tek cekim)"
ENGEL_DURUMLARI = {401, 403, 407, 429, 451}

FUTBOL = 1                                   # TYPE (maç öncesi) / GT (canlı) futbol kodu; gerçek veriyle doğrulanacak
MARKET_BLOKLARI = ("MA", "MSA")              # MA: maç marketleri, MSA: uzun vadeli (şampiyon vb.)
OZEL_KELIMELER = ("Oyuncu", "Kaleci", "Karşılaşma", "Takım ")   # not defteriyle aynı: seçenekleri maçtan maça değişen marketler
ZORUNLU_ETKINLIK_ALANLARI = ("C",)
SUTUN_SINIRI = 16_000                        # Excel 16.384 sütun; pay bırakıldı
SATIR_SINIRI = 1_000_000                     # Excel 1.048.576 satır
HUCRE_SINIRI = 32_000                        # Excel 32.767 karakter
BASLIK_SINIRI = 250                          # geniş tablo sütun başlığı

# Canlı skor/dakika/durum: gerçek veriyle doğrulanmış alan eşlemesi. İlk gerçek çekimden sonra doldurulacak.
# Boşken resmî sütunlar boş kalır; adaylar ayrıca "aday" sütunlarında ve bütün alanlar canli_durum sayfasında saklanır.
CANLI_ALAN_HARITASI: dict[str, str] = {}
CANLI_ADAY_ALANLAR = {
    "skor_ev": ("HS", "HSC", "SCH", "HG", "HomeScore"),
    "skor_dep": ("AS", "ASC", "SCA", "AG", "AwayScore"),
    "skor_metin": ("SC", "SCR", "SCORE", "Score"),
    "dakika": ("MIN", "MT", "DK", "CM", "EM", "ETM", "Minute"),
    "durum": ("ST", "STS", "STATUS", "ES", "PS", "PER", "Period", "Status"),
}


# ----------------------------------------------------------------------------------------------
# Sözlük
# ----------------------------------------------------------------------------------------------
class Sozluk:
    """104 marketlik hazır sözlük (salt okunur; bu modül sözlüğe hiçbir zaman yazmaz)."""

    def __init__(self, yol: Path = SOZLUK_DOSYASI):
        self.yol = Path(yol)
        metin = self.yol.read_text(encoding="utf-8")
        self.sha256 = hashlib.sha256(metin.encode("utf-8")).hexdigest()
        self.veri: dict = json.loads(metin)
        self.kod_sayisi = len([k for k in self.veri if not k.endswith("|*")])

    def bul(self, mtid, sov):
        """(kayıt, tam_eşleşme). Anahtar biçimi not defteriyle aynı: 'MTID|SOV' (SOV float yazımı), yoksa 'MTID|*'."""
        if mtid is None:
            return None, False
        f = _sayi(sov)
        if f is not None:
            k1 = f"{mtid}|{f}"
            if k1 in self.veri:
                return self.veri[k1], True
        return self.veri.get(f"{mtid}|*"), False


def _sayi(x):
    if isinstance(x, bool) or x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _g(v) -> str:
    return f"{v:g}"


def sozluk_market_adi(kayit: dict, tam: bool, sov) -> str:
    """Not defterindeki isim_ekle() kuralları: handikap işareti, {cizgi} şablonu, bilinmeyen çizgi eki."""
    f = _sayi(sov)
    sov_ok = f is not None and f != 0
    ad = kayit["ad"]
    hnd = re.search(r"\((\d+(?:,\d+)?):(\d+(?:,\d+)?)\)", ad)
    if hnd and sov_ok:
        x = _g(abs(f)).replace(".", ",")
        yeni = f"({x}:0)" if f > 0 else f"(0:{x})"       # pozitif çizgi ev sahibine, negatif deplasmana
        ad = ad[:hnd.start()] + yeni + ad[hnd.end():]
    elif "{cizgi}" in ad:
        ad = ad.replace("{cizgi}", _g(f).replace(".", ",") if sov_ok else "?")
    elif not tam and sov_ok and not hnd:
        ad = f"{ad} [{_g(f)}]"
    return ad


def maca_ozel_mi(ad: str | None, kayit: dict | None) -> bool:
    return bool((kayit and kayit.get("maca_ozel")) or (ad and ad.startswith(OZEL_KELIMELER)))


# ----------------------------------------------------------------------------------------------
# Etkinlik okuma
# ----------------------------------------------------------------------------------------------
def _etkinlik_listesi_mi(x) -> bool:
    ornek = x[:5]
    return bool(ornek) and all(isinstance(i, dict) for i in ornek) and any(
        any(k in i for k in MARKET_BLOKLARI) for i in ornek)


def mac_listesini_bul(veri, yol=("sg", "EA")):
    """(liste, bulunan_yol, yedek_arama_kullanildi). Beklenen yol yoksa en büyük etkinlik listesini arar
    ve bunu açıkça bildirir (not defterinde sessizdi)."""
    x, tamam = veri, True
    for k in yol:
        if isinstance(x, dict) and k in x:
            x = x[k]
        else:
            tamam = False
            break
    if tamam and isinstance(x, list) and (not x or all(isinstance(i, dict) for i in x)):
        return x, ".".join(yol), False
    en_iyi, en_iyi_yol = None, None

    def gez(o, p, d):
        nonlocal en_iyi, en_iyi_yol
        if d > 6:
            return
        if isinstance(o, list):
            if _etkinlik_listesi_mi(o) and (en_iyi is None or len(o) > len(en_iyi)):
                en_iyi, en_iyi_yol = o, p
            for i, v in enumerate(o[:50]):
                gez(v, f"{p}[{i}]", d + 1)
        elif isinstance(o, dict):
            for k, v in o.items():
                gez(v, f"{p}.{k}" if p else k, d + 1)
    gez(veri, "", 0)
    return (en_iyi or []), en_iyi_yol, True


def spor_grubu(e: dict) -> str:
    """Normalleştirilmiş etkinliğin grubu. Negatif TYPE uzun vadeli pazardır (gözlem: -1 futbol ligleri, -2 basketbol,
    -23 voleybol); yalnızca -1 futbol uzun vadeli sayılır, diğer negatifler başka sporların uzun vadelisidir."""
    if e.get("futbol"):
        return "futbol"
    t = e.get("type_ham")
    if isinstance(t, (int, float)) and not isinstance(t, bool) and t < 0:
        return "futbol_uzun_vadeli" if t == -FUTBOL else f"uzun_vadeli_{int(-t)}"
    return "spor_belirsiz" if e.get("spor_kodu") is None else f"spor_{e['spor_kodu']}"


def spor_kodu(ev: dict):
    """Maç öncesinde TYPE, canlıda GT. -1/0/boş = belirsiz (ör. uzun vadeli 'Şampiyon Kim Olur?')."""
    for k in ("TYPE", "GT"):
        v = ev.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            return int(v)
    return None


def _epoch_tr(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 1e9:
        return datetime.fromtimestamp(v / 1000 if v > 1e12 else v, tz=TR)
    return None


def _dt_tr(d, t):
    try:
        if isinstance(d, str) and re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", d):
            return datetime.strptime(f"{d} {t or '00:00'}", "%d.%m.%Y %H:%M").replace(tzinfo=TR)
        if isinstance(d, str) and re.match(r"\d{4}-\d{2}-\d{2}", d):
            dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TR)
            if t and dt.hour == 0 and dt.minute == 0 and re.fullmatch(r"\d{1,2}:\d{2}", str(t)):
                h, mi = map(int, str(t).split(":"))
                dt = dt.replace(hour=h, minute=mi)
            return dt.astimezone(TR)
    except (ValueError, TypeError):
        return None
    return None


def mac_zamani(ev: dict):
    """(TR saatli başlama zamanı | None, kaynak, çelişki). ESD (epoch ms) önce; D/T yedek ve çapraz kontrol."""
    esd = _epoch_tr(ev.get("ESD"))
    dt = _dt_tr(ev.get("D"), ev.get("T"))
    celiski = bool(esd and dt and abs((esd - dt).total_seconds()) > 60)
    if esd:
        return esd, "ESD", celiski
    if dt:
        return dt, "D/T", False
    for k in ("SD", "DT", "ED"):
        z = _epoch_tr(ev.get(k))
        if z:
            return z, k, False
    return None, None, False


def alanlari_duzlestir(o: dict, on: str = "", d: int = 0, sonuc: dict | None = None) -> dict:
    """Market blokları dışındaki bütün alanları 'a.b[0].c' biçiminde düzleştirir (canlı skor/dakika kaybolmasın)."""
    sonuc = {} if sonuc is None else sonuc
    for k, v in o.items():
        if not on and k in MARKET_BLOKLARI:
            continue
        p = f"{on}.{k}" if on else str(k)
        if isinstance(v, dict) and d < 4:
            alanlari_duzlestir(v, p, d + 1, sonuc)
        elif isinstance(v, list):
            if all(not isinstance(x, (dict, list)) for x in v):
                sonuc[p] = json.dumps(v, ensure_ascii=False)
            elif d < 4:
                for i, x in enumerate(v):
                    if isinstance(x, dict):
                        alanlari_duzlestir(x, f"{p}[{i}]", d + 1, sonuc)
                    else:
                        sonuc[f"{p}[{i}]"] = json.dumps(x, ensure_ascii=False) if isinstance(x, list) else x
            else:
                sonuc[p] = json.dumps(v, ensure_ascii=False)
        else:
            sonuc[p] = v
    return sonuc


def canli_durum(ev: dict) -> dict:
    alanlar = alanlari_duzlestir(ev)
    resmi = {ad: alanlar.get(yol) for ad, yol in CANLI_ALAN_HARITASI.items()}
    adaylar = {}
    for ad, anahtarlar in CANLI_ADAY_ALANLAR.items():
        for yol, v in alanlar.items():
            if yol.split(".")[-1].split("[")[0] in anahtarlar and v not in (None, ""):
                adaylar[ad] = {"alan": yol, "deger": v}
                break
    return {"resmi": resmi, "adaylar": adaylar, "alanlar": alanlar,
            "harita_dogrulandi": bool(CANLI_ALAN_HARITASI)}


def oran_oku(o):
    """(oran | None, durum). Bültende kapalı seçenek 1.0 gelir -> 'kapali' (not defteriyle aynı)."""
    v = _sayi(o)
    if v is None:
        return None, ("yok" if o is None else "gecersiz")
    return (v, "acik") if v > 1.0 else (None, "kapali")


def lig_haritasi(veri) -> dict:
    """sg.LA: [{LID, N, CC, SO}] -> {LID: (ad, ülke/kategori)}. Etkinliklerde LN yok; lig adı buradan gelir."""
    la = (veri.get("sg") or {}).get("LA") if isinstance(veri, dict) else None
    return {x.get("LID"): (x.get("N"), x.get("CC")) for x in (la or []) if isinstance(x, dict) and x.get("LID") is not None}


def etkinlik_normallestir(ev: dict, akis: str, sozluk: Sozluk, cekim_tr: datetime | None, ligler: dict | None = None) -> dict:
    spor = spor_kodu(ev)
    futbol = spor == FUTBOL
    bas, zkaynak, celiski = mac_zamani(ev)
    ev_adi, dep_adi = str(ev.get("HN") or ""), str(ev.get("AN") or "")
    lig_ad, lig_ulke = (ligler or {}).get(ev.get("LC"), (None, None))
    temel = {
        "akis": akis, "kod": ev.get("C"), "nid": ev.get("NID"), "ev_kodu": ev.get("EV"),
        "spor_kodu": spor, "lig": ev.get("LN") or lig_ad, "lig_ulke": lig_ulke, "lig_kodu": ev.get("LC"),
        "lig_kaynagi": "LN" if ev.get("LN") else ("LA" if lig_ad else None),
        "ev": ev.get("HN"), "deplasman": ev.get("AN"),
        "karsilasma": f"{ev_adi} - {dep_adi}" if (ev_adi or dep_adi) else (ev.get("ENN") or ev.get("ENO")),
        "etkinlik_adi": ev.get("ENN") or ev.get("ENO"),
        "baslama_tr": bas.isoformat() if bas else None, "baslama_kaynagi": zkaynak,
        "tarih_saat_celiskisi": celiski, "tarih": ev.get("D"), "saat": ev.get("T"),
        "mac_mbs": ev.get("EMBS") if ev.get("EMBS") is not None else ev.get("MBS"),     # Nesine maç MBS'i EMBS'te
        "mac_mbs_kaynagi": "EMBS" if ev.get("EMBS") is not None else ("MBS" if ev.get("MBS") is not None else None),
        "type_ham": ev.get("TYPE"),
        "baslama_saati_gecmis": bool(bas and cekim_tr and akis == "mac_oncesi" and bas < cekim_tr),
        "baslamamis_gorunuyor": bool(bas and cekim_tr and akis == "canli" and bas > cekim_tr + timedelta(minutes=10)),
    }
    marketler, uyumsuz_adlar = [], []
    for blok in MARKET_BLOKLARI:
        for sira, mk in enumerate(ev.get(blok) or []):
            if not isinstance(mk, dict):
                continue
            mtid, sov = mk.get("MTID"), mk.get("SOV")
            mn = mk.get("MN") if isinstance(mk.get("MN"), str) and mk.get("MN").strip() else None
            kayit, tam = sozluk.bul(mtid, sov) if futbol else (None, False)
            sozluk_adi = sozluk_market_adi(kayit, tam, sov) if kayit else None
            if mn:
                ad, ad_kaynak = mn.strip(), "json"
                if sozluk_adi and _norm(sozluk_adi) != _norm(ad):
                    uyumsuz_adlar.append({"market_tip_id": mtid, "ozel_deger": sov, "json": ad, "sozluk": sozluk_adi})
            elif sozluk_adi:
                ad, ad_kaynak = sozluk_adi, "sozluk"
            else:
                f = _sayi(sov)
                kimlik = mtid if mtid is not None else (mk.get("NO") if mk.get("NO") is not None else mk.get("ID"))
                ad = f"market {kimlik}" + (f" ({_g(f)})" if f not in (None, 0) else "")
                ad_kaynak = "yok"
            ozel = maca_ozel_mi(ad, kayit)
            ms = mk.get("MS")
            secenekler = []
            for s in mk.get("OCA") or []:
                if not isinstance(s, dict):
                    continue
                oran, durum = oran_oku(s.get("O"))
                etiket, e_kaynak = secenek_etiketi(s, kayit, ozel, ev_adi, dep_adi)
                secenekler.append({"secenek_no": s.get("N"), "secenek_adi": etiket, "secenek_adi_kaynagi": e_kaynak,
                                   "oran": oran, "oran_ham": s.get("O"), "oran_durumu": durum,
                                   "oynanabilirlik": oynanabilirlik(durum, ms),
                                   "secenek_alternatif_adi": None, "secenek_kodu_no": s.get("NO")})
            marketler.append({
                "market_blok": blok, "market_sira": sira, "market_tip_id": mtid, "market_json_id": mk.get("ID"),
                "market_no": mk.get("NO"), "market_mt": mk.get("MT"), "ozel_deger": sov,
                "ozel_deger2": mk.get("SOV2"), "ozel_deger3": mk.get("SOV3"), "market_durumu": ms,
                "market_mbs": mk.get("MBS"),
                "market_adi": ad, "market_adi_kaynagi": ad_kaynak, "sozluk_adi": sozluk_adi,
                "maca_ozel": ozel, "secenekler": secenekler,
            })
    sonuc = {**temel, "futbol": futbol, "marketler": marketler, "ad_uyumsuzluklari": uyumsuz_adlar,
             "eksik_alanlar": [k for k in ZORUNLU_ETKINLIK_ALANLARI if ev.get(k) is None]
             + ([] if (ev.get("HN") or ev.get("ENN") or ev.get("ENO")) else ["HN/ENN"])
             + ([] if bas else ["baslama_zamani"])
             + ([] if any(isinstance(ev.get(b), list) for b in MARKET_BLOKLARI) else ["MA/MSA"])}
    if akis == "canli":
        sonuc["canli"] = canli_durum(ev)
    return sonuc


def oynanabilirlik(oran_durumu: str, ms) -> str:
    """Oranın değeri (oran_durumu) ile market durumundan (MS) ayrı bir sonuç. MS'nin anlamı doğrulanana kadar
    yalnızca MS == 1 ve oran > 1 'oynanabilir' sayılır; MS eksik ya da 1 değilse 'durumu_dogrulanmamis'.
    Ham oran hiçbir durumda silinmez."""
    if oran_durumu != "acik":
        return oran_durumu
    return "oynanabilir" if ms == 1 and not isinstance(ms, bool) else "durumu_dogrulanmamis"


def secenek_etiketi(s: dict, kayit: dict | None, ozel: bool, ev: str, dep: str):
    """Önce JSON'daki seçenek adı (ON). Maça özel marketlerde sözlük ASLA kullanılmaz."""
    on = s.get("ON")
    if isinstance(on, str) and on.strip():
        return on.strip(), "json"
    n = s.get("N")
    if ozel:
        return f"seçenek {n} (maça özel, etiket yok)", "yok"
    if kayit:
        e = (kayit.get("secenekler") or {}).get(str(n))
        if e:
            return e.replace("{ev}", ev).replace("{dep}", dep), "sozluk"
    return f"seçenek {n}", "yok"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().casefold()


# ----------------------------------------------------------------------------------------------
# Satırlar, filtre, doğrulama
# ----------------------------------------------------------------------------------------------
TEMEL_SUTUNLAR = ["akis", "kod", "nid", "spor_kodu", "lig", "lig_ulke", "lig_kodu", "karsilasma", "ev", "deplasman", "etkinlik_adi",
                  "baslama_tr", "tarih", "saat", "mac_mbs", "diger_akista_da_var", "baslama_saati_gecmis",
                  "baslamamis_gorunuyor", "tarih_saat_celiskisi", "zaman_okunamadi", "canli_kodu", "ewma_eslesme",
                  "isim_celiskisi", "dogrulanmamis_eslesme"]
MARKET_SUTUNLAR = ["market_blok", "market_sira", "market_tip_id", "market_json_id", "market_no", "market_mt",
                   "ozel_deger", "ozel_deger2", "ozel_deger3", "market_durumu", "market_mbs", "market_adi",
                   "market_adi_kaynagi", "sozluk_adi", "maca_ozel"]
SECENEK_SUTUNLAR = ["secenek_no", "secenek_adi", "secenek_adi_kaynagi", "secenek_alternatif_adi", "oran", "oran_ham",
                    "oran_durumu", "oynanabilirlik"]


def satirlar(etkinlikler: list[dict]) -> list[dict]:
    """Her satır = bir maçın bir marketindeki bir seçenek. Seçeneksiz market de bir satır olarak kalır."""
    out = []
    for e in etkinlikler:
        t = {k: e.get(k) for k in TEMEL_SUTUNLAR}
        for m in e["marketler"]:
            mb = {k: m.get(k) for k in MARKET_SUTUNLAR}
            if not m["secenekler"]:
                out.append({**t, **mb, "secenek_no": None, "secenek_adi": "(seçenek yok)", "secenek_adi_kaynagi": "yok",
                            "secenek_alternatif_adi": None, "oran": None, "oran_ham": None,
                            "oran_durumu": "secenek_yok", "oynanabilirlik": "secenek_yok"})
            for s in m["secenekler"]:
                out.append({**t, **mb, **{k: s.get(k) for k in SECENEK_SUTUNLAR}})
    return out


def beklenen_satir_sayisi(etkinlikler: list[dict]) -> int:
    return sum(max(1, len(m["secenekler"])) for e in etkinlikler for m in e["marketler"])


def zaman_penceresi(simdi: datetime | None = None, bitis_saati: int = 3):
    """Not defteriyle aynı: bugün 00:00 -> ertesi gün 03:00 (TR). 00:00-03:00 arası çalışırsa dünü baz alır."""
    simdi = simdi or datetime.now(TR)
    gun = simdi.date() if simdi.hour >= bitis_saati else (simdi - timedelta(days=1)).date()
    bas = datetime(gun.year, gun.month, gun.day, tzinfo=TR)
    return bas, bas + timedelta(days=1, hours=bitis_saati)


def gun_penceresi(gun: date, bitis_saati: int = 3):
    bas = datetime(gun.year, gun.month, gun.day, tzinfo=TR)
    return bas, bas + timedelta(days=1, hours=bitis_saati)


def tr_zaman(metin: str) -> datetime:
    for bicim in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(metin.strip(), bicim).replace(tzinfo=TR)
        except ValueError:
            continue
    raise ValueError(f"Tarih anlaşılamadı: {metin!r} (ör. '2026-11-24 18:00' ya da '24.11.2026')")


def pencereye_gore_filtrele(etkinlikler, pencere):
    """(seçilen, pencere_dışı). Zamanı okunamayan maç DIŞARIDA BIRAKILMAZ, 'zaman_okunamadi' ile işaretlenir."""
    if pencere is None:
        return etkinlikler, []
    bas, bit = pencere
    secilen, disari = [], []
    for e in etkinlikler:
        z = datetime.fromisoformat(e["baslama_tr"]) if e.get("baslama_tr") else None
        if z is None:
            e["zaman_okunamadi"] = True
            secilen.append(e)
        elif bas <= z < bit:
            secilen.append(e)
        else:
            disari.append(e)
    return secilen, disari


class Rapor:
    def __init__(self):
        self.kayitlar: list[dict] = []

    def ekle(self, seviye: str, akis: str, kod: str, mesaj: str, sayi=None, ornek=None):
        self.kayitlar.append({"seviye": seviye, "akis": akis, "kod": kod, "mesaj": mesaj, "sayi": sayi,
                              "ornek": json.dumps(ornek, ensure_ascii=False, default=str)[:2000] if ornek is not None else None})

    def durum(self) -> str:
        sv = {k["seviye"] for k in self.kayitlar}
        return "BASARISIZ" if "KRITIK" in sv else ("UYARILI" if "UYARI" in sv else "BASARILI")


def akisi_dogrula(rapor: Rapor, akis: str, meta: dict, ham_etkinlik: list, yol: str | None, yedek: bool,
                  etkinlikler: list[dict], futbol_satir_sayisi: int):
    if yedek and ham_etkinlik:
        rapor.ekle("UYARI", akis, "YAPI_DEGISTI", f"Beklenen 'sg.EA' yolu yok; etkinlikler '{yol}' yolundan alındı.")
    if not ham_etkinlik:
        seviye = "KRITIK" if akis == "mac_oncesi" else "UYARI"
        rapor.ekle(seviye, akis, "ETKINLIK_YOK", "Yanıtta etkinlik listesi bulunamadı ya da boş."
                   + (" (Canlı maç olmayabilir.)" if akis == "canli" else ""))
    kodlar = [e.get("C") for e in ham_etkinlik if isinstance(e, dict) and e.get("C") is not None]
    tekrar = len(kodlar) - len(set(kodlar))
    if tekrar:
        rapor.ekle("UYARI", akis, "TEKRAR_KOD", "Aynı etkinlik kodu birden çok kez geçiyor (hepsi korundu).", tekrar)
    eksik: dict[str, int] = {}
    for e in etkinlikler:
        for k in e["eksik_alanlar"]:
            eksik[k] = eksik.get(k, 0) + 1
    for k, n in eksik.items():
        rapor.ekle("UYARI", akis, "EKSIK_ALAN", f"'{k}' alanı eksik etkinlik sayısı", n)
    secenek_yok = sum(1 for e in etkinlikler for m in e["marketler"] if not m["secenekler"])
    if secenek_yok:
        rapor.ekle("UYARI", akis, "SECENEKSIZ_MARKET", "Seçeneği (OCA) olmayan market; satır olarak korundu.", secenek_yok)
    durumlar: dict[str, int] = {}
    for e in etkinlikler:
        for m in e["marketler"]:
            for s in m["secenekler"]:
                durumlar[s["oran_durumu"]] = durumlar.get(s["oran_durumu"], 0) + 1
    if durumlar.get("gecersiz"):
        rapor.ekle("UYARI", akis, "GECERSIZ_ORAN", "Sayıya çevrilemeyen oran (ham değer saklandı).", durumlar["gecersiz"])
    asiri = [s["oran"] for e in etkinlikler if e["futbol"] for m in e["marketler"] for s in m["secenekler"]
             if s["oran"] and s["oran"] > 1000]
    if asiri:
        rapor.ekle("UYARI", akis, "ASIRI_ORAN", "Futbol maçlarında 1000'den büyük oran.", len(asiri), asiri[:5])
    rapor.ekle("BILGI", akis, "ORAN_DURUMLARI", "Seçenek oran durumları", sum(durumlar.values()), durumlar)
    futbol = [e for e in etkinlikler if e["futbol"]]
    ms_say: dict = {}
    oyn: dict = {}
    for e in futbol:
        for m in e["marketler"]:
            ms_say[str(m["market_durumu"])] = ms_say.get(str(m["market_durumu"]), 0) + 1
            for s in m["secenekler"]:
                oyn[s["oynanabilirlik"]] = oyn.get(s["oynanabilirlik"], 0) + 1
    rapor.ekle("BILGI", akis, "MARKET_DURUMU", "Futbol marketlerinin MS dağılımı (anlamı doğrulanmadı; yalnızca MS=1 "
               "oynanabilir sayılır).", sum(ms_say.values()), ms_say)
    rapor.ekle("BILGI", akis, "OYNANABILIRLIK", "Futbol seçeneklerinin oynanabilirlik dağılımı.", sum(oyn.values()), oyn)
    if oyn.get("durumu_dogrulanmamis"):
        rapor.ekle("UYARI", akis, "DURUMU_DOGRULANMAMIS_ORAN", "Oranı olan ama market durumu MS≠1 ya da eksik olan seçenek; "
                   "oynanabilir gösterilmedi, ham oran korundu.", oyn["durumu_dogrulanmamis"])
    anahtar_say: dict = {}
    for e in futbol:
        for m in e["marketler"]:
            k1 = (e["kod"], m["market_tip_id"], m["ozel_deger"])
            anahtar_say.setdefault(k1, set()).add((m["ozel_deger2"], m["ozel_deger3"], m["market_json_id"]))
    tekrar_k = [k for k, v in anahtar_say.items() if len(v) > 1]
    sov23 = sum(1 for k in tekrar_k if len({x[:2] for x in anahtar_say[k]}) == len(anahtar_say[k]))
    if tekrar_k:
        rapor.ekle("BILGI", akis, "MARKET_ANAHTARI", "Aynı (maç, MTID, SOV) birden çok markette; SOV2/SOV3 bunların bir "
                   "kısmını ayırıyor, benzersiz anahtar market_json_id.", len(tekrar_k), {"sov2_sov3_ile_ayrisan": sov23})
    ad_say = {"json": 0, "sozluk": 0, "yok": 0}
    for e in futbol:
        for m in e["marketler"]:
            ad_say[m["market_adi_kaynagi"]] += max(1, len(m["secenekler"]))
    toplam = sum(ad_say.values())
    if toplam:
        oran = (ad_say["json"] + ad_say["sozluk"]) / toplam
        rapor.ekle("BILGI" if oran >= 0.9 else "UYARI", akis, "ISIMLENDIRME",
                   f"Futbol seçeneklerinin %{oran * 100:.1f}'i isimli market altında (kaynaklar: {ad_say}).", toplam, ad_say)
    bilinmeyen: dict = {}
    for e in futbol:
        for m in e["marketler"]:
            if m["market_adi_kaynagi"] == "yok":
                k = f"{m['market_tip_id']}|{m['ozel_deger']}|NO={m['market_no']}"
                bilinmeyen[k] = bilinmeyen.get(k, 0) + 1
    if bilinmeyen:
        rapor.ekle("BILGI", akis, "BILINMEYEN_MARKET", "İsimlendirilemeyen futbol market kodları (sayı = market adedi).",
                   len(bilinmeyen), dict(sorted(bilinmeyen.items(), key=lambda x: -x[1])[:40]))
    uyumsuz = [u for e in etkinlikler for u in e["ad_uyumsuzluklari"]]
    if uyumsuz:
        rapor.ekle("UYARI", akis, "SOZLUK_JSON_UYUMSUZ", "JSON'daki market adı sözlükle uyuşmuyor; JSON adı kullanıldı.",
                   len(uyumsuz), uyumsuz[:10])
    spor: dict = {}
    for e in etkinlikler:
        spor[str(e["spor_kodu"])] = spor.get(str(e["spor_kodu"]), 0) + 1
    rapor.ekle("BILGI", akis, "SPOR_DAGILIMI", "Etkinliklerin spor kodu dağılımı (futbol = 1; diğerleri yalnızca ham JSON'da).",
               len(etkinlikler), spor)
    celiski = sum(1 for e in etkinlikler if e["tarih_saat_celiskisi"])
    if celiski:
        rapor.ekle("UYARI", akis, "ZAMAN_CELISKISI", "ESD ile D/T bir dakikadan fazla farklı.", celiski)
    if akis == "mac_oncesi":
        n = sum(1 for e in futbol if e["baslama_saati_gecmis"])
        if n:
            rapor.ekle("BILGI", akis, "BASLAMIS_OLABILIR", "Maç öncesi bültende başlama saati geçmiş futbol maçı.", n)
    else:
        n = sum(1 for e in futbol if e["baslamamis_gorunuyor"])
        if n:
            rapor.ekle("UYARI", akis, "BASLAMAMIS_CANLI", "Canlı akışta başlama saati 10 dk'dan ileride görünen maç.", n)
        adaylar: dict = {}
        for e in futbol:
            for ad, a in e["canli"]["adaylar"].items():
                adaylar.setdefault(ad, {}).setdefault(a["alan"], a["deger"])
        rapor.ekle("BILGI" if CANLI_ALAN_HARITASI else "UYARI", akis, "CANLI_ALANLAR",
                   "Skor/dakika/durum alan eşlemesi " + ("doğrulanmış." if CANLI_ALAN_HARITASI else
                   "HENÜZ DOĞRULANMADI: resmî sütunlar boş; aday alanlar ve bütün alanlar 'canli_durum' sayfasında."),
                   len(futbol), adaylar)
    beklenen = beklenen_satir_sayisi(futbol)
    if beklenen != futbol_satir_sayisi:
        rapor.ekle("KRITIK", akis, "SATIR_KAYBI", f"Beklenen {beklenen} seçenek satırı, üretilen {futbol_satir_sayisi}.")


# ----------------------------------------------------------------------------------------------
# Excel
# ----------------------------------------------------------------------------------------------
_KONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _hucre(v, sayac: dict):
    if isinstance(v, str):
        if _KONTROL.search(v):
            v = _KONTROL.sub("", v)
            sayac["kontrol_karakteri"] = sayac.get("kontrol_karakteri", 0) + 1
        if len(v) > HUCRE_SINIRI:
            v = v[:HUCRE_SINIRI] + " …[KESİLDİ, tam değer JSON'da]"
            sayac["kesilen_hucre"] = sayac.get("kesilen_hucre", 0) + 1
    elif isinstance(v, (dict, list)):
        return _hucre(json.dumps(v, ensure_ascii=False), sayac)
    return v


def genis_tablo(satir_listesi: list[dict]):
    """Her maç tek satır, her market/seçenek bir sütun. Aynı maçta aynı sütun adına düşen seçenekler
    birleştirilmez: çakışan adlara kod eki eklenir. Dönüş: (sütunlar, satırlar, hücre_sayısı)."""
    def etkinlik_anahtari(r):
        return (r["kod"], r["nid"], r["karsilasma"], r["baslama_tr"])

    def ad(r, seviye):
        a = f"{r['market_adi']} | {r['secenek_adi']}"
        if seviye >= 1:
            ek = "" if r.get("ozel_deger2") is None and r.get("ozel_deger3") is None else f"|{r.get('ozel_deger2')}-{r.get('ozel_deger3')}"
            a += f" [{r['market_tip_id']}|{r['ozel_deger']}{ek}|N{r['secenek_no']}]"
        if seviye >= 2:
            a += f" [{r['market_blok']}{r['market_sira']}]"
        if len(a) > BASLIK_SINIRI:                       # Excel başlığı sessizce kesilmesin: kısalt + benzersiz özet
            a = a[:BASLIK_SINIRI - 12] + "…#" + hashlib.sha1(a.encode("utf-8")).hexdigest()[:10]
        return a

    seviye = {}
    for s in range(3):
        sayim: dict = {}
        for i, r in enumerate(satir_listesi):
            sayim.setdefault((etkinlik_anahtari(r), ad(r, seviye.get(i, 0))), []).append(i)
        cakisan = [ix for ixs in sayim.values() if len(ixs) > 1 for ix in ixs]
        if not cakisan:
            break
        for ix in cakisan:
            seviye[ix] = seviye.get(ix, 0) + 1
    sutunlar, tablo, hucre = [], {}, 0
    sira_ek: dict = {}
    for i, r in enumerate(satir_listesi):
        c = ad(r, seviye.get(i, 0))
        k = etkinlik_anahtari(r)
        satir = tablo.setdefault(k, {"kod": r["kod"], "karsilasma": r["karsilasma"], "lig": r["lig"],
                                     "baslama_tr": r["baslama_tr"], "ev": r["ev"], "deplasman": r["deplasman"]})
        if c in satir:                                   # 3 seviyeden sonra hâlâ çakışıyorsa sıra numarası
            sira_ek[c] = sira_ek.get(c, 1) + 1
            c = f"{c} #{sira_ek[c]}"
        if c not in sutunlar:
            sutunlar.append(c)
        if r["oran"] is not None and r.get("oynanabilirlik") == "oynanabilir":
            satir[c] = r["oran"]
        elif r["oran"] is not None:                       # oran var, market durumu doğrulanmamış: sayı gibi gösterme
            satir[c] = f"? {_g(r['oran'])}"
        else:
            satir[c] = {"kapali": "-", "secenek_yok": "seçenek yok"}.get(
                r["oran_durumu"], f"({r['oran_durumu']}: {r['oran_ham']})")
        hucre += 1
    return sutunlar, list(tablo.values()), hucre


def excel_yaz(dosya: Path, akis: str, etkinlikler: list[dict], diger: list[dict], filtre_disi: list[dict],
              rapor: Rapor, marketsiz: list[dict], kaynak: dict, ekstra_sayfalar: dict | None = None) -> dict:
    import pandas as pd
    from openpyxl import load_workbook

    sayac: dict = {}
    futbol = [e for e in etkinlikler if e["futbol"]]
    belirsiz = [e for e in diger if spor_grubu(e) == "spor_belirsiz"]
    futbol_uzun = [e for e in diger if spor_grubu(e) == "futbol_uzun_vadeli"]
    uzun = satirlar(futbol)
    ozet = [{**{k: e.get(k) for k in TEMEL_SUTUNLAR},
             "market_sayisi": len(e["marketler"]),
             "secenek_sayisi": sum(len(m["secenekler"]) for m in e["marketler"]),
             "acik_oran": sum(1 for m in e["marketler"] for s in m["secenekler"] if s["oran"] is not None),
             "oynanabilir_oran": sum(1 for m in e["marketler"] for s in m["secenekler"] if s["oynanabilirlik"] == "oynanabilir"),
             "durumu_dogrulanmamis_oran": sum(1 for m in e["marketler"] for s in m["secenekler"]
                                              if s["oynanabilirlik"] == "durumu_dogrulanmamis"),
             "isimsiz_market": sum(1 for m in e["marketler"] if m["market_adi_kaynagi"] == "yok")} for e in futbol]
    sayfalar: list[tuple[str, list[dict], list[str] | None]] = [("ozet", ozet, None)]
    uzun_sutunlar = TEMEL_SUTUNLAR + MARKET_SUTUNLAR + SECENEK_SUTUNLAR
    parcalar = [uzun[i:i + SATIR_SINIRI] for i in range(0, len(uzun), SATIR_SINIRI)] or [[]]
    for i, p in enumerate(parcalar):
        sayfalar.append(("tum_oranlar" if i == 0 else f"tum_oranlar_{i + 1}", p, uzun_sutunlar))
    sutunlar, genis, hucre = genis_tablo(uzun)
    if len(sutunlar) + 6 <= SUTUN_SINIRI:
        sayfalar.append(("maclar_genis", genis, ["kod", "karsilasma", "lig", "baslama_tr", "ev", "deplasman"] + sutunlar))
        if hucre != len(uzun):
            rapor.ekle("KRITIK", akis, "GENIS_TABLO_KAYIP", f"Geniş tabloda {hucre} hücre, uzun tabloda {len(uzun)} satır.")
    else:
        rapor.ekle("BILGI", akis, "GENIS_TABLO_ATLANDI",
                   f"Geniş tablo {len(sutunlar)} sütunla Excel sınırını aşıyor; 'tum_oranlar' sayfası esas alınmalı.")
    if akis == "canli":
        cd = []
        for e in futbol:
            c = e["canli"]
            cd.append({"kod": e["kod"], "nid": e["nid"], "karsilasma": e["karsilasma"], "lig": e["lig"],
                       "son_dogrulama_tr": kaynak.get("cekim_tr"), "harita_dogrulandi": c["harita_dogrulandi"],
                       **{f"{k}": v for k, v in c["resmi"].items()},
                       **{f"aday_{k}": f"{v['deger']} ({v['alan']})" for k, v in c["adaylar"].items()},
                       **{f"alan.{k}": v for k, v in c["alanlar"].items()}})
        sayfalar.append(("canli_durum", cd, None))
    if futbol_uzun:
        sayfalar.append(("futbol_uzun_vadeli", satirlar(futbol_uzun), uzun_sutunlar))
    if belirsiz:
        sayfalar.append(("spor_belirsiz", satirlar(belirsiz), uzun_sutunlar))
    for ad_, veri_ in (ekstra_sayfalar or {}).items():
        if veri_:
            sayfalar.append((ad_, veri_, None))
    if marketsiz:
        sayfalar.append(("marketsiz_maclar", [{k: e.get(k) for k in TEMEL_SUTUNLAR} for e in marketsiz], None))
    if filtre_disi:
        sayfalar.append(("filtre_disi", [{k: e.get(k) for k in ("kod", "spor_kodu", "lig", "karsilasma", "baslama_tr")}
                                         | {"market_sayisi": len(e["marketler"])} for e in filtre_disi], None))
    sayfalar.append(("kaynak", [{"alan": k, "deger": json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}
                                for k, v in kaynak.items()], None))
    dosya.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(dosya, engine="openpyxl") as w:
        for ad, veri, sut in sayfalar:
            temiz = [{k: _hucre(v, sayac) for k, v in r.items()} for r in veri]
            df = pd.DataFrame(temiz, columns=sut) if sut else pd.DataFrame(temiz)
            if df.empty and not sut:
                df = pd.DataFrame({"bilgi": ["kayıt yok"]})
            df.to_excel(w, sheet_name=ad, index=False)
        dog = [r for r in rapor.kayitlar if r["akis"] in (akis, "genel")]
        pd.DataFrame(dog or [{"seviye": "BILGI", "mesaj": "kayıt yok"}]).to_excel(w, sheet_name="dogrulama", index=False)
    for k, v in sayac.items():
        rapor.ekle("BILGI", akis, k.upper(), "Excel'e yazarken düzeltilen hücre (tam değer JSON'da).", v)
    # Yazılanı geri oku: tum_oranlar satır sayısı uzun tabloyla aynı olmalı
    wb = load_workbook(dosya, read_only=True)
    yazilan = sum(wb[s].max_row - 1 for s in wb.sheetnames if s.startswith("tum_oranlar") and wb[s].max_row > 1)
    wb.close()
    if yazilan != len(uzun):
        rapor.ekle("KRITIK", akis, "EXCEL_SATIR_KAYBI", f"Excel'e {yazilan} satır yazıldı, beklenen {len(uzun)}.")
    return {"excel": str(dosya), "futbol_etkinlik": len(futbol), "secenek_satiri": len(uzun), "excel_satiri": yazilan,
            "genis_sutun": len(sutunlar)}


# ----------------------------------------------------------------------------------------------
# Çekim
# ----------------------------------------------------------------------------------------------
def cek(url: str, zaman_asimi: float = 30.0) -> dict:
    """Tek GET. Yeniden deneme yok: engel (401/403/429/451) ya da HTML yanıtı aşılmaya çalışılmaz."""
    host = urllib.parse.urlparse(url).hostname
    if host not in IZINLI_HOSTLAR:
        raise ValueError(f"İzin verilmeyen host: {host}")
    istek = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json",
                                                 "Accept-Language": "tr-TR,tr;q=0.9"})
    baglam = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)
    simdi = datetime.now(timezone.utc)
    meta = {"url": url, "cekim_utc": simdi.isoformat(timespec="seconds"),
            "cekim_tr": simdi.astimezone(TR).isoformat(timespec="seconds"), "user_agent": USER_AGENT,
            "http_durumu": None, "icerik_turu": None, "bayt": 0, "sha256": None, "hata": None}
    t0 = time.monotonic()
    govde = b""
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi, context=baglam) as y:
            govde = y.read()
            meta["http_durumu"] = y.status
            meta["icerik_turu"] = y.headers.get("Content-Type")
    except urllib.error.HTTPError as h:
        govde = h.read() or b""
        meta["http_durumu"] = h.code
        meta["icerik_turu"] = h.headers.get("Content-Type") if h.headers else None
        meta["hata"] = f"HTTP {h.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as h:
        neden = getattr(h, "reason", h)
        meta["hata"] = f"Bağlantı hatası: {neden}"
        if "403" in str(neden) and "unnel" in str(neden):
            meta["hata"] += " (bu bulut ortamının ağ politikası hostu engelliyor; Nesine'ye ulaşılmadı)"
    meta["sure_sn"] = round(time.monotonic() - t0, 2)
    meta["bayt"] = len(govde)
    meta["sha256"] = hashlib.sha256(govde).hexdigest() if govde else None
    return {"meta": meta, "govde": govde}


def govdeyi_coz(akis: str, cekim: dict, rapor: Rapor):
    meta, govde = cekim["meta"], cekim["govde"]
    if meta.get("hata") and meta.get("http_durumu") is None:
        rapor.ekle("KRITIK", akis, "BAGLANTI", meta["hata"])
        return None
    if meta.get("http_durumu") in ENGEL_DURUMLARI:
        rapor.ekle("KRITIK", akis, "ERISIM_ENGELI",
                   f"HTTP {meta['http_durumu']}: erişim engellendi. Engel aşılmaya çalışılmadı.")
        return None
    if meta.get("http_durumu") not in (None, 200):
        rapor.ekle("KRITIK", akis, "HTTP_DURUMU", f"Beklenmeyen HTTP {meta['http_durumu']}.")
        return None
    if not govde:
        rapor.ekle("KRITIK", akis, "BOS_YANIT", "Yanıt gövdesi boş.")
        return None
    bas = govde[:200].lstrip().lower()
    if bas.startswith((b"<!doctype", b"<html")) or "html" in str(meta.get("icerik_turu") or "").lower():
        rapor.ekle("KRITIK", akis, "ERISIM_ENGELI", "JSON yerine HTML geldi (engel/doğrulama sayfası olabilir). "
                   "Engel aşılmaya çalışılmadı.", ornek=govde[:200].decode("utf-8", "replace"))
        return None
    try:
        return json.loads(govde.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as h:
        rapor.ekle("KRITIK", akis, "JSON_HATASI", f"JSON çözülemedi: {h}")
        return None


_GENEL_TOKEN = {"fc", "ac", "us", "ca", "cf", "sc", "cd", "ud", "sd", "afc", "fk", "sk", "club", "the", "de", "la",
                "las", "los", "el", "al", "y"}


def _tokenler(ad) -> set:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(ad or "")).encode("ascii", "ignore").decode().casefold()
    return {t for t in re.split(r"[^a-z0-9]+", s) if t and t not in _GENEL_TOKEN}


def takim_adi_karsilastir(a, b) -> str:
    """'ayni' | 'yazim_farki' (kısaltma/ek farkı; doğrulanmamış) | 'celiski' (ortak sözcük yok) | 'bilinmiyor'.
    Hangi adın doğru olduğuna karar VERMEZ."""
    if not a or not b:
        return "bilinmiyor"
    if _norm(a) == _norm(b):
        return "ayni"
    ta, tb = _tokenler(a), _tokenler(b)
    if not ta or not tb:
        return "bilinmiyor"
    if ta == tb:
        return "yazim_farki"
    kucuk, buyuk = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if all(any(y == x or y.startswith(x) or x.startswith(y) for y in buyuk) for x in kucuk):
        return "yazim_farki"
    return "celiski"


def mac_adi_karsilastir(a: dict, b: dict) -> dict:
    ev, dep = takim_adi_karsilastir(a.get("ev"), b.get("ev")), takim_adi_karsilastir(a.get("deplasman"), b.get("deplasman"))
    genel = "celiski" if "celiski" in (ev, dep) else ("yazim_farki" if "yazim_farki" in (ev, dep) else
                                                      ("ayni" if ev == dep == "ayni" else "bilinmiyor"))
    return {"ev": ev, "deplasman": dep, "sonuc": genel}


def _ad_saat(e: dict):
    return (_norm(e.get("ev") or ""), _norm(e.get("deplasman") or ""), e.get("baslama_tr"))


def ewma_esle(ewma: list[dict], mac_oncesi: list[dict], canli: list[dict]) -> list[dict]:
    """EWMA (marketsiz) kayıtlarını oranlı maç öncesi maçlarla eşleştirir: önce NID (= maç öncesi C ya da NID),
    yoksa birebir takım adları + başlama saati. Eşleşen kayıt yeni maç sayılmaz; maç öncesi maça 'canli_kodu'
    olarak bağlanır. NID'siz ad+saat eşleşmesi, ad çelişkisi ya da saat farkı 'belirsiz' işaretlenir."""
    kod = {e["kod"]: e for e in mac_oncesi}
    nid = {e["nid"]: e for e in mac_oncesi if e.get("nid") is not None}
    ad_saat: dict = {}
    for e in mac_oncesi:
        ad_saat.setdefault(_ad_saat(e), []).append(e)
    canli_kodlar = {e["kod"] for e in canli} | {e.get("nid") for e in canli}
    sonuc = []
    for w in ewma:
        aday, yontem, notlar = None, None, []
        if w.get("nid") in kod:
            aday, yontem = kod[w["nid"]], "NID=C"
        elif w.get("nid") in nid:
            aday, yontem = nid[w["nid"]], "NID"
        if aday is None:
            ad_aday = ad_saat.get(_ad_saat(w), [])
            if len(ad_aday) == 1:
                aday, yontem = ad_aday[0], "ad+saat"
                notlar.append("NID maç öncesi bir maça uymuyor; yalnızca birebir ad ve saatle eşleşti")
            elif len(ad_aday) > 1:
                yontem = "belirsiz_coklu"
                notlar.append(f"{len(ad_aday)} aday maç")
        karsi = mac_adi_karsilastir(w, aday) if aday else None
        if aday and aday.get("baslama_tr") != w.get("baslama_tr"):
            notlar.append(f"başlama saati farklı: {aday.get('baslama_tr')} / {w.get('baslama_tr')}")
        belirsiz = bool(aday) and (yontem == "ad+saat" or karsi["sonuc"] == "celiski"
                                   or aday.get("baslama_tr") != w.get("baslama_tr"))
        durum = ("belirsiz_coklu" if yontem == "belirsiz_coklu" else "ayri_mac" if aday is None
                 else "eslesti_belirsiz" if belirsiz else "eslesti")
        if aday:
            aday["canli_kodu"] = w["kod"]
            aday["ewma_eslesme"] = yontem
            if karsi["sonuc"] == "celiski":
                aday["isim_celiskisi"] = True
            if belirsiz:
                aday["dogrulanmamis_eslesme"] = True
        sonuc.append({"ewma_kod": w["kod"], "ewma_nid": w.get("nid"), "ewma_ev": w.get("ev"), "ewma_deplasman": w.get("deplasman"),
                      "ewma_lig": w.get("lig"), "ewma_baslama_tr": w.get("baslama_tr"), "durum": durum, "yontem": yontem,
                      "eslesen_kod": aday["kod"] if aday else None, "eslesen_ev": aday.get("ev") if aday else None,
                      "eslesen_deplasman": aday.get("deplasman") if aday else None,
                      "ad_karsilastirma_ev": karsi["ev"] if karsi else None,
                      "ad_karsilastirma_deplasman": karsi["deplasman"] if karsi else None,
                      "ad_sonucu": karsi["sonuc"] if karsi else None,
                      "canli_akista": w["kod"] in canli_kodlar, "not": "; ".join(notlar) or None})
    return sonuc


def canli_ad_kontrol(mac_oncesi: list[dict], canli: list[dict]) -> list[dict]:
    """Aynı kimliğe (C/NID) bağlı canlı ve maç öncesi kayıtların takım adlarını karşılaştırır. Karar vermez, raporlar."""
    idx: dict = {}
    for e in mac_oncesi:
        for k in (e["kod"], e.get("nid")):
            if k is not None:
                idx.setdefault(k, e)
    out = []
    for c in canli:
        p = idx.get(c.get("nid")) or idx.get(c["kod"])
        if not p:
            continue
        karsi = mac_adi_karsilastir(p, c)
        if karsi["sonuc"] in ("celiski", "yazim_farki"):
            for e in (p, c):
                if karsi["sonuc"] == "celiski":
                    e["isim_celiskisi"] = True
                    e["dogrulanmamis_eslesme"] = True
            out.append({"kaynak": "mac_oncesi ↔ canli", "kod_1": p["kod"], "ad_1": p.get("karsilasma"),
                        "kod_2": c["kod"], "ad_2": c.get("karsilasma"), "ev": karsi["ev"], "deplasman": karsi["deplasman"],
                        "sonuc": karsi["sonuc"], "baslama_1": p.get("baslama_tr"), "baslama_2": c.get("baslama_tr")})
    return out


def nsn_adlarini_uygula(veri, etkinlikler: list[dict]) -> dict:
    """nsnBultenNames: C=3 -> seçenek kısa adı (EID, MID=market ID, ON=seçenek N); C=1/4 -> ev/deplasman kısa adı.
    Yalnızca anahtarları birebir tutan kayıtlar 'secenek_alternatif_adi' olarak yazılır; eksik etiket DOLDURULMAZ."""
    nsn = ((veri.get("nsn") or {}).get("nsnBultenNames") or []) if isinstance(veri, dict) else []
    sec = {(x.get("EID"), x.get("MID"), x.get("ON")): x.get("N") for x in nsn if isinstance(x, dict) and x.get("C") == 3}
    takim = {}
    for x in nsn:
        if isinstance(x, dict) and x.get("C") in (1, 4):
            takim.setdefault(x.get("EID"), {})["ev_kisa" if x.get("C") == 1 else "dep_kisa"] = x.get("HN") or x.get("AN")
    s = {"kayit": len(nsn), "secenek_kaydi": len(sec), "uygulanan_secenek": 0, "isimsiz_secenege_katki": 0,
         "takim_kaydi": sum(len(v) for v in takim.values()), "uygulanan_takim": 0}
    for e in etkinlikler:
        if e["kod"] in takim:
            e["alternatif_adlar"] = takim[e["kod"]]
            s["uygulanan_takim"] += len(takim[e["kod"]])
        for m in e["marketler"]:
            for o in m["secenekler"]:
                n = sec.get((e["kod"], m["market_json_id"], o["secenek_no"]))
                if n:
                    o["secenek_alternatif_adi"] = n
                    s["uygulanan_secenek"] += 1
                    s["isimsiz_secenege_katki"] += o["secenek_adi_kaynagi"] == "yok"
    s["eslesmeyen_secenek_kaydi"] = s["secenek_kaydi"] - s["uygulanan_secenek"]
    return s


def _kimlikler(ev: dict) -> set:
    return {x for x in (ev.get("C"), ev.get("NID")) if x is not None}


# ----------------------------------------------------------------------------------------------
# Ana akış
# ----------------------------------------------------------------------------------------------
def isle(cekimler: dict, cikti: Path, pencere=None, sozluk: Sozluk | None = None, onceki: Path | None = None) -> dict:
    """cekimler: {'mac_oncesi': {'meta':..., 'govde': bytes} | None, 'canli': ... | None}.
    Ham gövde, çekim meta bilgisi, normalleştirilmiş JSON, Excel ve doğrulama raporu yazar."""
    sozluk = sozluk or Sozluk()
    rapor = Rapor()
    cikti.mkdir(parents=True, exist_ok=True)
    (cikti / "ham").mkdir(exist_ok=True)
    cozulmus, kaynaklar = {}, {}
    for akis in ("mac_oncesi", "canli"):
        c = cekimler.get(akis)
        if c is None:
            continue
        if c["govde"]:
            (cikti / "ham" / f"{akis}.json").write_bytes(c["govde"])      # ham yanıt, bayt bayt
        kaynaklar[akis] = {**c["meta"], "ham_dosya": f"ham/{akis}.json" if c["govde"] else None}
        cozulmus[akis] = govdeyi_coz(akis, c, rapor)
    ham_listeler, etkinlik_akis, marketsiz = {}, {}, {}
    for akis, veri in cozulmus.items():
        if veri is None:
            continue
        liste, yol, yedek = mac_listesini_bul(veri, AKISLAR[akis]["yol"])
        cekim_tr = datetime.fromisoformat(kaynaklar[akis]["cekim_tr"]) if kaynaklar[akis].get("cekim_tr") else None
        ligler = lig_haritasi(veri)
        ets = [etkinlik_normallestir(ev, akis, sozluk, cekim_tr, ligler) for ev in liste if isinstance(ev, dict)]
        ewma = (veri.get("sg") or {}).get("EWMA") if isinstance(veri, dict) else None   # marketi olmayan etkinlikler
        marketsiz[akis] = [etkinlik_normallestir(ev, akis, sozluk, cekim_tr, ligler)
                           for ev in (ewma or []) if isinstance(ev, dict)]
        ligsiz = sum(1 for e in ets if e["futbol"] and not e["lig"])
        if ligsiz:
            rapor.ekle("UYARI", akis, "LIG_ADI_YOK", "Lig adı bulunamayan futbol etkinliği (LN yok, LA'da eşleşme yok).", ligsiz)
        ns = nsn_adlarini_uygula(veri, ets + marketsiz[akis])
        if ns["kayit"]:
            rapor.ekle("BILGI", akis, "NSN_ADLAR", "nsnBultenNames: yalnızca kısa/alternatif adlar; anahtarı birebir tutanlar "
                       "'secenek_alternatif_adi' olarak yazıldı, isimsiz seçenek doldurulmadı.", ns["kayit"], ns)
        ham_listeler[akis] = (liste, yol, yedek)
        etkinlik_akis[akis] = ets
        kaynaklar[akis].update({"etkinlik_yolu": yol, "yedek_arama": yedek, "ham_etkinlik_sayisi": len(liste)})
    # Çapraz işaret (yalnızca bilgi; sınıflandırma akışa göredir)
    if "mac_oncesi" in etkinlik_akis and "canli" in etkinlik_akis:
        ids = {a: set().union(*[_kimlikler({"C": e["kod"], "NID": e["nid"]}) for e in etkinlik_akis[a]] or [set()])
               for a in ("mac_oncesi", "canli")}
        for a, b in (("mac_oncesi", "canli"), ("canli", "mac_oncesi")):
            for e in etkinlik_akis[a]:
                e["diger_akista_da_var"] = bool(_kimlikler({"C": e["kod"], "NID": e["nid"]}) & ids[b])
        n = sum(1 for e in etkinlik_akis["canli"] if e.get("diger_akista_da_var") and e["futbol"])
        if n:
            rapor.ekle("BILGI", "genel", "IKI_AKISTA", "Hem maç öncesi hem canlı akışta görünen futbol maçı "
                       "(ikisinde de korundu, işaretlendi).", n)
    on_fb = [e for e in etkinlik_akis.get("mac_oncesi", []) if e["futbol"]]
    cl_fb = [e for e in etkinlik_akis.get("canli", []) if e["futbol"]]
    ewma_kayit = []
    if marketsiz.get("mac_oncesi"):
        mf = [e for e in marketsiz["mac_oncesi"] if e["futbol"]]
        ewma_kayit = ewma_esle(mf, on_fb, cl_fb)
        ayri = {k["ewma_kod"] for k in ewma_kayit if k["durum"] in ("ayri_mac", "belirsiz_coklu")}
        marketsiz["mac_oncesi"] = [e for e in marketsiz["mac_oncesi"] if not e["futbol"] or e["kod"] in ayri]
        d = _say(k["durum"] for k in ewma_kayit)
        rapor.ekle("BILGI", "mac_oncesi", "EWMA_ESLESME", "Marketsiz (EWMA) futbol kayıtları: oranlı maça bağlananlar yeni "
                   "maç sayılmadı ('ewma_eslesmeler' sayfası).", len(ewma_kayit), {"durum": d, "yontem": _say(k["yontem"] for k in ewma_kayit)})
        bel = [k for k in ewma_kayit if k["durum"] in ("eslesti_belirsiz", "belirsiz_coklu")]
        if bel:
            rapor.ekle("UYARI", "mac_oncesi", "BELIRSIZ_ESLESME", "Kesin olmayan EWMA eşleşmesi; ilgili maç "
                       "'dogrulanmamis_eslesme' ile işaretlendi.", len(bel),
                       [{k: x[k] for k in ("ewma_kod", "eslesen_kod", "yontem", "ad_sonucu", "not")} for x in bel])
    isim_farklari = [{"kaynak": "EWMA ↔ mac_oncesi", "kod_1": k["eslesen_kod"],
                      "ad_1": f"{k['eslesen_ev']} - {k['eslesen_deplasman']}", "kod_2": k["ewma_kod"],
                      "ad_2": f"{k['ewma_ev']} - {k['ewma_deplasman']}", "ev": k["ad_karsilastirma_ev"],
                      "deplasman": k["ad_karsilastirma_deplasman"], "sonuc": k["ad_sonucu"],
                      "baslama_1": None, "baslama_2": k["ewma_baslama_tr"]}
                     for k in ewma_kayit if k["ad_sonucu"] in ("celiski", "yazim_farki")]
    isim_farklari += canli_ad_kontrol(on_fb, cl_fb)
    cel = [x for x in isim_farklari if x["sonuc"] == "celiski"]
    if cel:
        rapor.ekle("UYARI", "genel", "ISIM_CELISKISI", "Aynı maç kimliğine bağlı kayıtlarda farklı takım (ortak sözcük yok). "
                   "Hangisinin doğru olduğu seçilmedi; maç 'dogrulanmamis_eslesme' ile işaretlendi, kupona alınmamalı.",
                   len(cel), [{k: x[k] for k in ("kaynak", "kod_1", "ad_1", "kod_2", "ad_2")} for x in cel])
    yaz = [x for x in isim_farklari if x["sonuc"] == "yazim_farki"]
    if yaz:
        rapor.ekle("BILGI", "genel", "ISIM_YAZIM_FARKI", "Aynı maçta takım adı yazım/kısaltma farkı (doğrulanmamış).", len(yaz))
    gercek_on = len(on_fb) + sum(1 for k in ewma_kayit if k["durum"] == "ayri_mac")
    ortak = sum(1 for e in cl_fb if e.get("diger_akista_da_var"))
    rapor.ekle("BILGI", "genel", "GERCEK_MAC_SAYISI", "Farklı futbol maçı sayısı (EWMA tekrarları ve iki akıştaki ortaklar "
               "bir kez sayıldı).", gercek_on + len(cl_fb) - ortak,
               {"mac_oncesi_oranli": len(on_fb), "mac_oncesi_yalnizca_marketsiz": gercek_on - len(on_fb),
                "mac_oncesi_toplam": gercek_on, "canli": len(cl_fb), "iki_akista_ortak": ortak,
                "belirsiz_ewma": sum(1 for k in ewma_kayit if k["durum"] == "belirsiz_coklu")})
    ozet = {"surum": SURUM, "olusturma_tr": datetime.now(TR).isoformat(timespec="seconds"),
            "sozluk": {"dosya": sozluk.yol.name, "sha256": sozluk.sha256, "kod_sayisi": sozluk.kod_sayisi},
            "pencere_tr": [p.isoformat() for p in pencere] if pencere else None, "akislar": {}}
    for akis, ets in etkinlik_akis.items():
        secilen, disari = pencereye_gore_filtrele(ets, pencere if akis == "mac_oncesi" else None)
        futbol, diger = [e for e in secilen if e["futbol"]], [e for e in secilen if not e["futbol"]]
        liste, yol, yedek = ham_listeler[akis]
        akisi_dogrula(rapor, akis, kaynaklar[akis], liste, yol, yedek, secilen, len(satirlar(futbol)))
        if disari:
            rapor.ekle("BILGI", akis, "FILTRE_DISI", "Tarih penceresi dışında kalan etkinlik ('filtre_disi' sayfası).", len(disari))
        anahtar_say: dict = {}
        for ev in liste:
            if isinstance(ev, dict):
                for k in ev:
                    anahtar_say[k] = anahtar_say.get(k, 0) + 1
        kaynaklar[akis]["etkinlik_alanlari"] = anahtar_say
        _onceki_karsilastir(rapor, akis, onceki, kaynaklar[akis], len(futbol))
        normal = {"kaynak": kaynaklar[akis], "pencere_tr": ozet["pencere_tr"],
                  "futbol": [_json_temiz(e) for e in futbol],
                  "futbol_uzun_vadeli": [_json_temiz(e) for e in diger if spor_grubu(e) == "futbol_uzun_vadeli"],
                  "spor_belirsiz": [_json_temiz(e) for e in diger if spor_grubu(e) == "spor_belirsiz"],
                  "diger_spor_sayilari": _say(e["spor_kodu"] for e in diger if e["spor_kodu"] is not None),
                  "diger_uzun_vadeli_sayilari": _say(spor_grubu(e) for e in diger
                                                     if spor_grubu(e).startswith("uzun_vadeli_")),
                  "filtre_disi_kodlar": [e["kod"] for e in disari],
                  "marketsiz_futbol": [_json_temiz(e) for e in marketsiz.get(akis, []) if e["futbol"]],
                  "ewma_eslesmeler": ewma_kayit if akis == "mac_oncesi" else [],
                  "isim_farklari": [x for x in isim_farklari
                                    if akis == "mac_oncesi" or x["kaynak"].endswith("canli")]}
        fu = sum(1 for e in diger if spor_grubu(e) == "futbol_uzun_vadeli")
        if fu:
            rapor.ekle("BILGI", akis, "FUTBOL_UZUN_VADELI", "TYPE=-1 futbol uzun vadeli pazarları ('futbol_uzun_vadeli' "
                       "sayfası; maç sayısına katılmadı).", fu)
        mfutbol = [e for e in marketsiz.get(akis, []) if e["futbol"]]
        if marketsiz.get(akis):
            rapor.ekle("BILGI", akis, "MARKETSIZ_MAC", "Bültende marketsiz listelenen etkinlik (EWMA); futbol olanlar "
                       "'marketsiz_maclar' sayfasında.", len(mfutbol), {"tum_sporlar": len(marketsiz[akis])})
        (cikti / f"{akis}.json").write_text(json.dumps(normal, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        ex = excel_yaz(cikti / f"{akis}.xlsx", akis, secilen, diger, disari, rapor, mfutbol,
                       {k: v for k, v in kaynaklar[akis].items() if k != "etkinlik_alanlari"},
                       {"ewma_eslesmeler": normal["ewma_eslesmeler"], "isim_farklari": normal["isim_farklari"]})
        ozet["akislar"][akis] = {**ex, "json": str(cikti / f"{akis}.json")}
    for akis in kaynaklar:
        if akis not in etkinlik_akis:
            ozet["akislar"][akis] = {"hata": "veri işlenemedi (bkz. dogrulama.json)"}
    ozet["kaynaklar"] = kaynaklar
    ozet["durum"] = rapor.durum()
    ozet["dogrulama"] = rapor.kayitlar
    (cikti / "kaynak.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (cikti / "dogrulama.json").write_text(json.dumps({"durum": ozet["durum"], "kayitlar": rapor.kayitlar},
                                                     ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return ozet


def _say(it) -> dict:
    s: dict = {}
    for x in it:
        s[str(x)] = s.get(str(x), 0) + 1
    return s


def _json_temiz(e: dict) -> dict:
    return {k: v for k, v in e.items() if k != "ad_uyumsuzluklari"}


def _onceki_karsilastir(rapor: Rapor, akis: str, onceki: Path | None, kaynak: dict, futbol_sayisi: int):
    if not onceki or not (onceki / "kaynak.json").exists():
        return
    try:
        eski = json.loads((onceki / "kaynak.json").read_text(encoding="utf-8"))
    except ValueError:
        return
    ek = eski.get("kaynaklar", {}).get(akis, {}).get("etkinlik_alanlari") or {}
    yeni = kaynak.get("etkinlik_alanlari") or {}
    kaybolan = sorted(set(ek) - set(yeni))
    if kaybolan:
        rapor.ekle("UYARI", akis, "ALAN_KAYBOLDU", "Önceki çekimde olan etkinlik alanları artık yok.", len(kaybolan), kaybolan)
    eklenen = sorted(set(yeni) - set(ek))
    if eklenen and ek:
        rapor.ekle("BILGI", akis, "YENI_ALAN", "Yeni etkinlik alanları.", len(eklenen), eklenen)
    eski_n = eski.get("akislar", {}).get(akis, {}).get("futbol_etkinlik")
    if eski_n and akis == "mac_oncesi" and abs(futbol_sayisi - eski_n) / eski_n > 0.5:
        rapor.ekle("UYARI", akis, "SAYI_DEGISIMI", f"Futbol etkinlik sayısı {eski_n} -> {futbol_sayisi} (%50'den fazla).")


def _son_cikti(kok: Path, haric: Path) -> Path | None:
    adaylar = sorted([p for p in kok.glob("bulten_*") if p.is_dir() and p != haric and (p / "kaynak.json").exists()])
    return adaylar[-1] if adaylar else None


def _pencere(arg) -> tuple | None:
    if arg.tarih:
        return gun_penceresi(tr_zaman(arg.tarih).date())
    if arg.bugun:
        return zaman_penceresi()
    if arg.baslangic or arg.bitis:
        if not (arg.baslangic and arg.bitis):
            raise SystemExit("--baslangic ve --bitis birlikte verilmeli.")
        bas, bit = tr_zaman(arg.baslangic), tr_zaman(arg.bitis)
        if bit <= bas:
            raise SystemExit("--bitis, --baslangic'tan sonra olmalı.")
        return bas, bit
    return None


def _ozet_yaz(ozet: dict, cikti: Path):
    print(f"\nDurum: {ozet['durum']}  |  Çıktı klasörü: {cikti}")
    for akis, a in ozet["akislar"].items():
        if "hata" in a:
            print(f"  {akis}: {a['hata']}")
        else:
            print(f"  {akis}: {a['futbol_etkinlik']} futbol etkinliği, {a['secenek_satiri']} seçenek satırı "
                  f"(Excel'de {a['excel_satiri']}) -> {Path(a['excel']).name}, {Path(a['json']).name}")
    for r in ozet["dogrulama"]:
        if r["seviye"] in ("KRITIK", "UYARI"):
            print(f"  [{r['seviye']}] {r['akis']} {r['kod']}: {r['mesaj']}" + (f" ({r['sayi']})" if r["sayi"] is not None else ""))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Nesine futbol bülteni (maç öncesi + canlı) -> ham JSON, JSON, Excel")
    alt = ap.add_subparsers(dest="komut", required=True)
    for ad in ("cek", "isle"):
        p = alt.add_parser(ad)
        p.add_argument("--cikti", default="output", help="çıktıların kök klasörü (varsayılan: output)")
        g = p.add_mutually_exclusive_group()
        g.add_argument("--tarih", help="tek gün: o gün 00:00 -> ertesi gün 03:00 (TR). ör. 24.11.2026")
        g.add_argument("--bugun", action="store_true", help="not defterindeki pencere: bugün 00:00 -> yarın 03:00 (TR)")
        p.add_argument("--baslangic", help="TR saatiyle başlangıç, ör. '2026-11-24 12:00'")
        p.add_argument("--bitis", help="TR saatiyle bitiş")
        if ad == "cek":
            p.add_argument("--akis", choices=["hepsi", "mac-oncesi", "canli"], default="hepsi")
        else:
            p.add_argument("--mac-oncesi-ham", help="daha önce kaydedilmiş maç öncesi ham JSON")
            p.add_argument("--canli-ham", help="daha önce kaydedilmiş canlı ham JSON")
            p.add_argument("--kaynak-klasor", help="önceki bir çekim klasörü: ham yanıtları ORİJİNAL çekim bilgisiyle yeniden işler")
    a = ap.parse_args(argv)
    pencere = _pencere(a)
    kok = Path(a.cikti)
    cikti = kok / f"bulten_{datetime.now(TR):%Y%m%d_%H%M%S}"
    cekimler = {}
    if a.komut == "cek":
        secim = {"hepsi": ("mac_oncesi", "canli"), "mac-oncesi": ("mac_oncesi",), "canli": ("canli",)}[a.akis]
        for akis in secim:
            print(f"{akis}: {AKISLAR[akis]['url']} çekiliyor (tek istek)...")
            cekimler[akis] = cek(AKISLAR[akis]["url"])
            m = cekimler[akis]["meta"]
            print(f"   HTTP {m['http_durumu']} | {m['bayt'] // 1024} KB | {m['sure_sn']} sn" + (f" | {m['hata']}" if m["hata"] else ""))
    elif a.kaynak_klasor:
        kk = Path(a.kaynak_klasor)
        eski = json.loads((kk / "kaynak.json").read_text(encoding="utf-8"))["kaynaklar"]
        for akis, meta in eski.items():
            if meta.get("ham_dosya"):
                g = (kk / meta["ham_dosya"]).read_bytes()
                if hashlib.sha256(g).hexdigest() != meta.get("sha256"):
                    raise SystemExit(f"{akis}: ham dosyanın SHA-256 özeti kaynak.json ile uyuşmuyor; işlem durduruldu.")
                tut = ("url", "cekim_utc", "cekim_tr", "user_agent", "http_durumu", "icerik_turu", "bayt", "sha256", "hata", "sure_sn")
                cekimler[akis] = {"govde": g, "meta": {**{k: meta.get(k) for k in tut},
                                                       "yeniden_islendi": f"{kk.name} klasöründeki ham yanıttan, yeni istek atılmadı"}}
            else:
                cekimler[akis] = {"govde": b"", "meta": {k: meta.get(k) for k in meta if k != "ham_dosya"}}
    else:
        for akis, dosya in (("mac_oncesi", a.mac_oncesi_ham), ("canli", a.canli_ham)):
            if dosya:
                g = Path(dosya).read_bytes()
                zaman = datetime.fromtimestamp(Path(dosya).stat().st_mtime, tz=timezone.utc)
                cekimler[akis] = {"govde": g, "meta": {
                    "url": f"dosya:{Path(dosya).name}", "kaynak_url": AKISLAR[akis]["url"],
                    "cekim_utc": zaman.isoformat(timespec="seconds"), "cekim_tr": zaman.astimezone(TR).isoformat(timespec="seconds"),
                    "cekim_zamani_notu": "dosya değiştirilme zamanı; gerçek çekim zamanı bilinmiyor",
                    "http_durumu": 200, "icerik_turu": "application/json", "bayt": len(g),
                    "sha256": hashlib.sha256(g).hexdigest(), "hata": None, "user_agent": None}}
        if not cekimler:
            raise SystemExit("En az bir ham dosya verin (--mac-oncesi-ham / --canli-ham).")
    ozet = isle(cekimler, cikti, pencere, onceki=_son_cikti(kok, cikti) if kok.exists() else None)
    _ozet_yaz(ozet, cikti)
    return 0 if ozet["durum"] != "BASARISIZ" else 2


if __name__ == "__main__":
    sys.exit(main())
