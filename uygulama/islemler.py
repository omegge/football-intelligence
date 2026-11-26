"""V1 işlemleri: mevcut modülleri MK-1 sırasıyla çağırır (yeni model yok).

  1. guncel_veri_cek     → fi.kaynaklar.guncel.guncelle (football-data.org season=2026; sonuçlar ve son maçlar)
  2. bulten_cek          → football-bulletin-fetch betiği (tek istek; Nesine maç öncesi)
  3. dondur_mac          → lig_guncel → is_akisi.bagimsiz_tahmin (oransız satır) → is_akisi.dondur
  4. fiyat_karsilastir_mac → yalnızca donmuş tahmin + dondurmadan SONRA çekilmiş bülten → bulten_dogrulama.disa_aktar
                           → is_akisi.fiyat_karsilastir (olasılık değişmez)
Haber araştırması bu uygulamada otomatik yapılmaz (ücretli arama API'si yok); Claude oturumunda yapılır ve
output/arastirma/genis_pilot/<maç>_<tur>/ altına kaydedilir, arayüz okur.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from . import veri as V
from fi import is_akisi as I

BETIK_KLASORU = V.KOK / ".claude" / "skills" / "football-bulletin-fetch" / "scripts"
KILIT = threading.Lock()


class IslemHatasi(RuntimeError):
    pass


class BultenHatasi(IslemHatasi):
    """Bülten çekimi başarısız; `kodlar` dogrulama.json'daki KRITIK kodlar (ör. BAGLANTI, ERISIM_ENGELI)."""

    def __init__(self, mesaj: str, kodlar: list[str], klasor: str | None):
        super().__init__(mesaj)
        self.kodlar, self.klasor = kodlar, klasor


def _tek_seferde(f):
    def sarmal(*a, **k):
        if not KILIT.acquire(blocking=False):
            raise IslemHatasi("başka bir işlem sürüyor; bitmesini bekleyin")
        try:
            return f(*a, **k)
        finally:
            KILIT.release()
    sarmal.__name__ = f.__name__
    sarmal.__doc__ = f.__doc__
    return sarmal


def fd_istemcisi():
    """football-data.org istemcisi. FD_TOKEN ortam değişkeni varsa (bulut) X-Auth-Token başlığını bağlantı açıcı ekler;
    yoksa (Claude ortamı) başlık eklenmez, ağ vekili ekler. Anahtar kayda ya da günlüğe yazılmaz."""
    import os
    from fi.kaynaklar import footballdataorg as F
    anahtar = os.environ.get("FD_TOKEN")
    if not anahtar:
        return F.FdorgIstemcisi()

    def acici(istek, zaman_asimi):
        istek.add_header("X-Auth-Token", anahtar)
        return F._varsayilan_acici(istek, zaman_asimi)
    return F.FdorgIstemcisi(onbellek=V.OUTPUT / "onbellek" / "footballdataorg", acici=acici)


