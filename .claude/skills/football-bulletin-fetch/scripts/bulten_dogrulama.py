#!/usr/bin/env python3
"""Bülten çekme DOĞRULAMASI: seçili maçların ayrıntılı dışa aktarımı ve referans bültenle karşılaştırma.

Bu araç bahis tahmini yapmaz, olasılık üretmez, oranları değiştirmez. Ham veri (ham/mac_oncesi.json) korunur;
dışa aktarım her seçenek için hem işlenmiş alanları hem ham alanları (N, NO, ON, O) taşır ve ikisini çapraz
denetler. Hiçbir alan sessizce düzeltilmez: tutarsızlıklar 'denetim' bölümünde raporlanır.

Kullanım (proje kökünden):
  python3 bulten_dogrulama.py disa-aktar --bulten output/bulten_YYYYAAGG_SSDDss --mac 3326567 --mac 3326548 [--cikti DOSYA]
  python3 bulten_dogrulama.py karsilastir --cekim DISA_AKTARIM.json --referans REF.json|REF.csv [--cikti DOSYA]

Referans biçimi (JSON listesi ya da CSV; sütun adları büyük/küçük harf duyarsız):
  mac_kodu | mac            : Nesine maç kodu ya da "Ev - Deplasman"
  market_kodu (isteğe bağlı): Nesine market tip kodu (MTID)
  market_adi                : tam market adı (ör. "Handikaplı Maç Sonucu (1:0)")
  cizgi (isteğe bağlı)      : çizgi/handikap değeri, işaretiyle (ör. -1, 2.5)
  secenek                   : seçenek adı (ör. "1", "Alt", "Bailey, Leon 2+")
  oran                      : ondalık oran; kapalıysa "-" ya da boş
  cekim_zamani (isteğe bağlı): ISO tarih-saat (referansın alındığı an)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path

OYUNCU_MTID = {701: "gol", 702: "ilk_gol", 709: "kart", 712: "asist", 714: "isabetli_sut", 740: "sut"}
ADAY_DOSYASI = Path(__file__).resolve().parent.parent / "data" / "market_aday_eslemeleri.json"


def aday_eslemeleri(yol: Path = ADAY_DOSYASI) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))["adaylar"] if Path(yol).exists() else {}


def _cizgi_metni(c) -> str:
    return f"{c:g}".replace(".", ",") if isinstance(c, (int, float)) else str(c)


def karsilastirma_adi(ad: str | None) -> str | None:
    """Karşılaştırma anahtarı: aksan/Türkçe karakter katlanmış, küçük harf (İlhan Fakılı ≡ Ilhan Fakili). Görüntülenmez."""
    if not ad:
        return None
    t = ad.replace("ı", "i").replace("İ", "I")
    return _sade(t)
ARAYUZ_DOGRULAMA_DOSYASI = Path(__file__).resolve().parent.parent / "data" / "market_arayuz_dogrulamalari.json"


def arayuz_dogrulamalari(yol: Path = ARAYUZ_DOGRULAMA_DOSYASI) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))["kodlar"] if Path(yol).exists() else {}


def periyot(market_adi: str | None, adsiz: bool = False) -> str:
    """Market adından değerlendirme periyodu (çıkarım; kaynak alanı 'market_adi'). Adsız market: 'bilinmiyor'."""
    if adsiz or not market_adi:
        return "bilinmiyor"
    a = market_adi
    if "Uzt." in a:
        return "uzatma_dahil"
    iy = bool(re.search(r"1\. ?Yarı|1\.Y|İlk Yarı|İY ", a))
    ikinci = bool(re.search(r"2\. ?Yarı|2\.Y", a))
    coklu = bool(re.search(r"İki Yarı|Yarıda|Yarıyı|Hangi Yarı|Gol Olacak Yarı", a)) or (iy and ("Maç" in a or ikinci))
    if coklu:
        return "coklu_periyot"
    if iy:
        return "ilk_yari"
    if ikinci:
        return "ikinci_yari"
    return "mac"


def dogrulama_seviyesi(market_kodu, cizgi, ad_kaynagi: str, aday: dict | None, dogrulamalar: dict) -> str:
    """arayuz_referansi > arayuz_kodu_farkli_cizgi > sozluk > bulten_adi > aday > adsiz."""
    if ad_kaynagi == "yok":
        return "aday" if aday else "adsiz"
    d = dogrulamalar.get(str(market_kodu))
    if d and cizgi in d["cizgiler"]:
        return "arayuz_referansi"
    if d:
        return "arayuz_kodu_farkli_cizgi"
    return "sozluk" if ad_kaynagi == "sozluk" else "bulten_adi"


HANDIKAP_AD = re.compile(r"\((\d+(?:[.,]\d+)?):(\d+(?:[.,]\d+)?)\)")


# ---------------------------------------------------------------- yardımcılar
def _sade(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+:.,/& -]", " ", s)).strip()


def oyuncu_ayir(ad: str) -> tuple[str | None, int | None]:
    """'Bailey, Leon 2+' → ('Leon Bailey', 2); 'Leon Bailey' → ('Leon Bailey', None). Biçim farkı korunur, ad değişmez."""
    m = re.match(r"^(.*?)\s+(\d+)\+$", ad.strip())
    isim, esik = (m.group(1), int(m.group(2))) if m else (ad.strip(), None)
    if "," in isim:
        soyad, ad_ = [p.strip() for p in isim.split(",", 1)]
        isim = f"{ad_} {soyad}"
    return (isim or None), esik


def handikap_bilgisi(market_adi: str, cizgi) -> dict | None:
    """Ad '(a:b)' içeriyorsa başlangıç avantajı. a>0 → ev sahibi önde başlar; b>0 → deplasman önde başlar.
    Çizgi işaretiyle tutarlılık ayrıca denetlenir (Nesine kuralı: çizgi > 0 ev sahibi lehine)."""
    m = HANDIKAP_AD.search(market_adi or "")
    if not m:
        return None
    a, b = (float(x.replace(",", ".")) for x in m.groups())
    uygulanan = "ev" if a > 0 else ("deplasman" if b > 0 else "yok")
    beklenen = "ev" if (cizgi or 0) > 0 else ("deplasman" if (cizgi or 0) < 0 else "yok")
    return {"ad_baslangici": f"{m.group(1)}:{m.group(2)}", "avantajli_takim": uygulanan, "cizgi": cizgi,
            "cizgi_isaretiyle_tutarli": uygulanan == beklenen or (uygulanan == "deplasman" and cizgi is not None and cizgi == 0)}


# ---------------------------------------------------------------- dışa aktarım
def disa_aktar(bulten_klasoru: Path, mac_kodlari: list[int]) -> dict:
    bk = Path(bulten_klasoru)
    ham = json.loads((bk / "ham" / "mac_oncesi.json").read_text(encoding="utf-8"))
    norm = json.loads((bk / "mac_oncesi.json").read_text(encoding="utf-8"))
    kaynak = json.loads((bk / "kaynak.json").read_text(encoding="utf-8"))
    ham_ea = {e.get("C"): e for e in (ham.get("sg") or {}).get("EA", [])}
    adaylar = aday_eslemeleri()
    dogrulamalar = arayuz_dogrulamalari()
    norm_ea = {e["kod"]: e for e in norm["futbol"]}
    km = kaynak["kaynaklar"]["mac_oncesi"]
    out = {"cekim": {"url": km["url"], "cekim_utc": km["cekim_utc"], "cekim_tr": km["cekim_tr"],
                     "ham_sha256": km["sha256"], "http": km["http_durumu"], "sozluk": kaynak.get("sozluk"),
                     "not": "oranlar ham JSON'daki değerlerle aynıdır (yuvarlama yok); kapalı seçenek ham değeri 1.0"},
           "maclar": []}
    for kod in mac_kodlari:
        he, ne = ham_ea.get(kod), norm_ea.get(kod)
        if he is None or ne is None:
            out["maclar"].append({"mac_kodu": kod, "durum": "bültende yok", "ham_var": he is not None, "isleme_var": ne is not None})
            continue
        ham_ma = {m["ID"]: m for m in he.get("MA", [])}
        marketler, denetim = [], defaultdict(list)
        anahtar_say = Counter()
        for m in ne["marketler"]:
            hm = ham_ma.get(m["market_json_id"])
            if hm is None:
                denetim["islenmis_ama_hamda_yok"].append(m["market_json_id"])
                continue
            ham_oca = {o["N"]: o for o in hm.get("OCA", [])}
            secenekler = []
            for s in m["secenekler"]:
                ho = ham_oca.get(s["secenek_no"])
                if ho is None:
                    denetim["secenek_hamda_yok"].append([m["market_json_id"], s["secenek_no"]])
                    continue
                if s["oran_ham"] != ho.get("O"):
                    denetim["oran_ham_uyusmazligi"].append([m["market_json_id"], s["secenek_no"], s["oran_ham"], ho.get("O")])
                kayit = {"secenek_no": s["secenek_no"], "secenek_adi": s["secenek_adi"],
                         "secenek_adi_kaynagi": s["secenek_adi_kaynagi"], "oran": ho.get("O"),
                         "durum": "kapali" if s["oran_durumu"] == "kapali" else ("aktif" if s["oynanabilirlik"] == "oynanabilir" else s["oynanabilirlik"]),
                         "oran_durumu": s["oran_durumu"], "oynanabilirlik": s["oynanabilirlik"],
                         "gosterim": "-" if s["oran_durumu"] == "kapali" else None,
                         "ham": {k: ho[k] for k in ("N", "NO", "ON", "O") if k in ho}}
                if m["market_tip_id"] in OYUNCU_MTID:
                    isim, esik = oyuncu_ayir(s["secenek_adi"] or "")
                    kayit["oyuncu"] = {"ham_ad": s["secenek_adi"], "ad": isim, "ad_karsilastirma": karsilastirma_adi(isim),
                                       "esik": esik, "istatistik": OYUNCU_MTID[m["market_tip_id"]]}
                secenekler.append(kayit)
                anahtar_say[(m["market_tip_id"], hm.get("SOV"), s["secenek_no"])] += 1
            for n in ham_oca:
                if n not in {s["secenek_no"] for s in m["secenekler"]}:
                    denetim["hamda_var_islenmiste_yok"].append([m["market_json_id"], n])
            hk = handikap_bilgisi(m["market_adi"], hm.get("SOV"))
            ad_ = adaylar.get(str(m["market_tip_id"])) if m["market_adi_kaynagi"] == "yok" else None
            aday = None if ad_ is None else {"aday_adi": ad_["aday_ad_sablonu"].replace("{cizgi}", _cizgi_metni(hm.get("SOV"))),
                                             "aday_secenekler": ad_.get("aday_secenekler"), "durum": ad_["durum"],
                                             "dogrulama_sayisi": len(ad_.get("kanitlar", [])),
                                             "not": "market_adi değiştirilmedi; aday kesinleşmedi"}
            marketler.append({"market_id": m["market_json_id"], "market_kodu": m["market_tip_id"], "market_no": m["market_no"],
                              "market_adi": m["market_adi"], "market_adi_kaynagi": m["market_adi_kaynagi"],
                              "sozluk_adi": m["sozluk_adi"], "cizgi": hm.get("SOV"), "maca_ozel": m["maca_ozel"],
                              "market_durumu_MS": hm.get("MS"), "market_mbs": hm.get("MBS"),
                              "aktif": hm.get("MS") == 1, "handikap": hk, "adsiz": m["market_adi_kaynagi"] == "yok",
                              "aday": aday,
                              "periyot": periyot(m["market_adi"], m["market_adi_kaynagi"] == "yok"),
                              "periyot_kaynagi": "market_adi (çıkarım)",
                              "dogrulama_seviyesi": dogrulama_seviyesi(m["market_tip_id"], hm.get("SOV"),
                                                                       m["market_adi_kaynagi"], aday, dogrulamalar),
                              "secenekler": secenekler,
                              "ham_ek_alanlar": {k: hm[k] for k in ("MN", "INM", "HM", "BM", "VT") if k in hm}})
            if m["market_adi_kaynagi"] == "yok":
                denetim["sozlukte_olmayan_market"].append({"market_kodu": m["market_tip_id"], "cizgi": hm.get("SOV"),
                                                           "ad": m["market_adi"], "aday": aday,
                                                           "secenek_sayisi": len(secenekler), "durum_MS": hm.get("MS")})
            if hk and not hk["cizgi_isaretiyle_tutarli"]:
                denetim["handikap_isaret_tutarsizligi"].append([m["market_tip_id"], hm.get("SOV"), m["market_adi"]])
        for mid in ham_ma:
            if mid not in {m["market_json_id"] for m in ne["marketler"]}:
                denetim["hamda_var_islenmiste_yok_market"].append(mid)
        denetim["tekrar_eden_secenek"] = [list(k) for k, v in anahtar_say.items() if v > 1]
        ayni_ad_farkli_cizgi = defaultdict(set)
        for m in marketler:
            ayni_ad_farkli_cizgi[m["market_kodu"]].add(m["cizgi"])
        # Oyuncu marketleri + ham ON adı taşıyan adsız marketler (ör. 703–710): adlar yalnızca KARŞILAŞTIRMA için toplanır
        for m in marketler:
            if m["adsiz"]:
                for s_ in m["secenekler"]:
                    on = s_["ham"].get("ON")
                    if on and not re.fullmatch(r"(Alt|Üst|\d+.*)", on) and " veya " not in on:
                        isim, esik = oyuncu_ayir(on)
                        s_["oyuncu_adayi"] = {"ham_ad": on, "ad": isim, "ad_karsilastirma": karsilastirma_adi(isim), "esik": esik,
                                              "not": "market adı bilinmediği için oyuncu istatistiği bilinmiyor"}
        tum_adlar = sorted({(s.get("oyuncu") or s.get("oyuncu_adayi"))["ad_karsilastirma"] for m in marketler for s in m["secenekler"]
                            if (s.get("oyuncu") or s.get("oyuncu_adayi")) and (s.get("oyuncu") or s.get("oyuncu_adayi"))["ad_karsilastirma"]})
        kesik = []
        for a in tum_adlar:
            uzun = [b for b in tum_adlar if b != a and b.startswith(a) and len(b) - len(a) <= 3]
            if uzun:
                kesik.append({"ad": a, "olasi_tam_ad": uzun, "not": "işaretlendi, düzeltilmedi"})
        for m in marketler:
            for s in m["secenekler"]:
                o = s.get("oyuncu") or s.get("oyuncu_adayi")
                if o:
                    o["olasi_kesik_ad"] = any(k["ad"] == o["ad_karsilastirma"] for k in kesik)
        oyuncu_bicim = Counter(("virgullu" if "," in (s["oyuncu"]["ham_ad"] or "") else "duz") for m in marketler
                               for s in m["secenekler"] if "oyuncu" in s)
        kg = [{"market_kodu": m["market_kodu"], "market_adi": m["market_adi"], "secenekler": [s["secenek_adi"] for s in m["secenekler"]]}
              for m in marketler if "Karşılıklı" in (m["market_adi"] or "") and re.search(r"Yarı|1\.Y|2\.Y", m["market_adi"] or "")]
        out["maclar"].append({
            "mac_kodu": kod, "ev": ne["ev"], "deplasman": ne["deplasman"], "karsilasma": ne["karsilasma"],
            "turnuva": ne["lig"], "turnuva_kodu": ne.get("lig_kodu"), "baslama_tr": ne["baslama_tr"], "ham_ad": he.get("ENO"),
            "sayilar": {"market_grubu": len(marketler), "benzersiz_market_turu": len({m["market_kodu"] for m in marketler}),
                        "benzersiz_market_ve_cizgi": len({(m["market_kodu"], m["cizgi"]) for m in marketler}),
                        "toplam_secenek": sum(len(m["secenekler"]) for m in marketler),
                        "kapali_secenek": sum(1 for m in marketler for s in m["secenekler"] if s["durum"] == "kapali"),
                        "durumu_dogrulanmamis_secenek": sum(1 for m in marketler for s in m["secenekler"] if s["durum"] == "durumu_dogrulanmamis"),
                        "pasif_market(MS!=1)": sum(1 for m in marketler if not m["aktif"]),
                        "oyuncu_marketi": sum(1 for m in marketler if m["market_kodu"] in OYUNCU_MTID),
                        "oyuncu_secenegi": sum(len(m["secenekler"]) for m in marketler if m["market_kodu"] in OYUNCU_MTID)},
            "cok_cizgili_marketler": {str(k): sorted(v) for k, v in ayni_ad_farkli_cizgi.items() if len(v) > 1},
            "kg_yari_marketleri": kg, "oyuncu_ad_bicimleri": dict(oyuncu_bicim), "olasi_kesik_oyuncu_adlari": kesik,
            "tanimsiz_marketler": [{"market_kodu": m["market_kodu"], "cizgi": m["cizgi"], "market_adi": m["market_adi"],
                                    "aday": m["aday"], "MS": m["market_durumu_MS"], "secenek_sayisi": len(m["secenekler"])}
                                   for m in marketler if m["adsiz"]],
            "denetim": {k: v for k, v in denetim.items()}, "marketler": marketler})
    return out


# ---------------------------------------------------------------- karşılaştırma
def _ondalik(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    if s in ("", "-", "–"):
        return None
    try:
        return float(s)
    except ValueError:
        return "gecersiz"


def referans_oku(yol: Path) -> list[dict]:
    yol = Path(yol)
    if yol.suffix.lower() == ".csv":
        with open(yol, encoding="utf-8-sig", newline="") as f:
            satirlar = list(csv.DictReader(f, delimiter=";" if ";" in f.readline() else ","))
        if not satirlar:   # ayraç tahmini için okunan ilk satırı geri al
            pass
        with open(yol, encoding="utf-8-sig", newline="") as f:
            ilk = f.readline(); f.seek(0)
            satirlar = list(csv.DictReader(f, delimiter=";" if ilk.count(";") > ilk.count(",") else ","))
    else:
        d = json.loads(yol.read_text(encoding="utf-8"))
        satirlar = d if isinstance(d, list) else d.get("satirlar", [])
    return [{k.strip().casefold(): v for k, v in r.items()} for r in satirlar]


def cekim_satirlari(cekim: dict) -> list[dict]:
    out = []
    for mac in cekim["maclar"]:
        for m in mac.get("marketler", []):
            for s in m["secenekler"]:
                out.append({"mac_kodu": mac["mac_kodu"], "mac": mac["karsilasma"], "market_kodu": m["market_kodu"],
                            "market_adi": m["market_adi"], "cizgi": m["cizgi"], "secenek": s["secenek_adi"],
                            "oran": None if s["durum"] == "kapali" else s["oran"], "durum": s["durum"],
                            "oyuncu": (s.get("oyuncu") or {}).get("ad"), "esik": (s.get("oyuncu") or {}).get("esik"),
                            "adsiz": m.get("adsiz", False), "secenek_no": s.get("secenek_no")})
    return out


def _mac_anahtari(r: dict, maclar: dict) -> int | None:
    k = r.get("mac_kodu") or r.get("kod")
    if k not in (None, ""):
        try:
            return int(k)
        except ValueError:
            pass
    ad = _sade(r.get("mac") or r.get("karsilasma"))
    return next((kod for kod, a in maclar.items() if _sade(a) == ad), None)


def karsilastir(cekim: dict, referans: list[dict]) -> dict:
    maclar = {m["mac_kodu"]: m["karsilasma"] for m in cekim["maclar"] if "karsilasma" in m}
    cs = cekim_satirlari(cekim)
    hatalar = {k: [] for k in ("1_eksik_market", "2_eksik_secenek", "3_yanlis_oran", "4_yanlis_oyuncu",
                               "5_yanlis_market_kodu_eslesmesi", "6_durum_hatasi", "7_tekrar_eden_secenek",
                               "8_yanlis_esik")}
    istat = defaultdict(lambda: {"referans_toplam_secenek": 0, "adla_eslesen_secenek": 0, "adsiz_eslesme_adayi_secenek": 0,
                                 "gercek_eksik_secenek": 0, "oran_dogru": 0, "oran_yanlis": 0, "durum_dogru": 0,
                                 "durum_yanlis": 0, "kapali_ref": 0})
    adsiz_m = defaultdict(dict)       # mac -> {market_anahtarı: [(secenek_no, oran|None), ...]}
    bilgi = {"cekimde_fazladan_market": [], "eslesmeyen_referans_maci": []}

    def market_anahtari(mk, ad, cizgi):
        return (mk, _sade(ad), None if cizgi in (None, "") else float(str(cizgi).replace(",", ".")))

    cekim_m = defaultdict(dict)       # mac -> {(kod, ad, cizgi): {secenek_sade: satir}}
    tekrar = Counter()
    for r in cs:
        mk = market_anahtari(r["market_kodu"], r["market_adi"], r["cizgi"])
        tekrar[(r["mac_kodu"], mk, _sade(r["secenek"]))] += 1
        cekim_m[r["mac_kodu"]].setdefault(mk, {})[_sade(r["secenek"])] = r
        if r.get("adsiz"):
            adsiz_m[r["mac_kodu"]].setdefault(mk, []).append((r.get("secenek_no"), r["oran"]))
    for (mac, mk, sec), n in tekrar.items():
        if n > 1:
            hatalar["7_tekrar_eden_secenek"].append({"kaynak": "cekim", "mac": mac, "market": mk, "secenek": sec, "adet": n})
    ref_tekrar = Counter()
    ref_m = defaultdict(lambda: defaultdict(dict))
    for r in referans:
        mac = _mac_anahtari(r, maclar)
        if mac is None:
            bilgi["eslesmeyen_referans_maci"].append(r.get("mac") or r.get("mac_kodu"))
            continue
        mk_kod = r.get("market_kodu")
        mk_kod = int(mk_kod) if mk_kod not in (None, "") else None
        sec = _sade(r.get("secenek"))
        ref_tekrar[(mac, mk_kod, _sade(r.get("market_adi")), r.get("cizgi"), sec)] += 1
        ref_m[mac][(mk_kod, _sade(r.get("market_adi")), None if r.get("cizgi") in (None, "") else float(str(r["cizgi"]).replace(",", ".")))][sec] = r
    for k, n in ref_tekrar.items():
        if n > 1:
            hatalar["7_tekrar_eden_secenek"].append({"kaynak": "referans", "anahtar": list(k), "adet": n})

    for mac, rmarkets in ref_m.items():
        cm = cekim_m.get(mac, {})
        eslesen_cekim = set()
        for (rkod, rad, rciz), rsec in rmarkets.items():
            # 1) ad + çizgi ile bul; 2) kod + çizgi ile bul
            ad_es = [k for k in cm if k[1] == rad and (rciz is None or k[2] == rciz)]
            kod_es = [k for k in cm if rkod is not None and k[0] == rkod and (rciz is None or k[2] == rciz)]
            hedef = ad_es[0] if len(ad_es) == 1 else (kod_es[0] if len(kod_es) == 1 else None)
            if hedef is None:
                # Adsız (sözlükte olmayan) bir çekim marketi, oran dizisi birebir aynıysa ADAY sayılır — ad verilmez.
                ref_oranlar = [_ondalik(x.get("oran")) for x in rsec.values()]
                adaylar_ = [k for k, v in adsiz_m.get(mac, {}).items() if k not in eslesen_cekim
                            and [o for _, o in sorted(v, key=lambda t: t[0] or 0)] == ref_oranlar]
                if len(adaylar_) == 1:
                    eslesen_cekim.add(adaylar_[0])
                    bilgi.setdefault("adsiz_eslesme_adaylari", []).append(
                        {"mac": mac, "referans_market_adi": rad, "referans_cizgi": rciz, "cekim_market": list(adaylar_[0]),
                         "secenek_sayisi": len(rsec), "eslesme": "oran dizisi birebir", "not": "kesin eşleme değildir"})
                    istat[mac]["referans_toplam_secenek"] += len(rsec)
                    istat[mac]["adsiz_eslesme_adayi_secenek"] += len(rsec)
                    continue
                hatalar["1_eksik_market"].append({"mac": mac, "market_kodu": rkod, "market_adi": rad, "cizgi": rciz,
                                                  "aday_sayisi": {"ad": len(ad_es), "kod": len(kod_es), "adsiz_oran": len(adaylar_)},
                                                  "referans_secenekleri": [[x.get("secenek"), x.get("oran")] for x in rsec.values()]})
                istat[mac]["referans_toplam_secenek"] += len(rsec)
                istat[mac]["gercek_eksik_secenek"] += len(rsec)
                continue
            eslesen_cekim.add(hedef)
            if rkod is not None and hedef[0] != rkod:
                hatalar["5_yanlis_market_kodu_eslesmesi"].append({"mac": mac, "referans_kodu": rkod, "cekim_kodu": hedef[0], "ad": rad})
            if ad_es == [] and kod_es:
                hatalar["5_yanlis_market_kodu_eslesmesi"].append({"mac": mac, "kod": rkod, "referans_adi": rad, "cekim_adi": hedef[1]})
            csec = cm[hedef]
            oyuncu_m = hedef[0] in OYUNCU_MTID
            for s, rr in rsec.items():
                st = istat[mac]
                st["referans_toplam_secenek"] += 1
                if _ondalik(rr.get("oran")) is None:
                    st["kapali_ref"] += 1
                c = csec.get(s)
                if c is None:
                    if oyuncu_m:
                        risim, resik = oyuncu_ayir(rr.get("secenek") or "")
                        ayni_oyuncu = [x for x in csec.values() if karsilastirma_adi(x["oyuncu"]) == karsilastirma_adi(risim)]
                        if ayni_oyuncu and resik is not None:
                            hatalar["8_yanlis_esik"].append({"mac": mac, "market": list(hedef), "referans": rr.get("secenek"),
                                                             "cekimdeki_esikler": sorted(x["esik"] for x in ayni_oyuncu if x["esik"] is not None)})
                            st["yanlis_esik_ya_da_oyuncu"] = st.get("yanlis_esik_ya_da_oyuncu", 0) + 1
                            continue
                        ayni_esik = [x for x in csec.values() if x["esik"] == resik]
                        benzer = [x for x in ayni_esik
                                  if SequenceMatcher(None, _sade(x["oyuncu"]), _sade(risim)).ratio() >= 0.8]
                        if benzer:
                            hatalar["4_yanlis_oyuncu"].append({"mac": mac, "market": hedef, "referans": rr.get("secenek"),
                                                               "cekim_aday": [x["secenek"] for x in benzer]})
                            st["yanlis_esik_ya_da_oyuncu"] = st.get("yanlis_esik_ya_da_oyuncu", 0) + 1
                            continue
                    st["gercek_eksik_secenek"] += 1
                    hatalar["2_eksik_secenek"].append({"mac": mac, "market": list(hedef), "secenek": rr.get("secenek")})
                    continue
                st["adla_eslesen_secenek"] += 1
                ro, co = _ondalik(rr.get("oran")), c["oran"]
                rkapali, ckapali = ro is None, c["durum"] == "kapali"
                st["durum_dogru" if rkapali == ckapali else "durum_yanlis"] += 1
                if not rkapali and not ckapali:
                    st["oran_dogru" if ro == co else "oran_yanlis"] += 1
                if rkapali != ckapali:
                    hatalar["6_durum_hatasi"].append({"mac": mac, "market": list(hedef), "secenek": c["secenek"],
                                                      "referans": "kapali" if rkapali else "aktif", "cekim": c["durum"]})
                elif not rkapali and ro != co:
                    hatalar["3_yanlis_oran"].append({"mac": mac, "market": list(hedef), "secenek": c["secenek"],
                                                     "referans": ro, "cekim": co})
        for k in cm:
            if k not in eslesen_cekim and ref_m.get(mac):
                bilgi["cekimde_fazladan_market"].append({"mac": mac, "market": list(k)})
    # zaman farkı
    ref_z = sorted({str(r.get("cekim_zamani")) for r in referans if r.get("cekim_zamani")})
    zaman = {"cekim_utc": cekim["cekim"]["cekim_utc"], "referans_zamanlari": ref_z}
    if ref_z:
        try:
            cz = datetime.fromisoformat(cekim["cekim"]["cekim_utc"])
            farklar = [abs((datetime.fromisoformat(z) - cz).total_seconds()) / 60 for z in ref_z]
            zaman["en_buyuk_fark_dk"] = round(max(farklar), 1)
        except ValueError:
            zaman["en_buyuk_fark_dk"] = "hesaplanamadı (zaman biçimi)"
    else:
        zaman["en_buyuk_fark_dk"] = "bilinmiyor — referansta çekim zamanı yok"
    zaman["not"] = ("Oranlar zamanla değişir: farklı anlarda alınmış verilerde '3_yanlis_oran' ve '6_durum_hatasi' "
                    "çekim hatası değil, piyasa değişimi olabilir.")
    for mac, st in istat.items():
        tam = st["durum_dogru"] - st["oran_yanlis"]       # eşleşen + durum doğru + (açıksa) oran birebir
        st["tam_dogru"] = tam
        st["dogruluk_orani(tam_dogru/referans_toplam)"] = round(tam / st["referans_toplam_secenek"], 4) if st["referans_toplam_secenek"] else None
        st["kapsama(adla+aday)/referans"] = round((st["adla_eslesen_secenek"] + st["adsiz_eslesme_adayi_secenek"])
                                                  / st["referans_toplam_secenek"], 4) if st["referans_toplam_secenek"] else None
        assert st["referans_toplam_secenek"] == st["adla_eslesen_secenek"] + st["adsiz_eslesme_adayi_secenek"] + \
            st["gercek_eksik_secenek"] + st.get("yanlis_esik_ya_da_oyuncu", 0), "sayım tutarsız"
        st["cekimde_olup_referansta_olmayan_market"] = sum(1 for x in bilgi["cekimde_fazladan_market"] if x["mac"] == mac)
    return {"zaman": zaman, "ozet": {k: len(v) for k, v in hatalar.items()}, "mac_istatistikleri": dict(istat),
            "hatalar": hatalar, "bilgi": bilgi}


# ---------------------------------------------------------------- Nesine arayüz metni (kopyala-yapıştır) okuyucu
_ORAN = re.compile(r"^(?:\d+(?:[.,]\d+)?|-)$")


def _oran_mi(x: str) -> bool:
    return bool(_ORAN.match(x.strip()))


def _baslik_mi(x: str) -> bool:
    """Arayüzdeki grup başlığı (ör. 'MAÇ SONUCU', 'KORNER/KART'): büyük harf, rakamsız."""
    x = x.strip()
    return len(x) >= 3 and x == x.upper() and not re.search(r"\d", x) and re.search(r"[A-ZÇĞİÖŞÜ]", x) is not None


def arayuz_metni_oku(yol: Path, mac_adi: str | None = None) -> dict:
    """Nesine arayüzünden kopyalanmış metni satırlara çevirir. Hiçbir değer düzeltilmez.
    Yapı: [maç adı] → GRUP BAŞLIĞI → '1' (MBS) [→ 'YENİ'] → market adı → (seçenek, oran) çiftleri.
    Bir '1' satırından sonra oran gelirse '1' seçenek adıdır; metin gelirse yeni market başlar.
    Dönüş: {'satirlar': [...], 'sorunlar': [...]} — sorunlar: eşleşmeyen satır, oranı olmayan seçenek vb."""
    satirlar = [l.strip() for l in Path(yol).read_text(encoding="utf-8").splitlines() if l.strip()]
    out, sorunlar = [], []
    mac, grup, market, yeni = mac_adi, None, None, False
    i = 0
    while i < len(satirlar):
        l = satirlar[i]
        sonraki = satirlar[i + 1] if i + 1 < len(satirlar) else None
        if " - " in l and sonraki and _baslik_mi(sonraki) and not _oran_mi(l):
            mac, market = l, None
            i += 1
            continue
        if _baslik_mi(l) and sonraki == "1":
            grup, market = l, None
            i += 1
            continue
        if l == "1" and sonraki is not None and not _oran_mi(sonraki):
            yeni = False
            j = i + 1
            if satirlar[j] == "YENİ":
                yeni, j = True, j + 1
            market = satirlar[j]
            i = j + 1
            continue
        if market is None:
            sorunlar.append({"satir": i + 1, "metin": l, "sorun": "market dışında satır"})
            i += 1
            continue
        if sonraki is not None and _oran_mi(sonraki) and not _oran_mi(l) or (l in ("0", "1", "2") and sonraki is not None and _oran_mi(sonraki)):
            out.append({"mac": mac, "grup": grup, "market_adi": market, "yeni_etiketi": yeni, "secenek": l,
                        "oran": sonraki, "kaynak_satir": i + 1})
            i += 2
            continue
        sorunlar.append({"satir": i + 1, "metin": l, "sorun": "oranı olmayan seçenek ya da tanınmayan satır", "market": market})
        i += 1
    return {"satirlar": out, "sorunlar": sorunlar}


def referans_kalitesi(satirlar: list[dict]) -> dict:
    """Referansın kendi içindeki tekrarlar (aynı maç+market+seçenek) ve market başına seçenek sayıları."""
    c = Counter((r["mac"], r["market_adi"], r["secenek"]) for r in satirlar)
    farkli_oranli = defaultdict(set)
    for r in satirlar:
        farkli_oranli[(r["mac"], r["market_adi"], r["secenek"])].add(r["oran"])
    return {"tekrar": [{"anahtar": list(k), "adet": n, "oranlar": sorted(farkli_oranli[k])} for k, n in c.items() if n > 1],
            "market_sayisi": {m: len({r["market_adi"] for r in satirlar if r["mac"] == m}) for m in {r["mac"] for r in satirlar}},
            "secenek_sayisi": {m: sum(1 for r in satirlar if r["mac"] == m) for m in {r["mac"] for r in satirlar}}}


def tanimsiz_market_raporu(bulten_klasoru: Path) -> dict:
    """Bütün bültende sözlükte olmayan (adsız) marketler: kod, çizgi, maç, durum, seçenek sayısı, ham seçenek adları.
    Hiçbir ad önerilmez; yalnızca aday dosyasında kanıtı olan kodlar için aday bilgisi eklenir."""
    bk = Path(bulten_klasoru)
    norm = json.loads((bk / "mac_oncesi.json").read_text(encoding="utf-8"))
    ham = json.loads((bk / "ham" / "mac_oncesi.json").read_text(encoding="utf-8"))
    ham_ma = {m["ID"]: m for e in (ham.get("sg") or {}).get("EA", []) for m in e.get("MA", [])}
    adaylar = aday_eslemeleri()
    kodlar = defaultdict(list)
    for e in norm["futbol"]:
        for m in e["marketler"]:
            if m["market_adi_kaynagi"] != "yok":
                continue
            hm = ham_ma.get(m["market_json_id"], {})
            kodlar[m["market_tip_id"]].append({"mac_kodu": e["kod"], "mac": e["karsilasma"], "lig": e["lig"],
                                               "cizgi": hm.get("SOV"), "MS": hm.get("MS"), "secenek_sayisi": len(m["secenekler"]),
                                               "ham_secenek_adlari": [o.get("ON") for o in hm.get("OCA", [])][:6],
                                               "islenmis_ad": m["market_adi"]})
    return {"bulten": str(bk), "toplam_adsiz_market": sum(len(v) for v in kodlar.values()),
            "kodlar": {str(k): {"adet": len(v), "aday": adaylar.get(str(k)), "ornekler": v} for k, v in sorted(kodlar.items())},
            "kural": "ad tahmin edilmez; aday yalnızca bağımsız referans kanıtıyla, kesinleşme iki doğrulama + kullanıcı onayıyla"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    d = alt.add_parser("disa-aktar"); d.add_argument("--bulten", required=True); d.add_argument("--mac", type=int, action="append", required=True)
    d.add_argument("--cikti")
    k = alt.add_parser("karsilastir"); k.add_argument("--cekim", required=True); k.add_argument("--referans", required=True)
    k.add_argument("--cikti")
    a = ap.parse_args(argv)
    if a.komut == "disa-aktar":
        r = disa_aktar(Path(a.bulten), a.mac)
        yol = Path(a.cikti or Path(a.bulten) / f"dogrulama_{'_'.join(map(str, a.mac))}.json")
    else:
        r = karsilastir(json.loads(Path(a.cekim).read_text(encoding="utf-8")), referans_oku(Path(a.referans)))
        yol = Path(a.cikti or Path(a.referans).with_suffix(".karsilastirma.json"))
    yol.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"cikti": str(yol)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
