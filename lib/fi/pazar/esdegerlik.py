"""Market eşdeğerliği ve fiyat tutarlılığı denetimi (B aşaması).

Yöntem
------
Her bülten seçeneği, 90 dakikalık maçın devre skorları uzayında bir OLAY'a çevrilir:
    nokta = (h1, a1, h2, a2)  -> 1. yarı ev/dep golü, 2. yarı ev/dep golü (her biri 0..UST)
    maç sonu: H = h1 + h2, A = a1 + a2
Olay bu ızgara üzerinde bir boolean maskedir. İki seçenek ancak maskeleri BİREBİR aynıysa aynı olaydır.
Izgara sınırı (UST) bütün çizgilerin üstünde tutulur; sınırı aşan eşik içeren seçenek eşlenmez.

Kesinlik düzeyleri
------------------
- "kesin": market kodu sözlükte, seçenek adları sözlükteki beklenen adlarla aynı, yarım çizgi (iade yok),
  market adında uzatma ibaresi yok. Olay eşdeğerliği matematiksel olarak kesindir; KAPSAM ise
  "normal süre (90+uzatma dakikaları), uzatma devreleri ve penaltılar hariç" VARSAYIMIDIR: Nesine kural
  metni bu sürümde okunmadı (kapsam_kaynagi alanında yazılır).
- "kontrol_gerekli": anlamı market kuralına bağlı seçenekler (ör. 'İlk Golü Hangi Takım Atar? = Olmaz',
  'Maç Skoru = diğer', aday adlı kodlar). Gruba dahil edilir ama "en yüksek fiyat"ın kesin listesine girmez.
- eşlenmedi: skor uzayıyla tanımlanamayan (korner, kart, oyuncu, özel) ya da adı/anlamı belirsiz seçenekler.

Kurallar (MK-1)
---------------
- Bu modül olasılık üretmez; oranları model girdisi yapmaz.
- Fiyat farkı arbitraj ya da pozitif beklenen değer olarak NİTELENDİRİLMEZ. Başabaş eşiği (1/oran)
  yalnızca eşiktir; gerçek olasılık değildir.
- "En yüksek fiyat" yalnızca oynanabilirlik == 'oynanabilir' ve kesinlik == 'kesin' seçeneklerden seçilir.
- Ham bülten değiştirilmez; girdi bulten_dogrulama.disa_aktar çıktısıdır.
"""
from __future__ import annotations

import argparse
import os
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SURUM = "esdegerlik-0.1"
from ..olay_uzayi import *  # noqa: F401,F403  (ızgara ve olay tanımları)
from ..olay_uzayi import (UST, H1, A1, H2, A2, H, A, TUM, EN_BUYUK_ESIK, ADAY_DEP_AU, SKOR_KODLARI,
                          _tablo, _skor_olayi)
KAPSAM_NORMAL = "normal_sure"
KAPSAM_KAYNAGI = ("varsayim: market adında 'Uzt.' ibaresi yok; Nesine kural metni bu sürümde okunmadı — "
                  "uzatma devreleri/penaltılar hariç 90 dk + uzatma dakikaları kabul edildi")


@dataclass
class Olay:
    maske: np.ndarray
    aciklama: str
    kesinlik: str = "kesin"          # kesin | kontrol_gerekli
    neden: str | None = None          # kontrol_gerekli ise neden


@dataclass
class Secenek:
    mac_kodu: int
    market_kodu: int
    market_adi: str
    cizgi: float
    secenek_no: int
    secenek_adi: str
    oran: float | None
    oynanabilirlik: str
    market_durumu_MS: int | None
    olay: Olay | None = None
    eslenmeme_nedeni: str | None = None

    @property
    def kimlik(self) -> str:
        return f"{self.market_kodu}|{self.cizgi:g}|{self.secenek_no}"

    def ozet(self) -> dict:
        d = {"market_kodu": self.market_kodu, "market_adi": self.market_adi, "cizgi": self.cizgi,
             "secenek_no": self.secenek_no, "secenek_adi": self.secenek_adi, "oran": self.oran,
             "oynanabilirlik": self.oynanabilirlik, "market_durumu_MS": self.market_durumu_MS}
        if self.olay is not None:
            d["kesinlik"] = self.olay.kesinlik
            if self.olay.neden:
                d["kontrol_nedeni"] = self.olay.neden
        return d


