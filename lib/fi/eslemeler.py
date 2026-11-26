"""Lig ve takım eşleme ADAYLARI (kanıtlı; hiçbiri otomatik onaylanmaz).

1) Nesine lig adı → kaynak lig: Nesine bültenlerindeki takım adlarının her aday kaynak ligin son sezon kadrosuyla
   'kesin' eşleşme oranı. Aday ancak bir kaynak ligde örtüşme ≥ %80 VE en yakın rakip ligde ≤ %20 ise
   "guclu_aday" olur; yine de durum "onay_bekliyor"dur. Onaylı eşleme yalnızca veri/lig_eslemeleri.json'a kullanıcı
   kararıyla yazılır.
2) OpenLigaDB takım adı (Almanca) → Nesine adı: aynı UTC başlama zamanında oynanan TEK maçın iki tarafı.
   Kanıt: başlama zamanı + karşılaşma eşleşmesi. Ad benzerliği tek başına kanıt sayılmaz; durum "onay_bekliyor".
"""
from __future__ import annotations

import glob
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .kaynaklar import openfootball as O
from .takim_adlari import TakimEslestirici, benzerlik

KOK = Path(__file__).resolve().parents[2]
ADAY_LIGLER = {"ENG": ["en.1", "en.2", "en.3", "en.4"], "DE": ["de.1", "de.2", "de.3"], "IT": ["it.1", "it.2"],
               "ES": ["es.1", "es.2"], "FR": ["fr.1", "fr.2"], "NL": ["nl.1"], "PT": ["pt.1"], "TR": ["tr.1", "tr.2"],
               "BE": ["be.1"], "SCO": ["sco.1"], "AT": ["at.1", "at.2"], "CH": ["ch.1", "ch.2"]}


def nesine_ligleri(desen: str = str(KOK / "output" / "bulten_*" / "mac_oncesi.json")) -> dict:
    L = defaultdict(lambda: {"takimlar": set(), "bultenler": set(), "ulke": None, "lig_kodu": None})
    for f in sorted(glob.glob(desen)):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        for e in d.get("futbol", []) + d.get("marketsiz_futbol", []):
            if not e.get("lig"):
                continue
            r = L[e["lig"]]
            r["takimlar"].update(x for x in (e.get("ev"), e.get("deplasman")) if x)
            r["bultenler"].add(Path(f).parent.name)
            r["ulke"], r["lig_kodu"] = e.get("lig_ulke"), e.get("lig_kodu")
    return L


def kaynak_kadrolari(lig: str, ek_takimlar: dict | None = None) -> tuple[str, set]:
    """Son sezon klasöründeki takım adları (ham dosya; tarih denetiminden bağımsız) + varsa güncel kaynak adları."""
    son = None
    for d in sorted(p for p in O.KOK.iterdir() if p.is_dir() and O.SEZON_DESENI.fullmatch(p.name)):
        if (d / f"{lig}.json").exists():
            son = d
    if son is None:
        return None, set()
    ms = O._maclar(json.loads((son / f"{lig}.json").read_bytes()))
    ad = {m.get("team1") for m in ms} | {m.get("team2") for m in ms}
    ad |= set((ek_takimlar or {}).get(lig, ()))
    return son.name, {a for a in ad if a}


