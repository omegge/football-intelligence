"""Oranlardan bağımsız maç araştırma girdisi.

Bülten çıktısından (mac_oncesi.json / canli.json) yalnızca izinli alanlar alınır: maç kimliği, takımlar, başlama
zamanı, lig, ülke/kategori ve veri bütünlüğü işaretleri. Marketler, seçenekler, oranlar ve MBS hiçbir zaman
geçmez (beyaz liste yaklaşımı). Üretilen fikstur.json analiz modüllerinin tek bülten girdisidir.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

IZINLI_ALANLAR = ("kod", "nid", "canli_kodu", "akis", "lig", "lig_ulke", "lig_kodu", "ev", "deplasman", "karsilasma",
                  "baslama_tr", "tarih", "saat", "diger_akista_da_var", "dogrulanmamis_eslesme", "isim_celiskisi",
                  "baslama_saati_gecmis", "zaman_okunamadi")
YASAK_PARCALAR = ("oran", "odds", "market", "secenek", "mbs", "kupon", "bahis", "oynanabilir", "price", "fiyat")


class OranSizintisi(ValueError):
    pass


def oransiz_mi(o, yol: str = "girdi") -> None:
    """Yapıda oran/bahis ile ilgili bir anahtar varsa OranSizintisi fırlatır."""
    if isinstance(o, dict):
        for k, v in o.items():
            if any(p in str(k).casefold() for p in YASAK_PARCALAR):
                raise OranSizintisi(f"oran/bahis alanı analiz girdisine sızdı: {yol}.{k}")
            oransiz_mi(v, f"{yol}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            oransiz_mi(v, f"{yol}[{i}]")


def mac_kimligi(e: dict) -> str:
    return f"nesine:{e['kod']}"


def fikstur_olustur(bulten_klasoru: Path) -> dict:
    """Bülten klasöründen oransız fikstür üretir (yalnızca futbol maçları)."""
    bulten_klasoru = Path(bulten_klasoru)
    maclar, kaynaklar = [], {}
    for akis in ("mac_oncesi", "canli"):
        dosya = bulten_klasoru / f"{akis}.json"
        if not dosya.exists():
            continue
        ham = dosya.read_bytes()
        veri = json.loads(ham)
        kaynaklar[akis] = {"dosya": dosya.name, "sha256": hashlib.sha256(ham).hexdigest(),
                           "cekim_tr": (veri.get("kaynak") or {}).get("cekim_tr")}
        for e in veri.get("futbol", []) + veri.get("marketsiz_futbol", []):
            m = {k: e.get(k) for k in IZINLI_ALANLAR}
            m["akis"] = akis
            m["mac_id"] = mac_kimligi(e)
            m["ewma_kaydi"] = not e.get("marketler")      # bültende yalnızca marketsiz listede bulunan maç
            maclar.append(m)
    fikstur = {"tur": "oransiz_fikstur", "olusturma_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "not": "Bu dosya oran, market, seçenek ya da MBS içermez; analiz modüllerinin tek bülten girdisidir.",
               "kaynak_bulten": str(bulten_klasoru.name), "kaynaklar": kaynaklar, "maclar": maclar}
    oransiz_mi(fikstur["maclar"], "maclar")
    return fikstur


def fikstur_yaz(bulten_klasoru: Path, hedef: Path | None = None) -> Path:
    fikstur = fikstur_olustur(bulten_klasoru)
    hedef = Path(hedef or Path(bulten_klasoru) / "fikstur.json")
    hedef.write_text(json.dumps(fikstur, ensure_ascii=False, indent=1), encoding="utf-8")
    return hedef


def fikstur_oku(yol: Path) -> dict:
    f = json.loads(Path(yol).read_text(encoding="utf-8"))
    if f.get("tur") != "oransiz_fikstur":
        raise OranSizintisi("bu dosya oransız fikstür değil; analiz modülleri bülten dosyalarını doğrudan okuyamaz")
    oransiz_mi(f.get("maclar"), "maclar")
    return f


def mac_bul(fikstur: dict, sorgu: str) -> list[dict]:
    """Kod (ör. '3318905' ya da 'nesine:3318905') veya takım adı parçasıyla arar."""
    q = str(sorgu).strip().casefold().removeprefix("nesine:")
    if q.isdigit():
        return [m for m in fikstur["maclar"] if str(m["kod"]) == q or str(m.get("canli_kodu")) == q]
    return [m for m in fikstur["maclar"] if q in str(m.get("karsilasma") or "").casefold()]


def arastirma_klasoru_hazirla(fikstur: dict, mac: dict, kok: Path) -> Path:
    """output/analiz/<tarih>_<kod>/ : girdi.json (oransız) ve boş kanit.jsonl."""
    oransiz_mi(mac, "mac")
    tarih = (mac.get("baslama_tr") or "")[:10] or "tarihsiz"
    k = Path(kok) / f"{tarih}_{mac['kod']}"
    k.mkdir(parents=True, exist_ok=True)
    girdi = {"tur": "mac_arastirma_girdisi", "mac": mac, "fikstur_kaynaklari": fikstur.get("kaynaklar"),
             "olusturma_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "uyari": ("Takım adı çelişkili ya da eşleşmesi doğrulanmamış maç; sonuçlar kupona alınmamalı."
                       if mac.get("dogrulanmamis_eslesme") or mac.get("isim_celiskisi") else None)}
    (k / "girdi.json").write_text(json.dumps(girdi, ensure_ascii=False, indent=1), encoding="utf-8")
    (k / "kanit.jsonl").touch(exist_ok=True)
    return k
