"""V1 arayüzünün (uygulama katmanı; lib/fi analiz kütüphanesinin dışında) salt okunur veri katmanı. Mevcut modülleri ve output/ çıktılarını okur; model YAZMAZ.

MK-1 arayüz kuralları:
  - Maç listesi ve maç özeti oran içermez (`oransiz_mac`).
  - Nesine fiyatları yalnızca o maç için SHA-256'sı doğrulanmış donmuş tahmin varsa ve karşılaştırma
    dondurmadan sonra yapılmışsa gösterilir (`fiyat_karsilastirmasi`).
  - Sürpriz araştırması bilgi amaçlıdır; olasılığa eklenmez.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fi import is_akisi as I
from fi.girdi import oransiz_mi
from fi.kaynaklar.guncel import FD_KODU

KOK = Path(__file__).resolve().parents[1]
# FI_OUTPUT: deneme ve tarayıcı testleri için ayrı çıktı kökü (gerçek arşive dokunmadan)
OUTPUT = Path(os.environ.get("FI_OUTPUT") or KOK / "output")
TAHMIN = OUTPUT / "tahminler"
BULTEN_DESENI = re.compile(r"bulten_(\d{8})_(\d{6})")


def _json(yol: Path):
    return json.loads(Path(yol).read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------ bülten
def bultenler(kok: Path = OUTPUT) -> list[Path]:
    """Maç öncesi bülteni olan çekim klasörleri, yeniden eskiye."""
    return sorted((p for p in Path(kok).glob("bulten_*") if BULTEN_DESENI.fullmatch(p.name)
                   and (p / "mac_oncesi.json").exists() and not _basarisiz(p)), key=lambda p: p.name, reverse=True)


def _basarisiz(klasor: Path) -> bool:
    d = Path(klasor) / "dogrulama.json"
    try:
        return d.exists() and json.loads(d.read_text(encoding="utf-8")).get("durum") == "BASARISIZ"
    except ValueError:
        return True


def bulten_bilgisi(klasor: Path) -> dict:
    b = _json(Path(klasor) / "mac_oncesi.json")
    k = b.get("kaynak", {})
    return {"klasor": Path(klasor).name, "cekim_tr": k.get("cekim_tr"), "sha256": k.get("sha256"),
            "mac_sayisi": len(b.get("futbol", [])), "pencere_tr": b.get("pencere_tr")}


def oransiz_mac(m: dict) -> dict:
    """Bülten satırından oransız maç özeti (marketler atılır)."""
    o = {"kod": m["kod"], "mac_id": f"nesine:{m['kod']}", "lig": m.get("lig"), "lig_kodu": m.get("lig_kodu"),
         "lig_ulke": m.get("lig_ulke"), "ev": m.get("ev"), "deplasman": m.get("deplasman"),
         "karsilasma": m.get("karsilasma"), "baslama_tr": m.get("baslama_tr"),
         "tarih_saat_celiskisi": m.get("tarih_saat_celiskisi"), "market_sayisi": len(m.get("marketler") or [])}
    oransiz_mi({k: v for k, v in o.items() if k != "market_sayisi"}, "mac")
    return o


def bulten_maclari(klasor: Path) -> list[dict]:
    return [oransiz_mac(m) for m in _json(Path(klasor) / "mac_oncesi.json").get("futbol", []) if m.get("baslama_tr")]


def gunun_maclari(klasor: Path, gun: str) -> list[dict]:
    """Türkiye saatine göre gün (is_akisi.gunun_maclari ile aynı kural)."""
    return I.gunun_maclari({"maclar": bulten_maclari(klasor)}, gun)


def gun_araligi(gun: str) -> tuple[datetime, datetime]:
    """Seçilen TR günü: [gün 00:00, ertesi gün 00:00) — ertesi gün 00:00–03:00 dahil DEĞİL."""
    g = date.fromisoformat(gun)
    bas = datetime(g.year, g.month, g.day, tzinfo=I.TR)
    return bas, bas + timedelta(days=1)


def bulten_gunleri(klasor: Path) -> list[str]:
    """Bülten penceresinin TAMAMEN kapsadığı TR günleri. Pencere 27.11 00:00 → 28.11 03:00 ise yalnızca 27.11
    (28.11'in yalnızca ilk 3 saati var: o gün eksik olduğu için seçilemez). Pencere bilgisi yoksa maçların günleri."""
    b = _json(Path(klasor) / "mac_oncesi.json")
    pen = b.get("pencere_tr")
    gunler = sorted({datetime.fromisoformat(m["baslama_tr"]).astimezone(I.TR).date().isoformat()
                     for m in b.get("futbol", []) if m.get("baslama_tr")})
    if not pen or not all(pen):
        return gunler
    bas, bit = (datetime.fromisoformat(x) for x in pen)
    return [g for g in gunler if gun_araligi(g)[0] >= bas and gun_araligi(g)[1] <= bit]


def gun_disi_maclar(klasor: Path, gun: str) -> int:
    """Bültende seçilen günün hemen ertesi (00:00–03:00) penceresinde olup bu güne dahil edilmeyen maç sayısı."""
    _, bit = gun_araligi(gun)
    return sum(1 for m in bulten_maclari(klasor)
               if bit <= datetime.fromisoformat(m["baslama_tr"]) < bit + timedelta(hours=3))


def mac_bul(kod: int, kok: Path = OUTPUT) -> tuple[dict | None, Path | None]:
    """Maçı en yeni bültenden bulur (oransız)."""
    for k in bultenler(kok):
        for m in bulten_maclari(k):
            if m["kod"] == kod:
                return m, k
    return None, None


# ------------------------------------------------------------------------------------------------ hazırlık
def hazirlik_ozeti(mac: dict) -> dict:
    """Olasılık hesaplamadan, maçın bağımsız tahmin kapısındaki ilk engeli (lig eşlemesi + model kapsamı)."""
    kaynak_lig = I.lig_eslemesi(mac["lig"], lig_kodu=mac.get("lig_kodu")) if mac.get("lig") else None
    kapsam, _ = I.kapsam_yukle()
    modeller = [ad for ad, m in kapsam["modeller"].items() if kaynak_lig in m.get("degerlendirme_ligleri", [])]
    if kaynak_lig is None:
        durum, neden = "hesaplanamaz", "lig eşlemesi onaylı değil (veri/lig_eslemeleri.json)"
    elif not modeller:
        durum, neden = "hesaplanamaz", f"{kaynak_lig} ligi için ileriye dönük değerlendirilmiş model yok"
    elif kaynak_lig not in FD_KODU:
        durum, neden = "hesaplanamaz", f"{kaynak_lig} için güncel veri kaynağı yok"
    else:
        durum, neden = "hazirlanabilir", "lig onaylı ve model kapsamda; veri güncelliği dondurmada denetlenir"
        adaylar = _aday_adlari(kaynak_lig)
        if adaylar and mac.get("ev") and mac.get("deplasman"):
            from fi.takim_adlari import TakimEslestirici
            E = TakimEslestirici()
            sorun = [f"'{ad}' → {e.durum}" for ad in (mac["ev"], mac["deplasman"])
                     for e in [E.eslestir(ad, f"openfootball:{kaynak_lig}", adaylar)] if not e.kullanilabilir]
            if sorun:
                durum, neden = "takim_onayi_gerekli", "takım eşlemesi kesin değil: " + ", ".join(sorun) + \
                    " (kullanıcı onayı gerekir; benzer ada göre otomatik eşlenmez)"
    return {"kaynak_lig": kaynak_lig, "modeller": modeller, "durum": durum, "neden": neden}


_ADAY_ONBELLEK: dict = {}


def _aday_adlari(kaynak_lig: str) -> list[str]:
    """Güncel football-data.org anlık görüntüsündeki takım adları (dondurmadaki birleşik verinin güncel sezon adları)."""
    kod = FD_KODU.get(kaynak_lig)
    for k in guncel_klasorleri():
        y = k / f"{kod}.json"
        if y.exists():
            anahtar = (str(y), y.stat().st_mtime)
            if anahtar not in _ADAY_ONBELLEK:
                _ADAY_ONBELLEK[anahtar] = sorted({x for m in _json(y) for x in (m["ev"], m["dep"])})
            return _ADAY_ONBELLEK[anahtar]
    return []


# ------------------------------------------------------------------------------------------------ dondurulmuş tahmin
def donmus_tahminler(kok: Path = TAHMIN) -> list[dict]:
    yol = Path(kok) / "kayit.jsonl"
    if not yol.exists():
        return []
    out = []
    for satir in yol.read_text(encoding="utf-8").splitlines():
        if satir.strip():
            k = json.loads(satir)
            k["yol"] = str(Path(kok) / k["dosya"])
            out.append(k)
    return out


def donmus_bul(kod: int, kok: Path = TAHMIN) -> dict | None:
    """Maçın en son donmuş tahmini; SHA-256 doğrulanır (bozuksa 'hata' alanı döner)."""
    adaylar = [k for k in donmus_tahminler(kok) if k["mac_id"] == f"nesine:{kod}"]
    if not adaylar:
        return None
    son = sorted(adaylar, key=lambda k: k["dondurma_utc"])[-1]
    try:
        d = I.donmus_oku(Path(son["yol"]))
    except (ValueError, FileNotFoundError) as e:
        return {"hata": str(e), **son}
    d["yol"] = son["yol"]
    d["surum_sayisi"] = len(adaylar)
    return d


# ------------------------------------------------------------------------------------------------ fiyat (dondurmadan sonra)
def fiyat_karsilastirmasi(kod: int, donmus: dict | None, kok: Path = OUTPUT) -> dict:
    """Yalnızca donmuş tahminle eşleşen ve dondurmadan sonra yapılmış karşılaştırma dosyası."""
    if not donmus or donmus.get("hata"):
        return {"durum": "kilitli", "neden": "önce bağımsız tahmin dondurulmalı (MK-1); fiyatlar gösterilmez"}
    for k in bultenler(kok):
        yol = k / f"fiyat_karsilastirma_{kod}.json"
        if not yol.exists():
            continue
        f = _json(yol)
        if f.get("donmus_sha256") != donmus["sha256"]:
            continue
        if datetime.fromisoformat(f["karsilastirma_utc"]) <= datetime.fromisoformat(donmus["dondurma_utc"]):
            continue
        return {"durum": "var", "klasor": k.name, **f}
    return {"durum": "yok", "neden": "donmuş tahmin var; dondurmadan sonra çekilmiş bültenle karşılaştırma yapılmadı"}


def en_yuksek_fiyatlar(fk: dict) -> list[dict]:
    """Eşdeğer seçenek grupları: oynanabilir ve 'kesin' üyeler arasında en yüksek oran; diğer üyeler ayrıca sayılır."""
    out = []
    for g in (fk.get("esdegerlik") or {}).get("esdegerlik_gruplari", []):
        uye = g.get("uyeler", [])
        uygun = [u for u in uye if u.get("oynanabilirlik") == "oynanabilir" and u.get("kesinlik") == "kesin"
                 and u.get("oran")]
        if not uygun:
            continue
        en = max(uygun, key=lambda u: u["oran"])
        out.append({"olay": g.get("olay"), "kapsam": g.get("kapsam"), "en_yuksek": en,
                    "uye_sayisi": len(uye), "kesin_oynanabilir": len(uygun),
                    "kontrol_gerekli": sum(u.get("kesinlik") != "kesin" for u in uye),
                    "fark": round(en["oran"] - min(u["oran"] for u in uygun), 2)})
    return sorted(out, key=lambda r: -r["uye_sayisi"])


# ------------------------------------------------------------------------------------------------ güncel sportif veri
def guncel_klasorleri(kok: Path = OUTPUT / "guncel") -> list[Path]:
    return sorted((p for p in Path(kok).glob("*") if p.is_dir()), reverse=True)


def son_maclar(kaynak_lig: str, takim_kaynak_adi: str, n: int = 10, kok: Path = OUTPUT / "guncel") -> dict:
    """football-data.org anlık görüntüsünden takımın son n bitmiş maçı (bağımsız veri; oran yok)."""
    kod = FD_KODU.get(kaynak_lig)
    for k in guncel_klasorleri(kok):
        yol = k / f"{kod}.json"
        if not yol.exists():
            continue
        maclar = [m for m in _json(yol) if m.get("durum") == "FINISHED"
                  and takim_kaynak_adi in (m.get("ev"), m.get("dep"))]
        maclar.sort(key=lambda m: m["utc_baslama"])
        son = maclar[-n:]
        ozet = {"G": 0, "B": 0, "M": 0, "atilan": 0, "yenilen": 0, "kg": 0, "ust25": 0}
        satirlar = []
        for m in reversed(son):
            ev = m["ev"] == takim_kaynak_adi
            a, y = (m["ms_ev"], m["ms_dep"]) if ev else (m["ms_dep"], m["ms_ev"])
            s = "G" if a > y else ("B" if a == y else "M")
            ozet[s] += 1
            ozet["atilan"] += a
            ozet["yenilen"] += y
            ozet["kg"] += a > 0 and y > 0
            ozet["ust25"] += a + y > 2
            satirlar.append({"tarih_tr": m["tr_baslama"][:16].replace("T", " "), "saha": "E" if ev else "D",
                             "rakip": m["dep"] if ev else m["ev"], "skor": f"{a}-{y}", "sonuc": s,
                             "iy": None if m.get("iy_ev") is None else
                             (f"{m['iy_ev']}-{m['iy_dep']}" if ev else f"{m['iy_dep']}-{m['iy_ev']}"),
                             "hafta": m.get("hafta")})
        return {"kaynak": f"football-data.org {kod}", "anlik_goruntu": k.name, "mac": len(son),
                "ozet": ozet, "satirlar": satirlar}
    return {"kaynak": None, "mac": 0, "neden": "güncel veri anlık görüntüsü yok", "satirlar": []}


def mac_durumu_fd(kaynak_lig: str, fd_mac_id: int, kok: Path = OUTPUT / "guncel") -> dict | None:
    kod = FD_KODU.get(kaynak_lig)
    for k in guncel_klasorleri(kok):
        yol = k / f"{kod}.json"
        if yol.exists():
            for m in _json(yol):
                if m.get("kaynak_id") == fd_mac_id:
                    return {**m, "anlik_goruntu": k.name}
            return None
    return None


# ------------------------------------------------------------------------------------------------ haber araştırması
def haber_raporlari(kod: int, kok: Path = OUTPUT / "arastirma" / "genis_pilot") -> list[dict]:
    """Maçın bütün haber araştırması sürümleri (rapor.json olanlar), yeniden eskiye."""
    out = []
    for d in sorted(Path(kok).glob("*"), reverse=True):
        r = d / "rapor.json"
        if r.exists():
            j = _json(r)
            if (j.get("mac") or {}).get("mac_id") == f"nesine:{kod}":
                ham = _json(d / "arastirma.json") if (d / "arastirma.json").exists() else {}
                out.append({"surum": d.name, "rapor": j, "iddialar": ham.get("iddialar", []),
                            "kayit_utc": ham.get("kayit_utc"),
                            "turlar_md": (d / "TURLAR.md").read_text(encoding="utf-8") if (d / "TURLAR.md").exists() else None})
    return sorted(out, key=lambda r: r.get("kayit_utc") or "", reverse=True)


def haber_tazeligi(rapor: dict, baslama_tr: str, simdi: datetime | None = None) -> dict:
    """Araştırma ne zaman yapıldı, hangi turdu, şu anki tur ne; eski araştırma güncel gibi gösterilmez."""
    from fi.haber.genis import GenisHata, arastirma_turu
    simdi = simdi or datetime.now(timezone.utc)
    son = (rapor.get("10_son_arastirma_ve_kaynaklar") or {})
    zaman = son.get("son_arastirma_utc")
    turlar = son.get("turlar") or []
    baslama = datetime.fromisoformat(baslama_tr).astimezone(timezone.utc)
    try:
        simdiki = arastirma_turu(baslama.isoformat(), simdi)
    except GenisHata:
        simdiki = "maç başladı"
    yas_saat = (simdi - datetime.fromisoformat(zaman)).total_seconds() / 3600 if zaman else None
    guncel = bool(zaman) and simdiki in turlar and yas_saat is not None and yas_saat <= 6
    return {"son_arastirma_utc": zaman, "turlar": turlar, "simdiki_tur": simdiki,
            "yas_saat": None if yas_saat is None else round(yas_saat, 1),
            "maca_kala_saat": round((baslama - datetime.fromisoformat(zaman)).total_seconds() / 3600, 1) if zaman else None,
            "guncel": guncel}


def iddia_satirlari(kayit: dict) -> list[dict]:
    """Ham iddialar + grup doğrulama seviyesi (rapor gruplarındaki URL zincirlerinden)."""
    r = kayit["rapor"]
    seviye = {}
    for g in (r.get("1_dogrulanmis_son_dakika") or []) + (r.get("2_dogrulanamayan_veya_celiskili") or []):
        for urller in (g.get("zincirler") or {}).values():
            for u in urller:
                seviye.setdefault((u, g.get("konu"), g.get("takim")), g.get("dogrulama"))
    out = []
    for i in kayit.get("iddialar", []):
        out.append({**i, "dogrulama": seviye.get((i.get("url"), i.get("konu"), i.get("takim")), "gruplanmadi")})
    return sorted(out, key=lambda x: (x.get("arastirma_utc") or "", x.get("konu") or ""), reverse=True)


def analiz_raporlari(kod: int, kok: Path = OUTPUT / "raporlar") -> list[dict]:
    """output/raporlar altında maç koduna ya da donmuş tahmine atıf yapan Markdown raporlar."""
    out = []
    for p in sorted(Path(kok).glob("*.md")):
        t = p.read_text(encoding="utf-8")
        if str(kod) in t or (p.name.startswith("SOU_MID") and kod == 3331002):
            out.append({"ad": p.name, "metin": t})
    return out


# ------------------------------------------------------------------------------------------------ sürpriz araştırması
def surpriz_arastirmasi(kok: Path = OUTPUT / "arastirma" / "surpriz_pilot_v1") -> dict:
    kok = Path(kok)
    kod = kok / "pilot_kodlama_v2.json"
    if not kod.exists():
        kod = kok / "pilot_kodlama.json"
    return {"rapor_md": (kok / "PILOT_RAPORU.md").read_text(encoding="utf-8") if (kok / "PILOT_RAPORU.md").exists() else None,
            "kodlama": _json(kod) if kod.exists() else None, "kodlama_dosyasi": kod.name if kod.exists() else None,
            "uyari": "Keşif verisi (n=10+10, kör değil). Sinyaller kanıtlanmadı; olasılığa EKLENMEZ."}


# ------------------------------------------------------------------------------------------------ arşiv ve performans
def arsiv(kok: Path = TAHMIN) -> list[dict]:
    """Donmuş tahminler + (varsa) güncel veriden gerçekleşen skor + ileri puanlama."""
    out = []
    for k in donmus_tahminler(kok):
        satir = {"mac_id": k["mac_id"], "dosya": k["dosya"], "dondurma_utc": k["dondurma_utc"],
                 "baslama_tr": k["baslama_tr"], "durum": k["durum"], "sha256": k["sha256"]}
        try:
            d = I.donmus_oku(Path(k["yol"]))
        except (ValueError, FileNotFoundError) as e:
            satir["butunluk"] = f"HATA: {e}"
            satir["sonuc"] = "puanlanmaz (bütünlük hatası)"
            out.append(satir)
            continue
        satir["butunluk"] = "SHA-256 doğrulandı"
        satir["karsilasma"] = d.get("karsilasma")
        t = d.get("tahmin") or {}
        kimlik = t.get("mac_kimligi_dogrulama") or {}
        lig = I.lig_eslemesi(d.get("lig")) if d.get("lig") else None
        fd = mac_durumu_fd(lig, kimlik.get("fd_mac_id")) if lig and kimlik.get("fd_mac_id") else None
        if fd and fd.get("durum") == "FINISHED" and fd.get("normal_sure_ev") is not None:
            satir["sonuc"] = f"{fd['normal_sure_ev']}-{fd['normal_sure_dep']}"
            p = I.ileri_puanla(Path(k["yol"]), fd["normal_sure_ev"], fd["normal_sure_dep"],
                               f"football-data.org {fd['kaynak_id']} ({fd['anlik_goruntu']})")
            pu = p.get("puanlar") or {}
            satir["puan"] = {"market": len(pu),
                             "ort_log_loss": round(sum(v["log_loss"] for v in pu.values()) / len(pu), 4) if pu else None,
                             "ort_brier": round(sum(v["brier"] for v in pu.values()) / len(pu), 4) if pu else None,
                             "ayrinti": pu}
        else:
            satir["sonuc"] = "henüz yok" if not fd else f"durum: {fd.get('durum')}"
        out.append(satir)
    return out


def simdi_tr() -> datetime:
    return datetime.now(timezone.utc).astimezone(I.TR)