def market_olaylari(market: dict, mac_kodu: int) -> list[Secenek]:
    kod = market["market_kodu"]
    cizgi = float(market.get("cizgi") or 0.0)
    ad = market.get("market_adi") or ""
    secenekler = []
    for s in market.get("secenekler", []):
        secenekler.append(Secenek(mac_kodu, kod, ad, cizgi, s.get("secenek_no"), s.get("secenek_adi") or "",
                                  s.get("oran"), s.get("oynanabilirlik") or "bilinmiyor",
                                  market.get("market_durumu_MS")))
    if "Uzt." in ad:
        for s in secenekler:
            s.eslenmeme_nedeni = "uzatma dahil market: kapsam 90 dk skor uzayından farklı"
        return secenekler
    if market.get("adsiz") and kod not in ADAY_DEP_AU:
        for s in secenekler:
            s.eslenmeme_nedeni = "adsız market"
        return secenekler

    if kod in SKOR_KODLARI:
        tanimli = []
        for s in secenekler:
            m, neden = _skor_olayi(kod, s.secenek_adi)
            if m is not None:
                s.olay = Olay(m, s.secenek_adi)
                tanimli.append(m)
            elif s.secenek_adi.strip().lower() == "diğer" and kod in (777, 779):
                s.eslenmeme_nedeni = "diger_bekliyor"
            else:
                s.eslenmeme_nedeni = neden
        for s in secenekler:
            if s.eslenmeme_nedeni == "diger_bekliyor":
                s.eslenmeme_nedeni = None
                birlesim = np.logical_or.reduce(tanimli) if tanimli else ~TUM
                s.olay = Olay(~birlesim, "listelenen skorların dışındaki her skor", "kontrol_gerekli",
                              "'diğer' seçeneğinin listelenmeyen bütün skorları kapsadığı market kural metniyle "
                              "doğrulanmadı")
        return secenekler

    if kod == 291:
        for s in secenekler:
            if s.secenek_adi == "Olmaz":
                s.olay = Olay((H + A) == 0, "maçta gol yok", "kontrol_gerekli",
                              "market kural metni okunmadı (kendi kalesine gol, iptal edilen gol kuralı)")
            else:
                s.eslenmeme_nedeni = "ilk golü atan takım skor uzayından belirlenemez (zaman sırası gerekir)"
        return secenekler

    tablo, not_ = _tablo(kod, cizgi, ad, market.get("handikap"))
    if tablo is None:
        for s in secenekler:
            s.eslenmeme_nedeni = not_ or "skor uzayıyla tanımlı değil (korner/kart/oyuncu/özel ya da tanımsız kod)"
        return secenekler

    aday = kod in ADAY_DEP_AU
    aday_sira = {1: "Alt", 2: "Üst"}
    for s in secenekler:
        anahtar = aday_sira.get(s.secenek_no) if aday else s.secenek_adi
        if anahtar not in tablo:
            s.eslenmeme_nedeni = f"seçenek adı beklenen adlarla uyuşmuyor: '{s.secenek_adi}'"
            continue
        if aday:
            s.olay = Olay(tablo[anahtar], f"aday: {anahtar}", "kontrol_gerekli", not_)
        else:
            s.olay = Olay(tablo[anahtar], anahtar)
    return secenekler


# ---------------------------------------------------------------------------------------------------------
# Denetimler
# ---------------------------------------------------------------------------------------------------------
def _imza(maske: np.ndarray) -> str:
    return hashlib.sha1(np.packbits(maske).tobytes()).hexdigest()


def _olay_tanimi(maske: np.ndarray) -> str:
    """İnsan okunur kısa tanım: maç sonu skoru olarak ifade edilebiliyorsa skor listesi."""
    ms = set(zip(H[maske].tolist(), A[maske].tolist()))
    # olay yalnızca maç sonu skoruna mı bağlı?
    yalniz_ms = True
    hucre = {}
    for h, a, m in zip(H.tolist(), A.tolist(), maske.tolist()):
        hucre.setdefault((h, a), set()).add(m)
    for k, v in hucre.items():
        if len(v) > 1:
            yalniz_ms = False
            break
    if yalniz_ms and len(ms) <= 6:
        return "maç sonu skoru ∈ {" + ", ".join(f"{h}-{a}" for h, a in sorted(ms)) + "}"
    if yalniz_ms:
        return f"maç sonu skoruna bağlı olay ({len(ms)} skor)"
    return "devre skorlarına bağlı olay"


