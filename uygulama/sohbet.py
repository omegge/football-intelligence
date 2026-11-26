"""Football Intelligence — Claude Code sohbet komutları.

Claude, kullanıcının Türkçe isteğine göre bu komutları çalıştırır ve çıktıyı (Markdown) sohbette sunar.
Yeni model ya da çekici yoktur: mevcut Nesine çekicisi, E2/E3 modelleri, dondurma, fiyat eşdeğerliği, haber katmanı
ve arşiv olduğu gibi çağrılır.

Proje kökünden:  PYTHONPATH=lib python3 -m uygulama.sohbet <komut> [seçenekler]

  bulten      [--gun YYYY-AA-GG] [--zorla]          Nesine bültenini çek (o TR günü 00:00–23:59) ve özetle
  maclar      [--gun] [--lig METIN] [--ara METIN] [--hepsi]   son başarılı bültenden oransız maç listesi
  tara        [--gun] [--min-oran X] [--maks-oran Y] [--market METIN] [--lig METIN] [--sinir 60]
                                                     keşif taraması; fiyat aralığı YALNIZCA kullanıcı isterse (oran
                                                     tarafsızlığı: oran eleme ölçütü değildir)
  mac         KOD|METIN                             maç dosyası: hazırlık, son 10 maç, bağımsız güç, araştırma durumu
  dondur      KOD                                   bağımsız olasılığı hesapla ve SHA-256 ile dondur
  karsilastir KOD [--zorla-cekim]                   dondurmadan SONRA güncel Nesine fiyatlarıyla karşılaştır
  marketler   KOD                                   maçın bütün Nesine marketleri (dondurmadan önce oransız)
  surpriz     KOD                                   sürpriz bağlamı: bağımsız favori, tarihsel taban oranları, pilot bulguları
  haber-kaydet DOSYA.json                           sohbette yapılan araştırmayı haber katmanına kaydet (doğrulama seviyeleriyle)
  performans                                        donmuş tahmin arşivi ve puanlama

MK-1: Oranlar yalnızca `tara`, `marketler` (dondurmadan sonra) ve `karsilastir` çıktısında görünür; hiçbiri modele girmez.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fi import is_akisi as I

from . import islemler as IS
from . import veri as V

EN_AZ_CEKIM_ARALIGI_DK = 10
GUNCEL_FIYAT_DK = 60          # karşılaştırma bundan eski fiyatla yapılmaz; yeni bülten çekilir
YENIDEN_DENEME_BEKLEME = (15, 45)      # yalnızca BAGLANTI hatasında; engelde hiç denenmez
DENENEBILIR = {"BAGLANTI"}


def _yaz(s: str = ""):
    print(s)


def _tr(iso: str | None) -> str:
    return datetime.fromisoformat(iso).astimezone(I.TR).strftime("%d.%m %H:%M") if iso else "—"


def _yuzde(p) -> str:
    return f"%{100 * p:.1f}".replace(".", ",") if isinstance(p, (int, float)) else str(p)


def _gun(g: str | None) -> str:
    return g or V.simdi_tr().date().isoformat()


def _bulten_ham(klasor: Path) -> dict:
    return json.loads((klasor / "mac_oncesi.json").read_text(encoding="utf-8"))


def _bulten_sec(gun: str) -> Path | None:
    """O günü tam kapsayan en yeni başarılı bülten."""
    return next((b for b in V.bultenler() if gun in V.bulten_gunleri(b)), None)


def _yas_dk(klasor: Path) -> float:
    k = (_bulten_ham(klasor).get("kaynak") or {}).get("cekim_utc")
    return (datetime.now(timezone.utc) - datetime.fromisoformat(k)).total_seconds() / 60 if k else 1e9


# ------------------------------------------------------------------------------------------------ bülten
def bulten(gun: str | None, zorla: bool = False) -> int:
    gun = _gun(gun)
    son = _bulten_sec(gun)
    if son and not zorla and _yas_dk(son) < EN_AZ_CEKIM_ARALIGI_DK:
        _yaz(f"> Son başarılı {gun} bülteni {_yas_dk(son):.0f} dakika önce çekildi ({son.name}); Nesine'ye yeni istek "
             f"gönderilmedi (en az {EN_AZ_CEKIM_ARALIGI_DK} dk aralık). Yine de yenilemek için `--zorla`.\n")
        return _bulten_ozeti(son, gun)
    denemeler = []
    for i in range(len(YENIDEN_DENEME_BEKLEME) + 1):
        try:
            r = IS.bulten_cek(gun)
            denemeler.append(f"deneme {i + 1}: başarılı")
            break
        except IS.BultenHatasi as e:
            denemeler.append(f"deneme {i + 1}: {', '.join(e.kodlar) or 'hata'}")
            if set(e.kodlar) - DENENEBILIR or not e.kodlar or i == len(YENIDEN_DENEME_BEKLEME):
                _yaz(f"**Bülten çekilemedi.** {'; '.join(denemeler)}.")
                if "ERISIM_ENGELI" in e.kodlar:
                    _yaz("Nesine erişimi engelledi. Engel aşılmaya çalışılmadı, yeniden denenmedi (proje kuralı 1).")
                _yaz(f"Ayrıntı: {e}")
                return 2
            time.sleep(YENIDEN_DENEME_BEKLEME[i])
    _yaz(f"Çekim: {'; '.join(denemeler)}.")
    return _bulten_ozeti(V.OUTPUT / r["klasor"], gun)


def _bulten_ozeti(klasor: Path, gun: str) -> int:
    b = _bulten_ham(klasor)
    k = b.get("kaynak") or {}
    dog = json.loads((klasor / "dogrulama.json").read_text(encoding="utf-8")) if (klasor / "dogrulama.json").exists() else {}
    maclar = [m for m in b.get("futbol", []) if m.get("baslama_tr")]
    gunun = V.gunun_maclari(klasor, gun)
    kod_gun = {m["kod"] for m in gunun}
    ms = [m for m in maclar if m["kod"] in kod_gun]
    market = sum(len(m.get("marketler") or []) for m in ms)
    secenek = sum(len(mk.get("secenekler") or []) for m in ms for mk in m.get("marketler") or [])
    oyn = sum(1 for m in ms for mk in m.get("marketler") or [] for s in mk.get("secenekler") or []
              if s.get("oynanabilirlik") == "oynanabilir")
    ozel = sum(1 for m in ms for mk in m.get("marketler") or [] if mk.get("maca_ozel"))
    _yaz(f"## Nesine bülteni — {gun} (Türkiye saati, yalnızca 00:00–23:59)")
    _yaz(f"- Klasör `{klasor.name}` · çekim {k.get('cekim_tr', '—')} ({_yas_dk(klasor):.0f} dk önce) · durum **{dog.get('durum', '—')}** "
         f"· ham SHA-256 `{(k.get('sha256') or '')[:12]}…`")
    _yaz(f"- **{len(ms)} maç · {market} market · {secenek} seçenek** (oynanabilir {oyn}; maça özel market {ozel})")
    disari = V.gun_disi_maclar(klasor, gun)
    if disari:
        _yaz(f"- Ertesi gün 00:00–03:00 arasındaki {disari} maç bu güne dahil edilmedi.")
    uyar = [x for x in dog.get("kayitlar", []) if x.get("seviye") in ("KRITIK", "UYARI")]
    for x in uyar[:6]:
        _yaz(f"- [{x['seviye']}] {x.get('kod')}: {x.get('mesaj', '')[:160]}")
    _yaz()
    _mac_tablosu(gunun, sinir=None, ozet_lig=True)
    return 0


def _mac_tablosu(maclar: list[dict], sinir: int | None = 60, ozet_lig: bool = False):
    donmus = {k["mac_id"] for k in V.donmus_tahminler()}
    simdi = datetime.now(timezone.utc)
    hz_onbellek: dict = {}
    if ozet_lig:
        ligler: dict = {}
        for m in maclar:
            ligler.setdefault(m["lig"] or "?", 0)
            ligler[m["lig"] or "?"] += 1
        _yaz("**Ligler:** " + " · ".join(f"{lig} ({n})" for lig, n in sorted(ligler.items(), key=lambda x: -x[1])[:25])
             + (" …" if len(ligler) > 25 else ""))
        _yaz()
    _yaz("| Saat (TR) | Kod | Lig | Maç | Bağımsız model |")
    _yaz("|---|---|---|---|---|")
    for m in maclar[:sinir] if sinir else maclar:
        if m["mac_id"] in donmus:
            d = "donmuş tahmin var"
        else:
            h = hz_onbellek.setdefault(m["mac_id"], V.hazirlik_ozeti(m))
            d = {"hazirlanabilir": f"hazırlanabilir ({'/'.join(h['modeller'])})",
                 "takim_onayi_gerekli": "takım adı onayı gerekli"}.get(h["durum"], "hesaplanamaz")
        if datetime.fromisoformat(m["baslama_tr"]) <= simdi:
            d += " · BAŞLADI"
        _yaz(f"| {_tr(m['baslama_tr'])} | {m['kod']} | {m['lig']} | {m['karsilasma']} | {d} |")
    if sinir and len(maclar) > sinir:
        _yaz(f"\n… {len(maclar) - sinir} maç daha (`--hepsi` ya da `--lig`/`--ara` ile süzün).")


def maclar(gun, lig, ara, hepsi) -> int:
    gun = _gun(gun)
    k = _bulten_sec(gun)
    if not k:
        _yaz(f"{gun} gününü tam kapsayan başarılı bülten yok. Önce `bulten --gun {gun}`.")
        return 1
    ms = V.gunun_maclari(k, gun)
    if lig:
        ms = [m for m in ms if lig.casefold() in (m["lig"] or "").casefold()]
    if ara:
        ms = [m for m in ms if ara.casefold() in (m["karsilasma"] or "").casefold()]
    _yaz(f"**{gun}** · bülten `{k.name}` ({_yas_dk(k):.0f} dk önce) · {len(ms)} maç\n")
    _mac_tablosu(ms, None if hepsi else 60)
    return 0


# ------------------------------------------------------------------------------------------------ keşif taraması
def tara(gun, min_oran, maks_oran, market, lig, sinir) -> int:
    gun = _gun(gun)
    k = _bulten_sec(gun)
    if not k:
        _yaz(f"{gun} için bülten yok. Önce `bulten --gun {gun}`.")
        return 1
    b = _bulten_ham(k)
    kodlar = {m["kod"] for m in V.gunun_maclari(k, gun)}
    simdi = datetime.now(timezone.utc)
    satir = []
    for m in b.get("futbol", []):
        if m["kod"] not in kodlar or datetime.fromisoformat(m["baslama_tr"]) <= simdi:
            continue
        if lig and lig.casefold() not in (m.get("lig") or "").casefold():
            continue
        for mk in m.get("marketler") or []:
            if market and market.casefold() not in (mk.get("market_adi") or "").casefold():
                continue
            for s in mk.get("secenekler") or []:
                o = s.get("oran")
                if s.get("oynanabilirlik") == "oynanabilir" and o and (min_oran or 0) <= o <= (maks_oran or 1e9):
                    satir.append((m, mk, s))
    maclar_: dict = {}
    for m, mk, s in satir:
        maclar_.setdefault(m["kod"], (m, []))[1].append((mk, s))
    aralik = (f"oran {min_oran or 1:g}–{maks_oran:g}" if maks_oran else f"oran ≥ {min_oran:g}") if (min_oran or maks_oran) \
        else "fiyat süzgeci yok"
    _yaz(f"## Bülten taraması — {gun} · {aralik}"
         + (f" · market “{market}”" if market else "") + (f" · lig “{lig}”" if lig else ""))
    _yaz(f"Bülten `{k.name}`, çekim {(b.get('kaynak') or {}).get('cekim_tr')} (**{_yas_dk(k):.0f} dk önce**; oranlar bu andaki "
         "fiyattır). Başlamış maçlar dışarıda.")
    _yaz("> Oran tarafsızlığı: oran bir eleme ölçütü değil, bilgi. Yüksek oran otomatik riskli, düşük oran otomatik güvenli "
         "değildir; olayın olasılığı ile fiyatın cazibesi ayrı değerlendirilir. Favori/sürpriz oranla belirlenmez (MK-1); her "
         "seçenek sportif kanıtla araştırılır. Sıralama saate göredir, orana göre değil.\n")
    _yaz(f"{len(satir)} seçenek, {len(maclar_)} maç.\n")
    _yaz("| Saat | Kod | Maç | Bağımsız model | Seçenek | Marketler / seçenekler |")
    _yaz("|---|---|---|---|---|---|")
    for kod, (m, lst) in sorted(maclar_.items(), key=lambda x: x[1][0]["baslama_tr"])[:sinir]:
        h = V.hazirlik_ozeti(V.oransiz_mac(m))
        d = {"hazirlanabilir": "hazırlanabilir", "takim_onayi_gerekli": "takım onayı gerekli"}.get(h["durum"], "hesaplanamaz")
        mks = {mk["market_adi"] for mk, _ in lst}
        ozel = sum(1 for mk in {id(mk): mk for mk, _ in lst}.values() if mk.get("maca_ozel"))
        ornek = (f"{len(mks)} market ({ozel} maça özel)" if not market else
                 "; ".join(f"{mk['market_adi']}: {s['secenek_adi']} {s['oran']:.2f}" for mk, s in lst[:6]))
        _yaz(f"| {_tr(m['baslama_tr'])} | {kod} | {m['karsilasma']} ({m['lig']}) | {d} | {len(lst)} | {ornek} |")
    if len(maclar_) > sinir:
        _yaz(f"\n… {len(maclar_) - sinir} maç daha.")
    return 0


# ------------------------------------------------------------------------------------------------ maç dosyası
def _mac_coz(ifade: str) -> tuple[dict, Path | None]:
    if ifade.isdigit():
        m, k = V.mac_bul(int(ifade))
        if m:
            return m, k
        raise SystemExit(f"Nesine {ifade} bültenlerde yok.")
    for k in V.bultenler():
        bul = [m for m in V.bulten_maclari(k) if ifade.casefold() in (m["karsilasma"] or "").casefold()]
        if len(bul) == 1:
            return bul[0], k
        if len(bul) > 1:
            raise SystemExit("Birden çok maç eşleşti: " + "; ".join(f"{m['kod']} {m['karsilasma']} {_tr(m['baslama_tr'])}"
                                                                     for m in bul[:10]))
    raise SystemExit(f"“{ifade}” bültenlerde bulunamadı.")


def _bagimsiz_guc(kaynak_lig: str, ad: str) -> str | None:
    """football-data.org anlık görüntüsünden sezon puan/maç ve gol farkı/maç (oransız, bağımsız)."""
    kod = V.FD_KODU.get(kaynak_lig)
    for k in V.guncel_klasorleri():
        y = k / f"{kod}.json"
        if y.exists():
            ms = [m for m in V._json(y) if m.get("durum") == "FINISHED" and ad in (m["ev"], m["dep"])]
            if not ms:
                return None
            p = gf = 0
            for m in ms:
                a, b = (m["ms_ev"], m["ms_dep"]) if m["ev"] == ad else (m["ms_dep"], m["ms_ev"])
                p += 3 if a > b else (1 if a == b else 0)
                gf += a - b
            return f"{len(ms)} maç, {p / len(ms):.2f} puan/maç, gol farkı {gf / len(ms):+.2f}/maç (anlık görüntü {k.name})"
    return None


def mac(ifade: str) -> int:
    from .sunucu import _takim_adlari
    m, k = _mac_coz(ifade)
    kod = m["kod"]
    d = V.donmus_bul(kod)
    hz = V.hazirlik_ozeti(m)
    _yaz(f"## {m['karsilasma']} — {m['lig']} · {_tr(m['baslama_tr'])} TR · Nesine {kod}")
    _yaz(f"Bülten `{k.name if k else '—'}` · {m.get('market_sayisi', 0)} market")
    if datetime.fromisoformat(m["baslama_tr"]) <= datetime.now(timezone.utc):
        _yaz("**Maç başladı:** maç öncesi analiz ve dondurma yapılamaz; canlı skor/dakika/kırmızı kart web araştırmasıyla "
             "doğrulanmalı (bülten canlı alanları doğrulanmamış adaydır).")
    _yaz("\n### Bağımsız model durumu")
    if d and not d.get("hata"):
        t = d["tahmin"]
        _yaz(f"- **Donmuş tahmin var:** {d['dondurma_utc']} UTC · SHA `{d['sha256'][:12]}…` · model {t.get('model_adi')} · "
             f"veri kesimi {t.get('veri_kesimi')}")
    elif d:
        _yaz(f"- Donmuş tahmin BOZUK: {d['hata']}")
    else:
        _yaz(f"- {hz['durum']}: {hz['neden']} (lig: {hz['kaynak_lig']}; modeller: {', '.join(hz['modeller']) or '—'})")
    if hz.get("kaynak_lig") and hz["modeller"]:
        kap, _ = I.kapsam_yukle()
        mod = kap["modeller"][hz["modeller"][0]]
        ic = [a for a, r in mod["marketler"].items() if r["kapsamda"]]
        _yaz(f"- Kalibre marketler ({hz['modeller'][0]}, {len(ic)}): {', '.join(ic)}")
        _yaz("- Diğer bütün marketler: **hesaplanamaz** (yüzde verilmez).")
    adlar = _takim_adlari(m, d if d and not d.get("hata") else None, hz)
    if adlar and hz.get("kaynak_lig"):
        _yaz("\n### Bağımsız güç ve son 10 maç (football-data.org; oransız)")
        for t_, et in (("ev", m["ev"]), ("dep", m["deplasman"])):
            if t_ not in adlar:
                _yaz(f"- {et}: takım eşlemesi kesin değil (veri yok)")
                continue
            g = _bagimsiz_guc(hz["kaynak_lig"], adlar[t_])
            s = V.son_maclar(hz["kaynak_lig"], adlar[t_], 10)
            o = s.get("ozet") or {}
            _yaz(f"- **{et}** ({adlar[t_]}): sezon {g or 'veri yok'}")
            if s.get("satirlar"):
                _yaz(f"  - Son {s['mac']}: {o['G']}G {o['B']}B {o['M']}M, gol {o['atilan']}–{o['yenilen']}, KG {o['kg']}/{s['mac']}, "
                     f"2,5 Üst {o['ust25']}/{s['mac']}: " + ", ".join(f"{r['saha']} {r['rakip']} {r['skor']}" for r in s["satirlar"][:10]))
    else:
        _yaz("\n### Bağımsız güç\n- Onaylı lig/takım eşlemesi yok: kaynak verisi yok. Form ve güç web araştırmasıyla, kaynaklı olarak toplanmalı.")
    hr = V.haber_raporlari(kod)
    _yaz("\n### Kayıtlı haber araştırması")
    if hr:
        tz = V.haber_tazeligi(hr[0]["rapor"], m["baslama_tr"])
        _yaz(f"- {len(hr)} sürüm; en yenisi `{hr[0]['surum']}`, {tz['yas_saat']} saat önce ({', '.join(tz['turlar'])}); şu anki tur "
             f"{tz['simdiki_tur']} → {'güncel' if tz['guncel'] else '**GÜNCEL DEĞİL**: yeni araştırma gerekir'}")
    else:
        _yaz("- Yok. Haber araştırması gerekir (haber-arastir becerisi).")
    return 0


# ------------------------------------------------------------------------------------------------ dondurma
def dondur(ifade: str) -> int:
    m, _ = _mac_coz(ifade)
    try:
        r = IS.dondur_mac(m["kod"])
    except IS.IslemHatasi as e:
        _yaz(f"**Dondurulmadı:** {e}")
        return 1
    if not r.get("donduruldu"):
        _yaz("**Bağımsız tahmin hesaplanamaz — dondurulmadı.**")
        for n in r.get("nedenler") or []:
            _yaz(f"- {n}")
        return 1
    return _donmus_yaz(m["kod"])


def _donmus_yaz(kod: int) -> int:
    d = V.donmus_bul(kod)
    t = d["tahmin"]
    _yaz(f"## Donmuş bağımsız tahmin — {d['karsilasma']}")
    _yaz(f"- Dondurma {d['dondurma_utc']} UTC · SHA-256 `{d['sha256']}` · model **{t['model_adi']}** · veri kesimi "
         f"{t['veri_kesimi']} · eğitim {t.get('egitim_mac_sayisi')} maç")
    e3 = t.get("e3_duzeltmesi")
    _yaz(f"- λ ev {t['lambda_ev']:.3f} · λ dep {t['lambda_dep']:.3f}"
         + (f" · E3 γ {e3['gamma']} δ {e3['delta']} ({e3['pencere_mac']} maçlık pencere, son kayıt {e3.get('pencere_son')})" if e3 else ""))
    _yaz("- Oranlar bu hesaba girmedi (girdi denetimi: oransiz_mi). Haber ve yorumlar da girmedi.\n")
    _yaz("| Market | Bağımsız olasılık |")
    _yaz("|---|---|")
    for a, p in t["olasiliklar"].items():
        _yaz(f"| {a} | {_yuzde(p)} |")
    _yaz(f"\nHesaplanamaz: {len(t.get('hesaplanamaz_pazarlar') or {})} model marketi + bütün özel marketler (korner, kart, oyuncu, "
         "devre, handikap çizgileri vb.). Bunlara yüzde verilmez.")
    return 0


# ------------------------------------------------------------------------------------------------ fiyat karşılaştırması
def karsilastir(ifade: str, zorla_cekim: bool = False) -> int:
    m, _ = _mac_coz(ifade)
    kod = m["kod"]
    d = V.donmus_bul(kod)
    if not d or d.get("hata"):
        _yaz("**Karşılaştırma kilitli:** önce bağımsız tahmin dondurulmalı (MK-1)." if not d else f"Donmuş tahmin bozuk: {d['hata']}")
        return 1
    gun = datetime.fromisoformat(m["baslama_tr"]).astimezone(I.TR).date().isoformat()
    dond = datetime.fromisoformat(d["dondurma_utc"])

    def en_yeni():           # maçı içeren, dondurmadan sonra çekilmiş en yeni başarılı bülten
        for b in V.bultenler():
            c = (_bulten_ham(b).get("kaynak") or {}).get("cekim_utc")
            if c and datetime.fromisoformat(c) > dond and any(x["kod"] == kod for x in V.bulten_maclari(b)):
                return b
        return None
    son = en_yeni()
    if zorla_cekim or son is None or _yas_dk(son) > GUNCEL_FIYAT_DK:
        _yaz(f"Dondurmadan sonra çekilmiş ve {GUNCEL_FIYAT_DK} dakikadan yeni bülten yok; Nesine bülteni çekiliyor…")
        if bulten(gun, zorla=True) != 0:
            return 2
        _yaz()
        son = en_yeni()
    if son and not (son / f"fiyat_karsilastirma_{kod}.json").exists():
        try:
            IS.fiyat_karsilastir_mac(kod)          # en yeni dondurma sonrası bültenle
        except IS.IslemHatasi as e:
            if "zaten var" not in str(e):
                _yaz(f"**Karşılaştırma yapılmadı:** {e}")
                return 1
    fk = V.fiyat_karsilastirmasi(kod, d)
    if fk["durum"] != "var":
        _yaz(f"Karşılaştırma yok: {fk.get('neden')}")
        return 1
    klasor = V.OUTPUT / fk["klasor"]
    _yaz(f"## Fiyat karşılaştırması — {d['karsilasma']}")
    _yaz(f"- Donmuş tahmin {d['dondurma_utc']} UTC (SHA `{d['sha256'][:12]}…`) → bülten `{fk['klasor']}`, çekim "
         f"{_bulten_ham(klasor)['kaynak'].get('cekim_tr')} (**{_yas_dk(klasor):.0f} dk önce**)")
    _yaz("- Başabaş = 1/oran (olasılık değildir). EV = p × oran − 1 (bilgi; öneri değil). Pozitif EV satırları avantaj "
         "sayılmaz: “model–piyasa ayrışması · doğrulama gerekli”.\n")
    _yaz("| Market | Seçenek | Oran | Bağımsız p | Başabaş | EV | Değerlendirme |")
    _yaz("|---|---|---|---|---|---|---|")
    for s in fk["satirlar"]:
        if not s.get("model_marketi"):
            continue
        ev = s.get("beklenen_deger")
        deg = ("model–piyasa ayrışması · doğrulama gerekli" if ev is not None and ev > 0 else
               "fiyat modelin üstünde değil" if ev is not None else s.get("not") or "")
        _yaz(f"| {s['market_adi']} | {s['secenek_adi']} | {s.get('oran') or '—'} | {_yuzde(s['bagimsiz_olasilik'])} | "
             f"{_yuzde(s['basabas_esigi']) if s.get('basabas_esigi') else '—'} | {f'{ev:+.3f}' if ev is not None else '—'} | {deg} |")
    ey = V.en_yuksek_fiyatlar(fk)
    if ey:
        _yaz("\n**Eşdeğer seçeneklerde en yüksek fiyat** (aynı olay, farklı Nesine marketleri; fiyat oranı olasılık değildir):\n")
        _yaz("| Olay | En yüksek fiyatlı seçenek | Oran | Kesin/üye | Fark |")
        _yaz("|---|---|---|---|---|")
        for g in ey[:15]:
            _yaz(f"| {g['olay']} | {g['en_yuksek']['market_adi']} — {g['en_yuksek']['secenek_adi']} | {g['en_yuksek']['oran']} | "
                 f"{g['kesin_oynanabilir']}/{g['uye_sayisi']} | {g['fark']} |")
    sy = fk["esdegerlik"].get("sayilar", {})
    _yaz(f"\nSeçenek {sy.get('toplam_secenek')} · skor uzayına eşlenen {sy.get('skor_uzayina_eslenen')} · eşlenmeyen "
         f"{sy.get('eslenmeyen')} (korner, kart, oyuncu vb.: model yok, **hesaplanamaz**) · alt küme fiyat tutarsızlığı "
         f"{len(fk['esdegerlik'].get('alt_kume_fiyat_tutarsizliklari') or [])}. Bütün marketler: `marketler {kod}`.")
    return 0


def marketler(ifade: str) -> int:
    m, _ = _mac_coz(ifade)
    kod = m["kod"]
    d = V.donmus_bul(kod)
    donmus = bool(d and not d.get("hata"))
    hz = V.hazirlik_ozeti(m)
    model_yok = hz["durum"] != "hazirlanabilir" and not d
    acik = donmus or model_yok
    k = next((b for b in V.bultenler() if any(x["kod"] == kod for x in V.bulten_maclari(b))), None)
    ham = next(x for x in _bulten_ham(k)["futbol"] if x["kod"] == kod)
    n_sec = sum(len(mk.get("secenekler") or []) for mk in ham["marketler"])
    _yaz(f"## {ham['karsilasma']} — {len(ham['marketler'])} Nesine marketi, {n_sec} seçenek (bülten `{k.name}`, çekim "
         f"{_bulten_ham(k)['kaynak'].get('cekim_tr')}, **{_yas_dk(k):.0f} dk önce**)")
    if donmus:
        _yaz("> Bağımsız tahmin donmuş; oranlar açık. Kapsamdaki marketlerin olasılıkları: `karsilastir`.\n")
    elif model_yok:
        _yaz(f"> Bu maç için bağımsız model yok ({hz['neden']}). Oranlar yalnızca KEŞİF içindir: şirket marjı içerir, olasılık "
             "değildir; hiçbir hesaba girmez. Her seçenek sportif kanıtla (destekleyen/karşıt) değerlendirilir; yüzde ve EV verilmez.\n")
    else:
        _yaz("> Bağımsız model hazırlanabilir ama tahmin henüz donmadı: oranlar GÖSTERİLMİYOR (MK-1 sırası). Önce `dondur`, "
             "sonra yeniden `marketler`.\n")
    for mk in ham["marketler"]:
        cizgi = f" [{mk['ozel_deger']:g}]" if mk.get("ozel_deger") not in (None, 0, 0.0) else ""
        sec = ", ".join(f"{s['secenek_adi']}" + (f" {s['oran']:.2f}" if acik and s.get("oran") else "")
                        + ("" if s.get("oynanabilirlik") == "oynanabilir" else f" ({s.get('oynanabilirlik')})")
                        for s in mk.get("secenekler") or [])
        _yaz(f"- **{mk['market_adi']}**{cizgi}{' (maça özel)' if mk.get('maca_ozel') else ''}: {sec}")
    return 0


# ------------------------------------------------------------------------------------------------ sürpriz bağlamı
def surpriz(ifade: str) -> int:
    m, _ = _mac_coz(ifade)
    d = V.donmus_bul(m["kod"])
    _yaz(f"## Sürpriz bağlamı — {m['karsilasma']}")
    s = V.surpriz_arastirmasi()
    havuz_yol = V.OUTPUT / "arastirma" / "surpriz_pilot_v1" / "havuz.json"
    if d and not d.get("hata"):
        p = d["tahmin"]["olasiliklar"]
        if "MS_1" in p and "MS_2" in p:
            taraf, pf = ("ev", p["MS_1"]) if p["MS_1"] >= p["MS_2"] else ("dep", p["MS_2"])
            kat = None if pf < 0.5 else "50-60" if pf < 0.6 else "60-70" if pf < 0.7 else "70-80" if pf < 0.8 else "80+"
            ad = m["ev"] if taraf == "ev" else m["deplasman"]
            _yaz(f"- **Bağımsız favori:** {ad} ({taraf}), P(kazanır) {_yuzde(pf)} — model {d['tahmin']['model_adi']} (oransız).")
            if kat and havuz_yol.exists():
                h = [x for x in json.loads(havuz_yol.read_text()) if x["kategori"] == kat]
                b_ = sum(x["etiket"] == "berabere" for x in h) / len(h)
                l_ = sum(x["etiket"] == "favori_kaybetti" for x in h) / len(h)
                _yaz(f"- Tarihsel taban (büyük 5 lig 2022–26, {len(h)} maç, aynı kategori {kat}): favori berabere {_yuzde(b_)}, "
                     f"kaybetti {_yuzde(l_)}. Kalibre bir modelde sürprizlerin çoğu bu oranlarda, rastgele gerçekleşir.")
            elif not kat:
                _yaz("- İki tarafın kazanma olasılığı da %50'nin altında: belirgin bağımsız favori yok.")
        else:
            _yaz("- Donmuş tahminde MS 1/2 kalibre değil (hesaplanamaz): bağımsız favori yüzdesi verilemez.")
    else:
        _yaz("- Donmuş bağımsız tahmin yok: favori oranla belirlenmez (MK-1). Önce `dondur` ya da bağımsız sezon verisi (`mac`).")
    k = s.get("kodlama") or {}
    if k.get("sinyal_sikligi"):
        _yaz("\n**10+10 sürpriz pilotu (keşif, kör değil; kanıtlanmış sinyal YOK):**")
        for t in k["sinyal_sikligi"]:
            _yaz(f"- {t['sinyal']}: sürprizlerde {t['surpriz']}/10, kontrollerde {t['kontrol_yanlis_alarm']}/10")
        _yaz("- Okuma: hiçbir sinyal iki grubu ayırmadı; “favoride kilit eksik” kontrollerde daha sıktı. Bu sinyaller olasılığa eklenmez; "
             "yalnızca araştırma kontrol listesidir. Maç içi olaylar (kırmızı kart, VAR, penaltı) sürprizlerin 3/10'unu belirledi ve önceden bilinemez.")
    return 0


# ------------------------------------------------------------------------------------------------ haber kaydı
def haber_kaydet(dosya: str) -> int:
    from fi.haber import genis as G
    g = json.loads(Path(dosya).read_text(encoding="utf-8"))
    m, _ = _mac_coz(str(g["kod"]))
    mac_ = {"mac_id": m["mac_id"], "karsilasma": m["karsilasma"], "lig": m["lig"],
            "baslama_utc": datetime.fromisoformat(m["baslama_tr"]).astimezone(timezone.utc).isoformat(timespec="seconds"),
            "baslama_tr": m["baslama_tr"]}
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tur = G.arastirma_turu(mac_["baslama_utc"], datetime.now(timezone.utc))
    for x in g.get("aramalar") or []:          # zaman damgası komut tarafından verilir; elle yazılan gelecek zaman reddedilir
        if not x.get("utc") or datetime.fromisoformat(x["utc"]) > datetime.now(timezone.utc):
            x["utc"] = simdi
        x.setdefault("tur", tur)
    iddialar = [G.Iddia(**{"mac_id": m["mac_id"], "arastirma_utc": simdi, "tur": tur, **i}) for i in g.get("iddialar", [])]
    gorusler = [G.DisGorus(**{"mac_id": m["mac_id"], "arastirma_utc": simdi, **x}) for x in g.get("gorusler", [])]
    d = V.donmus_bul(m["kod"])
    model = d if d and not d.get("hata") else {"durum": "hesaplanamaz", "nedenler": ["donmuş bağımsız tahmin yok"]}
    ad = re.sub(r"[^a-z0-9]+", "_", m["karsilasma"].casefold()).strip("_")[:40]
    hedef = V.OUTPUT / "arastirma" / "genis_pilot" / f"{ad}_{m['kod']}_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    z = G.kaydet(mac_, iddialar, gorusler, hedef, g.get("aramalar"))
    r = G.mac_raporu(mac_, iddialar, gorusler, model, aramalar=g.get("aramalar"), yorumlar=g.get("yorumlar"))
    (hedef / "rapor.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (hedef / "RAPOR.md").write_text(G.rapor_md(r), encoding="utf-8")
    deg = G.iddia_degerlendir(iddialar, mac_["baslama_utc"])
    from collections import Counter
    _yaz(f"Kaydedildi: `{hedef.relative_to(V.KOK) if hedef.is_relative_to(V.KOK) else hedef}` · tur {tur} · SHA `{z['sha256'][:12]}…`")
    _yaz(f"- {len(iddialar)} iddia → {len(deg)} grup: " + ", ".join(f"{k} {v}" for k, v in Counter(x['dogrulama'] for x in deg).items()))
    _yaz(f"- {len(gorusler)} dış görüş (karantina: model girdisi değil)")
    return 0


# ------------------------------------------------------------------------------------------------ performans
def performans() -> int:
    a = V.arsiv()
    puanli = [r for r in a if r.get("puan")]
    _yaz(f"## Tahmin arşivi — {len(a)} donmuş tahmin, {len(puanli)} puanlandı")
    _yaz("| Maç | Başlama | Dondurma (UTC) | Bütünlük | Sonuç | Market | Ort. log-kayıp | Ort. Brier |")
    _yaz("|---|---|---|---|---|---|---|---|")
    for r in a:
        p = r.get("puan") or {}
        _yaz(f"| {r.get('karsilasma') or r['mac_id']} | {_tr(r['baslama_tr'])} | {r['dondurma_utc']} | {r['butunluk']} | "
             f"{r.get('sonuc')} | {p.get('market', '—')} | {p.get('ort_log_loss', '—')} | {p.get('ort_brier', '—')} |")
    if len(puanli) < 100:
        _yaz(f"\nİleriye dönük değerlendirme için en az 100 puanlanmış maç gerekir; şu an {len(puanli)}. Sonuçlar football-data.org "
             "anlık görüntüsünden gelir (güncel veri için `PYTHONPATH=lib python3 -m fi.kaynaklar.guncel guncelle`).")
    return 0


def main(argv=None) -> int:
    a = argparse.ArgumentParser(prog="uygulama.sohbet", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = a.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("bulten"); p.add_argument("--gun"); p.add_argument("--zorla", action="store_true")
    p = alt.add_parser("maclar"); p.add_argument("--gun"); p.add_argument("--lig"); p.add_argument("--ara"); p.add_argument("--hepsi", action="store_true")
    p = alt.add_parser("tara"); p.add_argument("--gun"); p.add_argument("--min-oran", type=float)
    p.add_argument("--maks-oran", type=float); p.add_argument("--market"); p.add_argument("--lig")
    p.add_argument("--sinir", type=int, default=40)
    for ad in ("mac", "dondur", "marketler", "surpriz"):
        alt.add_parser(ad).add_argument("ifade")
    p = alt.add_parser("karsilastir"); p.add_argument("ifade"); p.add_argument("--zorla-cekim", action="store_true")
    alt.add_parser("haber-kaydet").add_argument("dosya")
    alt.add_parser("performans")
    x = a.parse_args(argv)
    return {"bulten": lambda: bulten(x.gun, x.zorla), "maclar": lambda: maclar(x.gun, x.lig, x.ara, x.hepsi),
            "tara": lambda: tara(x.gun, x.min_oran, x.maks_oran, x.market, x.lig, x.sinir),
            "mac": lambda: mac(x.ifade), "dondur": lambda: dondur(x.ifade), "marketler": lambda: marketler(x.ifade),
            "surpriz": lambda: surpriz(x.ifade), "karsilastir": lambda: karsilastir(x.ifade, x.zorla_cekim),
            "haber-kaydet": lambda: haber_kaydet(x.dosya), "performans": performans}[x.komut]()


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)      # çıktı kesildiğinde (| head) sessiz çık
    sys.exit(main())