def lig_adaylari(ek_takimlar: dict | None = None) -> list[dict]:
    E = TakimEslestirici()
    out = []
    for nlig, v in sorted(nesine_ligleri().items()):
        kaynaklar = ADAY_LIGLER.get(v["ulke"])
        if not kaynaklar:
            continue
        sonuclar = []
        for lig in kaynaklar:
            sezon, kadro = kaynak_kadrolari(lig, ek_takimlar)
            eslesen = []
            for t in sorted(v["takimlar"]):
                r = E.eslestir(t, f"openfootball:{lig}", sorted(kadro))
                if r.kullanilabilir:
                    eslesen.append([t, r.kaynak_adi])
            sonuclar.append({"kaynak_lig": lig, "kadro_sezonu": sezon, "eslesen": len(eslesen),
                             "oran": round(len(eslesen) / len(v["takimlar"]), 3), "ornekler": eslesen[:6]})
        # İkinci kanıt (yalnızca LİG adayı için; takım eşlemesi sayılmaz): her Nesine takımının en benzer kaynak adı
        # (benzerlik ≥ 0,75) hangi ligde?
        kadrolar = {r["kaynak_lig"]: kaynak_kadrolari(r["kaynak_lig"], ek_takimlar)[1] for r in sonuclar}
        benzer = defaultdict(int)
        for t in v["takimlar"]:
            enb = max(((benzerlik(t, a), lig) for lig, kd in kadrolar.items() for a in kd), default=(0, None))
            if enb[0] >= 0.75:
                benzer[enb[1]] += 1
        for r in sonuclar:
            r["benzerlik_onerisi"] = benzer.get(r["kaynak_lig"], 0)
            r["benzerlik_orani"] = round(benzer.get(r["kaynak_lig"], 0) / len(v["takimlar"]), 3)
        sonuclar.sort(key=lambda r: (-r["oran"] - r["benzerlik_orani"]))
        ilk, ikinci = sonuclar[0], (sonuclar[1] if len(sonuclar) > 1 else {"oran": 0.0, "benzerlik_orani": 0.0})
        guclu = (len(v["takimlar"]) >= 4 and ilk["oran"] + ilk["benzerlik_orani"] >= 0.8
                 and ikinci["oran"] + ikinci["benzerlik_orani"] <= 0.2)
        out.append({"nesine_lig": nlig, "nesine_lig_kodu": v["lig_kodu"], "ulke": v["ulke"],
                    "nesine_takim_sayisi": len(v["takimlar"]), "bultenler": sorted(v["bultenler"]),
                    "en_iyi_aday": ilk["kaynak_lig"] if ilk["oran"] + ilk["benzerlik_orani"] > 0 else None,
                    "kanit_gucu": "guclu_aday" if guclu else ("zayif_aday" if ilk["oran"] + ilk["benzerlik_orani"] > 0
                                                              else "aday_yok"),
                    "durum": "onay_bekliyor", "karsilastirma": sonuclar,
                    "not": "Kadro sezonu eski olabilir (terfi/düşme); güçlü aday bile kullanıcı onayı olmadan kullanılmaz."
                           if guclu else "Takım sayısı az ya da örtüşme yetersiz: eşleme önerilmez."})
    return out