def _oynanabilir(s: Secenek) -> bool:
    return s.oynanabilirlik == "oynanabilir" and isinstance(s.oran, (int, float)) and s.oran > 1.0


def esdegerlik_gruplari(secenekler: list[Secenek]) -> list[dict]:
    gruplar: dict[str, list[Secenek]] = {}
    for s in secenekler:
        if s.olay is not None:
            gruplar.setdefault(_imza(s.olay.maske), []).append(s)
    sonuc = []
    for imza, uyeler in gruplar.items():
        if len({(u.market_kodu, u.cizgi) for u in uyeler}) < 2:
            continue  # tek marketteki olay: karşılaştırma yok
        kesin = [u for u in uyeler if u.olay.kesinlik == "kesin"]
        kontrol = [u for u in uyeler if u.olay.kesinlik != "kesin"]
        oyn_kesin = [u for u in kesin if _oynanabilir(u)]
        oyn_hepsi = [u for u in uyeler if _oynanabilir(u)]
        en_yuksek = max(oyn_kesin, key=lambda u: u.oran) if oyn_kesin else None
        en_dusuk = min(oyn_kesin, key=lambda u: u.oran) if oyn_kesin else None
        g = {
            "olay_imzasi": imza,
            "olay": _olay_tanimi(uyeler[0].olay.maske) + " — ör. " + min(
                uyeler, key=lambda u: (u.olay.kesinlik != "kesin", u.market_kodu)).market_adi + ": " + min(
                uyeler, key=lambda u: (u.olay.kesinlik != "kesin", u.market_kodu)).secenek_adi,
            "kapsam": KAPSAM_NORMAL,
            "kapsam_kaynagi": KAPSAM_KAYNAGI,
            "olay_esdegerligi": "kesin" if len(kesin) >= 2 and not kontrol else (
                "kesin (kesin üyeler arasında); diğer üyeler için kontrol gerekli" if len(kesin) >= 2
                else "kontrol gerekli"),
            "uyeler": [u.ozet() for u in sorted(uyeler, key=lambda u: -(u.oran or 0))],
            "en_yuksek_fiyat": None if not en_yuksek else {
                **en_yuksek.ozet(), "basabas_esigi": round(1.0 / en_yuksek.oran, 6),
                "not": "başabaş eşiği = 1/oran; gerçek olasılık değildir"},
            "kesin_oynanabilir_fiyat_araligi": None if not en_yuksek else [en_dusuk.oran, en_yuksek.oran],
            "kontrol_gerekli_uyelerde_daha_yuksek_fiyat": (
                sorted({u.oran for u in oyn_hepsi if u.olay.kesinlik != "kesin"
                        and (not en_yuksek or u.oran > en_yuksek.oran)}) or None),
            "oynanabilir_olmayan_uye_sayisi": sum(1 for u in uyeler if not _oynanabilir(u)),
            "yorum_siniri": "Fiyat farkı arbitraj ya da pozitif beklenen değer anlamına gelmez; "
                            "market marjı, limitler ve kural farkları olabilir. Olasılık bu modülde hesaplanmaz.",
        }
        sonuc.append(g)
    sonuc.sort(key=lambda g: (g["en_yuksek_fiyat"] is None, -len(g["uyeler"])))
    return sonuc


