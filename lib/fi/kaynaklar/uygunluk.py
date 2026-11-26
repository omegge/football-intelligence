"""C aşaması: lig/sezon bazında veri uygunluğu matrisi (yalnızca YEREL önbellekten; ağ isteği atmaz).

Kaynaklar ve karar durumu docs/VERI_KAYNAKLARI.md'deki kullanıcı kararlarına dayanır:
  - OpenFootball (CC0, git klonu)              : KABUL — tarihsel skor + ilk yarı skoru
  - OpenLigaDB (ODbL 1.0, adil kullanım)       : entegrasyona uygun — Almanya + UEFA kulüp turnuvaları (topluluk girişi)
  - football-data.org ücretsiz plan            : 12 yarışma, gecikmeli; anahtar gizli (bu modül okumaz)
  - football-data.co.uk, ClubElo, StatsBomb    : PASİF (kullanıcı kararı) — matriste "kullanılmıyor" olarak yazılır
Korner, kart, şut, xG, hakem: izinli ve güncel toplu kaynak YOK; yalnızca OpenFootball '*-full' dosyalarında (3 lig,
1 sezon) kart ve hakem adı var. Bu boşluk matriste açıkça gösterilir; değer uydurulmaz.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import openfootball as O

KOK = Path(__file__).resolve().parents[3]
OLDB = KOK / "output" / "onbellek" / "openligadb"

# İstenen kapsam: (görünen ad, openfootball kodu ya da None, OpenLigaDB önbellek dosyası ya da None,
#                  football-data.org ücretsiz planda mı)
KAPSAM = [
    ("İngiltere Premier League", "en.1", None, True),
    ("İngiltere Championship", "en.2", None, True),
    ("İngiltere League One", "en.3", None, False),
    ("İngiltere League Two", "en.4", None, False),
    ("Almanya Bundesliga", "de.1", None, True),
    ("Almanya 2. Bundesliga", "de.2", None, False),
    ("Almanya 3. Liga", "de.3", "getmatchdata_bl3_2026.json", False),
    ("İspanya La Liga", "es.1", None, True),
    ("İspanya Segunda División", "es.2", None, False),
    ("İtalya Serie A", "it.1", None, True),
    ("İtalya Serie B", "it.2", None, False),
    ("Fransa Ligue 1", "fr.1", None, True),
    ("Fransa Ligue 2", "fr.2", None, False),
    ("Hollanda Eredivisie", "nl.1", None, True),
    ("Portekiz Primeira Liga", "pt.1", None, True),
    ("Türkiye Süper Lig", "tr.1", None, False),
    ("Türkiye 1. Lig", "tr.2", None, False),
    ("Belçika Pro League", "be.1", None, False),
    ("İskoçya Premiership", "sco.1", None, False),
    ("Avusturya Bundesliga", "at.1", None, False),
    ("İsviçre Super League", "ch.1", None, False),
    ("Danimarka Superliga", None, None, False),
    ("Norveç Eliteserien", None, None, False),
    ("İsveç Allsvenskan", None, None, False),
    ("UEFA Şampiyonlar Ligi", "uefa.cl", "getmatchdata_ucl_2026.json", True),
    ("UEFA Avrupa Ligi", None, "getmatchdata_uel2026_2026.json", False),
    ("UEFA Konferans Ligi", None, "getmatchdata_uecl2026_2026.json", False),
]


def openfootball_ozeti(lig: str, kok: Path = O.KOK) -> dict | None:
    sezonlar = []
    for d in sorted(p for p in Path(kok).iterdir() if p.is_dir() and O.SEZON_DESENI.fullmatch(p.name)):
        f = d / f"{lig}.json"
        if not f.exists():
            continue
        ms = O._maclar(json.loads(f.read_bytes()))
        skorlu = [m for m in ms if O._skor(m, "ft")]
        ht = [m for m in skorlu if O._skor(m, "ht")]
        tarihler = sorted(m["date"] for m in skorlu if m.get("date"))
        takimlar = {m.get("team1") for m in ms} | {m.get("team2") for m in ms}
        sezonlar.append({"sezon": d.name, "mac": len(ms), "skorlu": len(skorlu), "ilk_yari_skorlu": len(ht),
                         "takim": len(takimlar - {None}),
                         "ilk_tarih": tarihler[0] if tarihler else None, "son_tarih": tarihler[-1] if tarihler else None,
                         "tamam_orani": round(len(skorlu) / len(ms), 3) if ms else 0.0})
    if not sezonlar:
        return None
    tam = [s for s in sezonlar if s["tamam_orani"] >= 0.98]
    return {"sezonlar": sezonlar, "sezon_sayisi": len(sezonlar), "tam_sezon_sayisi": len(tam),
            "skorlu_mac": sum(s["skorlu"] for s in sezonlar),
            "ilk_yari_orani": round(sum(s["ilk_yari_skorlu"] for s in sezonlar) / max(1, sum(s["skorlu"] for s in sezonlar)), 3),
            "son_skorlu_tarih": max((s["son_tarih"] for s in sezonlar if s["son_tarih"]), default=None),
            "eksik_sezon_araligi": _bosluklar([s["sezon"] for s in sezonlar])}


def _bosluklar(sezonlar: list[str]) -> list[str]:
    yillar = sorted(int(s[:4]) for s in sezonlar)
    return [f"{y}-{str(y + 1)[2:]}" for y in range(yillar[0], yillar[-1]) if y not in yillar] if yillar else []


def okuyucu_denetimi(lig: str, kok: Path = O.KOK) -> list[dict]:
    """lig_oku ile sezon sezon okuma; sert tarih tutarsızlığı olan (modelde KULLANILAMAYAN) sezonlar."""
    hatali = []
    for d in sorted(p for p in Path(kok).iterdir() if p.is_dir() and O.SEZON_DESENI.fullmatch(p.name)):
        if not (d / f"{lig}.json").exists():
            continue
        try:
            O.lig_oku(lig, kok=kok, sezonlar=[d.name])
        except O.VeriTutarsizligi as e:
            hatali.append({"sezon": d.name, "neden": str(e)[:200]})
    return hatali


def openligadb_ozeti(dosya: str, kok: Path = OLDB) -> dict | None:
    f = Path(kok) / dosya
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    biten = [m for m in d if m.get("matchIsFinished")]
    iy = [m for m in biten if any(r.get("resultTypeID") == 1 for r in m.get("matchResults", []))]
    goller = [g for m in biten for g in m.get("goals", [])]
    erisim = None
    for ad in ("getmatchdata_2026.erisim_utc",):
        if (Path(kok) / ad).exists():
            erisim = (Path(kok) / ad).read_text().strip()
    return {"dosya": dosya, "mac": len(d), "biten": len(biten), "ilk_yari_skorlu": len(iy),
            "son_biten_utc": max((m["matchDateTimeUTC"] for m in biten), default=None),
            "gol_olayi": len(goller), "dakikali_gol_orani": round(sum(1 for g in goller if g.get("matchMinute") is not None)
                                                                  / len(goller), 3) if goller else None,
            "erisim_utc": erisim}


def full_dosya_ozeti(kok: Path = O.KOK) -> list[dict]:
    out = []
    for f in sorted(Path(kok).glob("*/*-full.json")):
        ms = O._maclar(json.loads(f.read_bytes()))
        out.append({"dosya": f"{f.parent.name}/{f.name}", "mac": len(ms),
                    "kart_kaydi_olan": sum(1 for m in ms if m.get("bookings")),
                    "hakem_kaydi_olan": sum(1 for m in ms if m.get("referees")),
                    "gol_dakikasi_olan": sum(1 for m in ms if m.get("goals1") or m.get("goals2"))})
    return out


def matris() -> dict:
    satirlar = []
    for ad, of, oldb, fdorg in KAPSAM:
        o = openfootball_ozeti(of) if of else None
        if o:
            o["okunamayan_sezonlar"] = okuyucu_denetimi(of)
        l = openligadb_ozeti(oldb) if oldb else None
        if o and o["tam_sezon_sayisi"] >= 5 and o["ilk_yari_orani"] >= 0.85:
            durum = "tarihsel_yeterli"
        elif o or l:
            durum = "kismi"
        else:
            durum = "veri_yok"
        satirlar.append({"lig": ad, "openfootball": of, "openfootball_ozet": o, "openligadb_ozet": l,
                         "football_data_org_ucretsiz": fdorg, "durum": durum,
                         "korner": "yok", "kart": "yok (yalnızca *-full dosyaları)" if of in ("en.1", "de.1", "at.1") else "yok",
                         "sut_xg": "yok", "hakem": "yok (yalnızca *-full dosyaları)" if of in ("en.1", "de.1", "at.1") else "yok"})
    return {"uretim_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "openfootball_commit": O.commit_kimligi(O.KOK), "satirlar": satirlar, "full_dosyalar": full_dosya_ozeti(),
            "pasif_kaynaklar": ["football-data.co.uk (koşullar: AI/bot yasağı)", "ClubElo (koşullar belirsiz)",
                                "StatsBomb (kullanım sözleşmesi)", "open-matchday (köken belirsiz)"]}


def rapor_md(m: dict) -> str:
    s = ["# Veri uygunluğu matrisi (C aşaması)", "",
         f"Üretim: {m['uretim_utc']} · OpenFootball commit `{(m['openfootball_commit'] or '')[:12]}` · "
         "OpenLigaDB: yerel önbellek (tek seferlik adil kullanım istekleri).", "",
         "Durum: **tarihsel_yeterli** = OpenFootball'da ≥5 tam sezon ve ilk yarı skoru ≥%85 · **kismi** = veri var ama "
         "sezon/güncellik eksik · **veri_yok** = izinli kaynak yok.", "",
         "| Lig | Durum | OF sezon (tam) | OF skorlu maç | İY skor % | OF son skor | Eksik sezonlar | Okuyucu: kullanılamayan "
         "sezon | OpenLigaDB 2026-27 (biten/toplam, son) | fd.org ücretsiz | Korner | Kart | Şut/xG | Hakem |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in m["satirlar"]:
        o, l = r["openfootball_ozet"], r["openligadb_ozet"]
        s.append("| " + " | ".join([
            r["lig"], r["durum"],
            f"{o['sezon_sayisi']} ({o['tam_sezon_sayisi']})" if o else "—",
            str(o["skorlu_mac"]) if o else "—",
            f"{100 * o['ilk_yari_orani']:.0f}" if o else "—",
            o["son_skorlu_tarih"] or "—" if o else "—",
            ", ".join(o["eksik_sezon_araligi"]) or "yok" if o else "—",
            (", ".join(x["sezon"] for x in o["okunamayan_sezonlar"]) or "yok") if o else "—",
            f"{l['biten']}/{l['mac']}, {(l['son_biten_utc'] or '—')[:10]}" if l else "—",
            "evet" if r["football_data_org_ucretsiz"] else "hayır",
            r["korner"], r["kart"], r["sut_xg"], r["hakem"]]) + " |")
    s += ["", "Okuyucu denetimi: kullanılamayan sezonlarda kaynak tarihleri sert tutarsız (ör. 2019-20 COVID sonrası maçlar "
          "2019 yılıyla yazılmış). Kanıtlı tek tek düzeltme yapılmadan bu sezonlar modelde KULLANILMAZ; genel yıl +1 kuralı "
          "uygulanmaz."]
    s += ["", "## OpenFootball '-full' dosyaları (kart, hakem, gol dakikası)", "",
          "| Dosya | Maç | Kart kaydı | Hakem kaydı | Gol dakikası |", "|---|---|---|---|---|"]
    for f in m["full_dosyalar"]:
        s.append(f"| {f['dosya']} | {f['mac']} | {f['kart_kaydi_olan']} | {f['hakem_kaydi_olan']} | {f['gol_dakikasi_olan']} |")
    s += ["", "Pasif (kullanılmayan) kaynaklar: " + "; ".join(m["pasif_kaynaklar"]) + "."]
    return "\n".join(s)


if __name__ == "__main__":
    import sys
    m = matris()
    cik = Path(sys.argv[1]) if len(sys.argv) > 1 else KOK / "output" / "veri_uygunlugu"
    cik.mkdir(parents=True, exist_ok=True)
    (cik / "matris.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    (cik / "MATRIS.md").write_text(rapor_md(m), encoding="utf-8")
    print(cik / "MATRIS.md")