def openligadb_takim_adaylari(nesine_mac_oncesi: Path, oldb_dosyalari: list[Path]) -> list[dict]:
    d = json.loads(Path(nesine_mac_oncesi).read_text(encoding="utf-8"))
    nes = defaultdict(list)
    for e in d.get("futbol", []):
        if e.get("baslama_tr"):
            utc = datetime.fromisoformat(e["baslama_tr"]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
            nes[utc].append(e)
    out = []
    for f in oldb_dosyalari:
        for m in json.loads(Path(f).read_text(encoding="utf-8")):
            utc = m["matchDateTimeUTC"][:16]
            aday = nes.get(utc, [])
            for e in aday:
                # aynı anda başlayan birden çok maç varsa: ancak bir tarafın adı birebir aynıysa karşılaşma belirlenir
                n1, n2 = m["team1"]["teamName"], m["team2"]["teamName"]
                tek = len(aday) == 1
                ortak = {e["ev"], e["deplasman"]} & {n1, n2}
                if not tek and not ortak:
                    continue
                for oldb_ad, nesine_ad in ((n1, e["ev"]), (n2, e["deplasman"])):
                    out.append({"openligadb_adi": oldb_ad, "openligadb_takim_id": (m["team1"] if oldb_ad == n1 else m["team2"])
                                .get("teamId"), "nesine_adi": nesine_ad, "kanit": {
                                    "utc_baslama": utc, "openligadb_mac_id": m["matchID"], "nesine_mac_kodu": e["kod"],
                                    "ayni_anda_baslayan_nesine_maci": len(aday),
                                    "karsilasma_belirleyici": "tek maç" if tek else f"ortak ad: {sorted(ortak)}"},
                                "durum": "onay_bekliyor"})
    return out


if __name__ == "__main__":
    import sys
    cik = KOK / "veri"
    ek = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else None
    (cik / "lig_esleme_adaylari.json").write_text(json.dumps(
        {"aciklama": "ADAY kayıtlar; hiçbiri onaylı değildir. Onay için veri/lig_eslemeleri.json'a kullanıcı kararı yazılır.",
         "uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "adaylar": lig_adaylari(ek)},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(cik / "lig_esleme_adaylari.json")


# ------------------------------------------------------------------------------------------- fikstür hizalaması
FD_ADAYLARI = {"İngiltere Championship": ("ELC", "en.2"), "İngiltere Premier Lig": ("PL", "en.1"),
               "Almanya Bundesliga": ("BL1", "de.1"), "İtalya Serie A": ("SA", "it.1"), "İspanya La Liga": ("PD", "es.1"),
               "Fransa Ligue 1": ("FL1", "fr.1"), "Hollanda Eredivisie": ("DED", "nl.1"),
               "Portekiz Premier Lig": ("PPL", "pt.1"), "Hollanda 1. Lig": ("DED", "nl.1")}


def fikstur_hizalama(nesine_maclari: list[dict], fd_maclari: list[dict]) -> dict:
    """Nesine maçları ↔ football-data.org planlı maçları: aynı UTC başlama dakikası VE iki takım da eşleşiyor mu?
    Takım eşleşmesi için 'kesin' ya da benzerlik ≥ 0,75 (yalnızca LİG kanıtı; takım eşlemesi onayı değildir)."""
    E = TakimEslestirici()
    zaman = defaultdict(list)
    for m in fd_maclari:
        zaman[m["utc_baslama"][:16]].append(m)
    hizali, hizasiz, tek = [], [], []
    for e in nesine_maclari:
        utc = datetime.fromisoformat(e["baslama_tr"]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        bulundu = None
        for m in zaman.get(utc, []):
            sk = []
            for nes, fd in ((e["ev"], m["ev"]), (e["deplasman"], m["dep"])):
                r = E.eslestir(nes, "fdorg", [fd])
                sk.append("kesin" if r.kullanilabilir else ("benzer" if benzerlik(nes, fd) >= 0.75 else "yok"))
            if "yok" not in sk:
                bulundu = {"nesine": e["karsilasma"], "nesine_kod": e.get("kod"), "fd": f"{m['ev']} - {m['dep']}",
                           "fd_id": m["kaynak_id"], "utc": utc, "takim_eslesmesi": sk}
                break
        if bulundu:
            hizali.append(bulundu)
            continue
        ayni = zaman.get(utc, [])
        kayit = {"nesine": e["karsilasma"], "utc": utc, "ayni_dakika_fd_maci": len(ayni)}
        if len(ayni) == 1:
            m = ayni[0]
            sk = []
            for nes, fd in ((e["ev"], m["ev"]), (e["deplasman"], m["dep"])):
                r = E.eslestir(nes, "fdorg", [fd])
                sk.append("kesin" if r.kullanilabilir else ("benzer" if benzerlik(nes, fd) >= 0.75 else "ad_onayi_gerekli"))
            if "ad_onayi_gerekli" in sk and sk.count("ad_onayi_gerekli") < 2:
                kayit.update({"tek_aday": f"{m['ev']} - {m['dep']}", "fd_id": m["kaynak_id"], "takim_eslesmesi": sk})
                tek.append(kayit)
                continue
        hizasiz.append(kayit)
    return {"hizali": hizali, "tek_aday_dakika": tek, "hizasiz": hizasiz}


def lig_kanit_raporu(fikstur: dict, istemci=None) -> list[dict]:
    """Her aday için: Nesine yarışma kimliği, ülke, kaynak kodu, sezon, takım listesi ve fikstür hizalaması."""
    from .kaynaklar.guncel import fd_sezon
    lig_maclari = defaultdict(list)
    for m in fikstur.get("maclar", []):
        lig_maclari[m["lig"]].append(m)
    out = []
    for nlig, (fd_kod, of_lig) in FD_ADAYLARI.items():
        ms = lig_maclari.get(nlig, [])
        if not ms:
            continue
        fd, meta = fd_sezon(fd_kod, 2026, istemci)
        planli = [m for m in fd if m["durum"] in ("SCHEDULED", "TIMED")]
        h = fikstur_hizalama(ms, planli)
        fd_takimlar = sorted({m["ev"] for m in fd} | {m["dep"] for m in fd})
        kodlar = sorted({m.get("lig_kodu") for m in ms})
        ulke = sorted({m.get("lig_ulke") for m in ms})
        if h["hizali"] and not h["hizasiz"] and not h["tek_aday_dakika"] and len(kodlar) == 1:
            durum = "kesin_eslesme_adayi"
        elif (h["hizali"] or h["tek_aday_dakika"]) and not h["hizasiz"] and len(kodlar) == 1:
            durum = "guclu_aday_takim_adi_onayi_gerekli"
        else:
            durum = "uyusmuyor" if not (h["hizali"] or h["tek_aday_dakika"]) else "belirsiz"
        out.append({"nesine_lig": nlig, "nesine_yarisma_kimligi": kodlar, "ulke": ulke, "kaynak": "football-data.org",
                    "kaynak_kodu": fd_kod, "kaynak_lig": of_lig, "sezon": "2026-27", "fd_takim_sayisi": len(fd_takimlar),
                    "nesine_mac": len(ms), "hizali_mac": len(h["hizali"]), "tek_aday_mac": len(h["tek_aday_dakika"]), "hizasiz_mac": len(h["hizasiz"]),
                    "kanit": h, "fd_sha256": meta.get("sha256"), "durum": durum, "onay": "kullanıcı onayı bekliyor",
                    "not": "Fikstür hizalaması = aynı başlama dakikası + iki takım. Takım benzerliği tek başına kanıt değil."})
    return out