def bolumleme_denetimi(secenekler: list[Secenek]) -> list[dict]:
    """Seçenekleri ayrık ve kapsayıcı olan marketler için 1/oran toplamı (kitap marjı göstergesi)."""
    marketler: dict[tuple, list[Secenek]] = {}
    for s in secenekler:
        marketler.setdefault((s.market_kodu, s.cizgi), []).append(s)
    sonuc = []
    for (kod, c), ss in marketler.items():
        if any(s.olay is None for s in ss) or len(ss) < 2:
            continue
        toplam = np.zeros_like(H1, dtype=int)
        for s in ss:
            toplam += s.olay.maske.astype(int)
        ayrik = bool((toplam <= 1).all())
        kapsayici = bool((toplam >= 1).all())
        satir = {"market_kodu": kod, "cizgi": c, "market_adi": ss[0].market_adi, "secenek_sayisi": len(ss),
                 "ayrik": ayrik, "kapsayici": kapsayici}
        if ayrik and kapsayici and all(_oynanabilir(s) for s in ss):
            satir["ters_oran_toplami"] = round(sum(1.0 / s.oran for s in ss), 6)
            satir["not"] = "1/oran toplamı > 1 kitap marjını gösterir; olasılık değildir"
        elif ayrik and kapsayici:
            satir["ters_oran_toplami"] = None
            satir["not"] = "oynanabilir olmayan seçenek var; toplam hesaplanmadı"
        sonuc.append(satir)
    return sonuc


def alt_kume_tutarsizliklari(secenekler: list[Secenek]) -> list[dict]:
    """A ⊊ B iken fiyat(A) < fiyat(B): ima edilen eşikler kendi içinde tutarsız (yalnızca kesin ve oynanabilir)."""
    ss = [s for s in secenekler if s.olay is not None and s.olay.kesinlik == "kesin" and _oynanabilir(s)]
    sonuc = []
    for a in ss:
        for b in ss:
            if a is b or (a.market_kodu, a.cizgi) == (b.market_kodu, b.cizgi):
                continue
            ma, mb = a.olay.maske, b.olay.maske
            if ma.sum() >= mb.sum() or (ma & ~mb).any():
                continue  # a, b'nin kesin alt kümesi değil
            if a.oran < b.oran:
                sonuc.append({"alt_kume": a.ozet(), "ust_kume": b.ozet(),
                              "aciklama": "Daha dar olayın fiyatı daha geniş olayınkinden düşük.",
                              "yorum_siniri": "Arbitraj ya da +EV olarak nitelendirilmez; kural/kapsam, marj ya da "
                                              "farklı güncellenme zamanı nedeniyle olabilir. Kontrol edilmeli."})
    return sonuc


def mac_denetimi(mac: dict) -> dict:
    secenekler: list[Secenek] = []
    for m in mac.get("marketler", []):
        secenekler.extend(market_olaylari(m, mac.get("mac_kodu")))
    eslenen = [s for s in secenekler if s.olay is not None]
    nedenler: dict[str, int] = {}
    for s in secenekler:
        if s.olay is None:
            nedenler[s.eslenmeme_nedeni or "bilinmiyor"] = nedenler.get(s.eslenmeme_nedeni or "bilinmiyor", 0) + 1
    return {
        "mac_kodu": mac.get("mac_kodu"), "karsilasma": mac.get("karsilasma"), "turnuva": mac.get("turnuva"),
        "baslama_tr": mac.get("baslama_tr"),
        "sayilar": {"toplam_secenek": len(secenekler), "skor_uzayina_eslenen": len(eslenen),
                    "kesin": sum(1 for s in eslenen if s.olay.kesinlik == "kesin"),
                    "kontrol_gerekli": sum(1 for s in eslenen if s.olay.kesinlik != "kesin"),
                    "eslenmeyen": len(secenekler) - len(eslenen)},
        "eslenmeme_nedenleri": dict(sorted(nedenler.items(), key=lambda x: -x[1])),
        "esdegerlik_gruplari": esdegerlik_gruplari(secenekler),
        "bolumleme_denetimi": bolumleme_denetimi(secenekler),
        "alt_kume_fiyat_tutarsizliklari": alt_kume_tutarsizliklari(secenekler),
    }


def denetle(cekim: dict) -> dict:
    return {
        "surum": SURUM, "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kaynak_cekim": cekim.get("cekim"),
        "uyari": "Bu çıktı olasılık içermez. Başabaş eşiği gerçek olasılık değildir. Fiyat farkı arbitraj/+EV "
                 "olarak yorumlanmaz.",
        "izgara": {"devre_basina_takim_ust_siniri": UST, "nokta_sayisi": int(H1.size)},
        "maclar": [mac_denetimi(m) for m in cekim.get("maclar", [])],
    }