def _bulten_dogrulama():
    spec = importlib.util.spec_from_file_location("bulten_dogrulama", BETIK_KLASORU / "bulten_dogrulama.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------------------------------ 1. güncel veri
@_tek_seferde
def guncel_veri_cek(istemci=None, kok: Path | None = None) -> dict:
    from fi.kaynaklar import guncel as G
    r = G.guncelle(istemci=istemci or fd_istemcisi(), kok=kok or V.OUTPUT / "guncel")
    return {"islem": "güncel veri", "utc": r["utc"], "yarisma": len(r["yarismalar"]), "sorunlu": r["sorunlu"],
            "son_biten": {k: v["son_biten_utc"] for k, v in r["yarismalar"].items()}}


# ------------------------------------------------------------------------------------------------ 2. bülten
@_tek_seferde
def bulten_cek(gun: str | None = None, cikti: Path = V.OUTPUT, zaman_asimi: int = 300) -> dict:
    """Seçili TR günü için yalnızca o gün 00:00–23:59 (maç listesiyle aynı kural). '--bugun' ve '--tarih' kullanılmaz:
    ikisi de pencereyi ertesi gün 03:00'e uzatır; '--bugun' ayrıca gece 03:00'e kadar önceki günü 'bugün' sayar."""
    from datetime import date
    g = date.fromisoformat(gun) if gun else V.simdi_tr().date()
    bas, bit = V.gun_araligi(g.isoformat())          # tam gün: 00:00 → ertesi gün 00:00 (03:00'e kadar uzatılmaz)
    komut = [sys.executable, str(BETIK_KLASORU / "nesine_bulletin.py"), "cek", "--baslangic", f"{bas:%Y-%m-%d %H:%M}",
             "--bitis", f"{bit:%Y-%m-%d %H:%M}", "--akis", "mac-oncesi", "--cikti", str(cikti)]
    p = subprocess.run(komut, capture_output=True, text=True, timeout=zaman_asimi, cwd=V.KOK)
    klasor = next((s.split("Çıktı klasörü:")[1].strip() for s in p.stdout.splitlines() if "Çıktı klasörü:" in s), None)
    if p.returncode != 0 or not klasor:
        kodlar = []
        if klasor and (Path(klasor) / "dogrulama.json").exists():
            d = json.loads((Path(klasor) / "dogrulama.json").read_text(encoding="utf-8"))
            kodlar = sorted({k.get("kod") for k in d.get("kayitlar", []) if k.get("seviye") == "KRITIK"})
        raise BultenHatasi(f"bülten çekilemedi (çıkış {p.returncode}; kritik: {', '.join(kodlar) or 'bilinmiyor'}): "
                           f"{(p.stderr or p.stdout)[-400:]}", kodlar, Path(klasor).name if klasor else None)
    return {"islem": "bülten", "gun": g.isoformat(), "klasor": Path(klasor).name, "cikti": p.stdout[-1500:]}


# ------------------------------------------------------------------------------------------------ 3. dondurma
def _fd_kimligi(kaynak_lig: str, mac: dict, tahmin: dict) -> dict:
    """Güncel anlık görüntüde aynı UTC dakikasında iki takımı da eşleşen football-data.org maçı (kimlik doğrulaması)."""
    utc = datetime.fromisoformat(mac["baslama_tr"]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    ev, dep = (tahmin.get("ev_esleme") or {}).get("kaynak_adi"), (tahmin.get("dep_esleme") or {}).get("kaynak_adi")
    for k in V.guncel_klasorleri():
        y = k / f"{V.FD_KODU[kaynak_lig]}.json"
        if y.exists():
            for m in V._json(y):
                if m["utc_baslama"][:16] == utc and (m["ev"], m["dep"]) == (ev, dep):
                    return {"nesine": mac["mac_id"], "fd_mac_id": m["kaynak_id"], "utc": m["utc_baslama"],
                            "durum": m["durum"], "anlik_goruntu": k.name}
            break
    return {"nesine": mac["mac_id"], "durum": "football-data.org eşleşmesi bulunamadı (aynı dakika + iki takım)"}


@_tek_seferde
def dondur_mac(kod: int, lig_maclari: list[dict] | None = None, lig_raporu: dict | None = None,
               kok: Path = V.TAHMIN, simdi: datetime | None = None) -> dict:
    mac, _ = V.mac_bul(kod)
    if mac is None:
        raise IslemHatasi(f"Nesine {kod} hiçbir bültende yok")
    if V.donmus_bul(kod, kok):
        raise IslemHatasi("bu maç için donmuş tahmin zaten var; donmuş tahmin değiştirilmez")
    hz = V.hazirlik_ozeti(mac)
    if hz["durum"] != "hazirlanabilir":
        raise IslemHatasi(f"bağımsız tahmin hazırlanamaz: {hz['neden']}")
    if lig_maclari is None:
        from fi.kaynaklar.guncel import lig_guncel
        lig_maclari, lig_raporu = lig_guncel(hz["kaynak_lig"], fd_istemcisi())
    satir = {k: mac[k] for k in ("mac_id", "karsilasma", "lig", "baslama_tr", "ev", "deplasman")}
    t = I.bagimsiz_tahmin(satir, lig_maclari, hz["kaynak_lig"])
    if t["durum"] != "hesaplandi":
        return {"islem": "dondurma", "durum": "hesaplanamaz", "nedenler": t.get("nedenler"), "donduruldu": False}
    if lig_raporu:
        fm = lig_raporu.get("fd_meta") or {}
        t["veri_kaynagi_raporu"] = {"son_tarih": lig_raporu.get("son_tarih"), "ayni": lig_raporu.get("ayni"),
                                    "eklenen": lig_raporu.get("eklenen"), "fd_sha256": fm.get("sha256"),
                                    "fd_erisim_utc": fm.get("erisim_utc"), "atif": fm.get("atif")}
    t["mac_kimligi_dogrulama"] = _fd_kimligi(hz["kaynak_lig"], satir, t)
    r = I.dondur(satir, t, kok=kok, simdi=simdi)
    return {"islem": "dondurma", "durum": "hesaplandi", "donduruldu": True, **r}


# ------------------------------------------------------------------------------------------------ 4. fiyat karşılaştırması
@_tek_seferde
def fiyat_karsilastir_mac(kod: int, kok: Path = V.OUTPUT, tahmin_kok: Path = V.TAHMIN) -> dict:
    d = V.donmus_bul(kod, tahmin_kok)
    if not d or d.get("hata"):
        raise IslemHatasi("önce bağımsız tahmin dondurulmalı (MK-1)")
    dondurma = datetime.fromisoformat(d["dondurma_utc"])
    if datetime.now(timezone.utc) >= datetime.fromisoformat(d["baslama_tr"]):
        raise IslemHatasi("maç başlamış: maç öncesi fiyat karşılaştırması yapılmaz")
    for k in V.bultenler(kok):
        cekim = (V._json(k / "mac_oncesi.json").get("kaynak") or {}).get("cekim_utc")
        if not cekim or datetime.fromisoformat(cekim) <= dondurma:
            continue
        if not any(m["kod"] == kod for m in V.bulten_maclari(k)):
            continue
        mevcut = k / f"fiyat_karsilastirma_{kod}.json"
        if mevcut.exists() and V._json(mevcut).get("donmus_sha256") == d["sha256"]:
            raise IslemHatasi(f"bu donmuş tahmin için {k.name} bülteniyle karşılaştırma zaten var (üzerine yazılmaz); "
                              "yeni karşılaştırma için yeni bülten çekin")
        BD = _bulten_dogrulama()
        disa = BD.disa_aktar(k, [kod])
        (k / f"dogrulama_{kod}.json").write_text(json.dumps(disa, ensure_ascii=False, indent=1), encoding="utf-8")
        nesine_mac = disa["maclar"][0]
        fk = I.fiyat_karsilastir(Path(d["yol"]), nesine_mac)
        (k / f"fiyat_karsilastirma_{kod}.json").write_text(json.dumps(fk, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"islem": "fiyat karşılaştırması", "klasor": k.name, "satir": len(fk["satirlar"]),
                "donmus_sha256": fk["donmus_sha256"]}
    raise IslemHatasi("dondurmadan sonra çekilmiş ve bu maçı içeren bülten yok: önce 'Bülten çek'")
