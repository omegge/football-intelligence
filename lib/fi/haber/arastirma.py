"""Tarihsel ve güncel araştırma oturumları — ayrı klasör, ayrı etiket, ayrı dondurma.

tarihsel : kesim = maç başlangıcı; sonuç biliniyor → çıktılar "KÖR DEĞİL" etiketi taşır; output/arastirma/tarihsel/
guncel   : kesim = araştırma anı ve başlangıçtan ÖNCE olmalı; önce model tahmininin SHA-256 özeti verilmiş olmalı
           (tahmin haberden önce dondurulur); output/arastirma/guncel/. Nesine fiyatı ancak dondurmadan sonra açılır.
Her oturum sabit kontrol listesini maç başına izler: her kategori ya kanıtla, ya durum kaydıyla
("aranip_bulunamadi", "erisim_engeli", "kaynak_yok" …) kapatılır; "aranmadı" kalan kategori raporda görünür.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ..kanit import Kanit, KanitDeposu
from .kanit_kaydi import KATEGORILER, DurumKaydi

KOK = Path(__file__).resolve().parents[3] / "output" / "arastirma"
KONTROL_LISTESI = ("kadro", "sakatlik", "ceza", "td_aciklama", "rotasyon", "fikstur", "motivasyon", "taktik",
                   "karsi_senaryo")
ETIKET = {"tarihsel": "TARİHSEL — sonuç biliniyor; KÖR TEST DEĞİLDİR",
          "guncel": "GÜNCEL — maç öncesi; tahmin haberden önce donduruldu"}


class ModHatasi(ValueError):
    pass


def _utc(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ModHatasi("zaman saat dilimli olmalı")
    return d.astimezone(timezone.utc)


class AramaOturumu:
    def __init__(self, mod: str, oturum_adi: str, kok: Path = KOK, tahmin_sha256: str | None = None,
                 simdi: str | None = None):
        if mod not in ETIKET:
            raise ModHatasi("mod 'tarihsel' ya da 'guncel' olmalı")
        if mod == "guncel" and not (tahmin_sha256 and len(tahmin_sha256) == 64):
            raise ModHatasi("güncel modda model tahmini haberden ÖNCE dondurulmuş olmalı (SHA-256 gerekli)")
        self.mod, self.tahmin_sha256 = mod, tahmin_sha256
        self.simdi = simdi or datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.klasor = Path(kok) / mod / oturum_adi
        self.klasor.mkdir(parents=True, exist_ok=True)
        self.depo = KanitDeposu(self.klasor / "kanitlar.jsonl")
        self.maclar: dict[str, dict] = {}
        self.durumlar: list[DurumKaydi] = []

    def mac_ekle(self, mac_id: str, baslama_utc: str) -> str:
        b = _utc(baslama_utc)
        if self.mod == "tarihsel":
            kesim = b
        else:
            kesim = _utc(self.simdi)
            if kesim >= b:
                raise ModHatasi("güncel modda araştırma maç başlamadan önce yapılmalı")
        self.maclar[mac_id] = {"baslama_utc": b.isoformat(), "kesim_zamani": kesim.isoformat(),
                               "kapatilan": set()}
        return kesim.isoformat()

    def kanit_ekle(self, k: Kanit) -> str:
        m = self.maclar.get(k.mac_id)
        if m is None:
            raise ModHatasi(f"maç oturuma eklenmemiş: {k.mac_id}")
        if k.deger.get("mod") != self.mod:
            raise ModHatasi("kanıt modu oturum moduyla aynı olmalı (tarihsel/güncel karışmaz)")
        y = k.deger.get("yayin_zamani")
        if not y or k.deger.get("zaman_durumu") != "mac_oncesi_dogrulandi":
            raise ModHatasi("yalnızca maç öncesi doğrulanmış kanıt eklenebilir")
        if len(y) > 10 and _utc(y) >= _utc(m["kesim_zamani"]):
            raise ModHatasi("kanıt kesim zamanından sonra yayımlanmış")
        m["kapatilan"].add(k.konu)
        return self.depo.ekle(k)

    def durum_ekle(self, d: DurumKaydi) -> None:
        if d.mac_id not in self.maclar:
            raise ModHatasi(f"maç oturuma eklenmemiş: {d.mac_id}")
        self.durumlar.append(d)
        if d.kategori:
            self.maclar[d.mac_id]["kapatilan"].add(d.kategori)

    def eksik_kategoriler(self, mac_id: str) -> list[str]:
        return [c for c in KONTROL_LISTESI if c not in self.maclar[mac_id]["kapatilan"]]

    def dondur(self) -> dict:
        rapor = {"etiket": ETIKET[self.mod], "mod": self.mod, "olusturma_utc": self.simdi,
                 "tahmin_sha256": self.tahmin_sha256,
                 "maclar": {k: {"baslama_utc": v["baslama_utc"], "kesim_zamani": v["kesim_zamani"],
                                "aranmadi": self.eksik_kategoriler(k)} for k, v in self.maclar.items()},
                 "durumlar": [asdict(d) for d in self.durumlar],
                 "kanit_ozeti": self.depo.ozet()}
        js = json.dumps(rapor, ensure_ascii=False, indent=1, sort_keys=True)
        (self.klasor / "oturum.json").write_text(js, encoding="utf-8")
        kanit_b = (self.klasor / "kanitlar.jsonl").read_bytes() if (self.klasor / "kanitlar.jsonl").exists() else b""
        ozet = {"oturum_sha256": hashlib.sha256(js.encode()).hexdigest(),
                "kanitlar_sha256": hashlib.sha256(kanit_b).hexdigest(),
                "dondurma_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        (self.klasor / "dondurma.json").write_text(json.dumps(ozet, indent=1), encoding="utf-8")
        return ozet


assert set(KONTROL_LISTESI) <= set(KATEGORILER)