def rapor_md(sonuc: dict) -> str:
    s = [f"# Market eşdeğerliği ve fiyat tutarlılığı ({sonuc['surum']})", "",
         f"> {sonuc['uyari']}", "",
         f"Kapsam varsayımı: {KAPSAM_KAYNAGI}.", ""]
    for m in sonuc["maclar"]:
        n = m["sayilar"]
        s += [f"## {m['karsilasma']} ({m['mac_kodu']}, {m['turnuva']}, {m['baslama_tr']})", "",
              f"- Seçenek: {n['toplam_secenek']}; skor uzayına eşlenen {n['skor_uzayina_eslenen']} "
              f"(kesin {n['kesin']}, kontrol gerekli {n['kontrol_gerekli']}); eşlenmeyen {n['eslenmeyen']}.",
              f"- Çok marketli eşdeğer olay grubu: {len(m['esdegerlik_gruplari'])}; "
              f"alt küme fiyat tutarsızlığı: {len(m['alt_kume_fiyat_tutarsizliklari'])}.", "",
              "| Olay | Eşdeğerlik | Üyeler (market: seçenek = oran) | En yüksek (kesin, oynanabilir) |",
              "|---|---|---|---|"]
        for g in m["esdegerlik_gruplari"]:
            uy = "; ".join(f"{u['market_adi']}: {u['secenek_adi']} = {u['oran']}"
                           + ("" if u["oynanabilirlik"] == "oynanabilir" else f" [{u['oynanabilirlik']}]")
                           + (" [kontrol gerekli]" if u.get("kesinlik") != "kesin" else "")
                           for u in g["uyeler"])
            ey = g["en_yuksek_fiyat"]
            eys = f"{ey['oran']} ({ey['market_adi']}; başabaş eşiği {ey['basabas_esigi']:.4f})" if ey else "—"
            s.append(f"| {g['olay']} | {g['olay_esdegerligi']} | {uy} | {eys} |")
        if m["alt_kume_fiyat_tutarsizliklari"]:
            s += ["", "**Alt küme fiyat tutarsızlıkları** (arbitraj/+EV değildir; kontrol edilmeli):", ""]
            for t in m["alt_kume_fiyat_tutarsizliklari"][:40]:
                a, b = t["alt_kume"], t["ust_kume"]
                s.append(f"- {a['market_adi']}: {a['secenek_adi']} = {a['oran']}  ⊊  "
                         f"{b['market_adi']}: {b['secenek_adi']} = {b['oran']}")
        bol = [b for b in m["bolumleme_denetimi"] if b.get("ters_oran_toplami")]
        if bol:
            s += ["", "**Bölümleme (1/oran toplamı — marj göstergesi, olasılık değil):** "
                  + ", ".join(f"{b['market_adi']} {b['ters_oran_toplami']:.3f}" for b in bol[:30])]
        kapsamaz = [b for b in m["bolumleme_denetimi"] if not (b["ayrik"] and b["kapsayici"])]
        if kapsamaz:
            s += ["", "Ayrık/kapsayıcı olmayan marketler (listelenmeyen sonuç var ya da örtüşme): "
                  + ", ".join(f"{b['market_adi']} (ayrık={b['ayrik']}, kapsayıcı={b['kapsayici']})"
                              for b in kapsamaz)]
        s += ["", "Eşlenmeme nedenleri: " + "; ".join(f"{k}: {v}" for k, v in m["eslenmeme_nedenleri"].items()), ""]
    return "\n".join(s)


def main(argv=None):
    p = argparse.ArgumentParser(description="Market eşdeğerliği ve fiyat tutarlılığı denetimi (olasılık üretmez)")
    p.add_argument("--cekim", required=True, help="bulten_dogrulama.py disa-aktar çıktısı (JSON)")
    p.add_argument("--cikti", required=True, help="çıktı klasörü")
    a = p.parse_args(argv)
    cekim = json.loads(Path(a.cekim).read_text(encoding="utf-8"))
    sonuc = denetle(cekim)
    cik = Path(a.cikti)
    cik.mkdir(parents=True, exist_ok=True)
    (cik / "esdegerlik.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    (cik / "ESDEGERLIK_RAPORU.md").write_text(rapor_md(sonuc), encoding="utf-8")
    print(cik / "ESDEGERLIK_RAPORU.md")


if __name__ == "__main__":
    main()
