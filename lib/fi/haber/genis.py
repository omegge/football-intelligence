"""Geniş (açık internet) maç araştırması: kaynak güvenilirliği, kanıt zincirleri, zaman turları, dış görüş karantinası
ve 10 bölümlük maç raporu.

Mevcut haber katmanıyla uyumludur (kanit_kaydi.KATEGORILER, kaynak.KaynakKaydi, aynı MK-1 yasak hostları).

Temel kurallar
--------------
- Erişim yolu ayrıdır: 'arama_ozeti' (yalnızca web arama sonucu; sayfa okunmadı), 'sayfa_okundu' (koşullar/robots
  izin veriyor ve sayfa insan okuması gibi tek tek açıldı), 'kullanici_saglamasi'. Arama özeti tek başına "doğrulandı"
  sayılmaz; en fazla "dogrulanmadi" düzeyinde iddia taşır.
- Otomatik toplu okuma yoktur. Bir host otomatik okumaya kapalıysa (robots/koşullar/bot koruması) yalnızca arama özeti
  ve bağlantı saklanır; sayfa açılmaz, koruma aşılmaz. Uzun metin kopyalanmaz (özet ≤ 300 karakter).
- Bağımsızlık: aynı ilk kaynağa dayanan ya da aynı yayıncı grubundan gelen iddialar TEK kanıt zinciridir.
- Doğrulama düzeyleri: resmi (A sınıfı tek zincir) · iki_bagimsiz (≥2 zincir, en az biri ≤ B) · dogrulanmadi ·
  celiskili (aynı konu/takım/kişi için zıt durumlar). Maç başladıktan sonra yayımlanan ya da yayın saati maç gününde
  bilinmeyen iddia maç öncesi bilgi sayılmaz.
- Dış görüşler (önizleme/tahmin siteleri, analistler, forumlar) KARANTİNADADIR: yüzde ve oranları kaydedilebilir ama
  hiçbir model girdisine, kalibrasyon hedefine ya da olasılık kaynağına giremez (`model_girdisi_denetle`).
- Haberlerin olasılık etkisi ölçülmüş bir yöntem olmadan uygulanmaz: nicel etki her zaman "hesaplanamaz".
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from .kaynak import YASAK_HOSTLAR

KOK = Path(__file__).resolve().parents[3]
SINIF_DOSYASI = KOK / "veri" / "genis_kaynak_siniflari.json"

# Kaynak sınıfı → güvenilirlik katmanı (A en yüksek). Katman iddianın TÜRÜNE göre yorumlanır: istatistik platformu
# veri için B'dir ama kadro haberi için kaynak sayılmaz.
SINIFLAR = {
    "resmi_kulup": "A", "resmi_federasyon": "A", "resmi_lig": "A", "td_basin_toplantisi": "A",
    "ulusal_basin": "B", "yerel_basin": "B", "haber_ajansi": "B", "guvenilir_muhabir": "B",
    "istatistik_platformu": "B", "bagimsiz_analist": "C", "onizleme_tahmin_sitesi": "C",
    "forum_topluluk": "D", "bilinmeyen": "D", "arama_ozeti": "E",
}
ERISIM_YOLLARI = ("arama_ozeti", "sayfa_okundu", "kullanici_saglamasi")
TURLAR = ("T-24s", "T-6s", "T-90dk", "diger")
KONULAR = ("sonuc_form", "puan_durumu", "disiplin", "sakatlik", "ceza", "kadro_disi", "ilk11_beklenen", "ilk11_kesin", "rotasyon", "td_aciklama", "td_degisimi",
           "taktik", "motivasyon", "fikstur_yogunlugu", "yolculuk", "takim_ici", "donus", "hakem", "diger")
DURUM_ZITLARI = {("yok", "var"), ("oynamaz", "oynar"), ("sakat", "hazir"), ("cezali", "cezasiz"), ("kadroda", "kadro_disi")}
OZET_SINIRI = 300
NICEL_ETKI = "hesaplanamaz"
KARANTINA_ANAHTARLARI = ("dis_gorus", "tahmin_yuzdesi", "site_tahmini", "analist_yuzdesi", "piyasa_orani", "oran")


class GenisHata(ValueError):
    pass


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _utc(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else None            # saat dilimi yoksa kesin zaman sayılmaz


@dataclass
class Iddia:
    mac_id: str
    konu: str
    takim: str                      # "ev" | "dep" | "iki_takim" | "yok"
    kisi: str | None                # oyuncu / teknik direktör (varsa)
    durum: str | None               # ör. "yok", "oynar", "sakat", "cezali", "kadro_disi", "hazir"
    ozet: str                       # kendi cümlemizle kısa özet; uzun alıntı yok
    url: str
    kaynak_sinifi: str
    erisim_yolu: str
    arastirma_utc: str              # araştırmanın yapıldığı an
    yayin_utc: str | None           # sayfadaki/sonuçtaki yayın zamanı (saat dilimli ISO) ya da yalnızca tarih
    tur: str = "diger"
    ilk_kaynak: str | None = None   # haberin dayandığı ilk kaynak (URL ya da "kulüp açıklaması" vb.); bilinmiyorsa None
    yayinci_grubu: str | None = None
    nicel_etki: str = NICEL_ETKI
    notlar: str = ""
    ilgili_mac_dogrulandi: bool = False   # metin bu maçı (tarih/rakip) açıkça anıyor mu (araştırmacı işaretler)
    veri_dogrulamasi: str | None = None   # bağımsız veriyle sınama sonucu: "dogrulandi" | "celisiyor" | None

    def __post_init__(self):
        if self.veri_dogrulamasi not in (None, "dogrulandi", "celisiyor", "kismen"):
            raise GenisHata("veri_dogrulamasi: dogrulandi | kismen | celisiyor | None")
        if self.konu not in KONULAR:
            raise GenisHata(f"bilinmeyen konu: {self.konu}")
        if self.kaynak_sinifi not in SINIFLAR:
            raise GenisHata(f"bilinmeyen kaynak sınıfı: {self.kaynak_sinifi}")
        if self.erisim_yolu not in ERISIM_YOLLARI:
            raise GenisHata(f"bilinmeyen erişim yolu: {self.erisim_yolu}")
        if self.tur not in TURLAR:
            raise GenisHata(f"bilinmeyen araştırma turu: {self.tur}")
        if host(self.url) in YASAK_HOSTLAR:
            raise GenisHata("bahis sitesi haber kaynağı olamaz (MK-1)")
        if len(self.ozet) > OZET_SINIRI:
            raise GenisHata(f"özet {len(self.ozet)} karakter > {OZET_SINIRI}: uzun metin kopyalanmaz")
        if self.nicel_etki != NICEL_ETKI:
            raise GenisHata("haberin sayısal olasılık etkisi ölçülmüş yöntem olmadan verilemez")
        if self.erisim_yolu == "arama_ozeti":
            self.kaynak_sinifi_etkin = "arama_ozeti"
        else:
            self.kaynak_sinifi_etkin = self.kaynak_sinifi

    @property
    def katman(self) -> str:
        return SINIFLAR[self.kaynak_sinifi_etkin]

    @property
    def zincir(self) -> str:
        """Kanıt zinciri anahtarı: ilk kaynak > yayıncı grubu > host."""
        return (self.ilk_kaynak or self.yayinci_grubu or host(self.url)).lower()

    @property
    def anahtar(self) -> tuple:
        return (self.mac_id, self.konu, self.takim, (self.kisi or "").casefold())

    def mac_oncesi(self, baslama_utc: str) -> str:
        bas = _utc(baslama_utc)
        y = _utc(self.yayin_utc)
        if y is not None:
            return "mac_oncesi" if y < bas else "mac_sonrasi"
        ar = _utc(self.arastirma_utc)
        if ar is not None and ar < bas and self.ilgili_mac_dogrulandi:
            # güncel araştırma: maçtan önce bulundu ve metin bu maçı anıyor → bilinebilir (yayın saati bilinmiyor)
            return "mac_oncesi"
        if self.yayin_utc and re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.yayin_utc):
            return "ayni_gun_saat_yok" if self.yayin_utc == bas.date().isoformat() else (
                "mac_oncesi" if self.yayin_utc < bas.date().isoformat() else "mac_sonrasi")
        return "tarih_yok"

    def kayit(self) -> dict:
        d = asdict(self)
        d.update({"katman": self.katman, "zincir": self.zincir, "host": host(self.url)})
        return d


@dataclass
class DisGorus:
    """Önizleme / tahmin sitesi / analist / forum görüşü. KARANTİNA: model girdisi değildir."""
    mac_id: str
    kaynak_adi: str
    url: str
    kaynak_sinifi: str
    erisim_yolu: str
    arastirma_utc: str
    yayin_utc: str | None
    beklenen: str                    # ör. "ev kazanır", "beraberlik", "KG var", "3,5 alt"
    gerekce: str                     # sportif gerekçe özeti (≤ 300)
    konu_etiketleri: list = field(default_factory=list)   # ör. ["taktik", "ilk_yari", "korner"]
    karantina_sayilar: dict = field(default_factory=dict)  # sitenin verdiği yüzde/oran: YALNIZCA KAYIT
    surpriz_bekliyor: bool = False
    model_girdisi: bool = False

    def __post_init__(self):
        if self.model_girdisi:
            raise GenisHata("dış görüş model girdisi olamaz (MK-1)")
        if len(self.gerekce) > OZET_SINIRI:
            raise GenisHata("gerekçe özeti çok uzun")
        if host(self.url) in YASAK_HOSTLAR:
            raise GenisHata("bahis sitesi kaynak olamaz")
        if self.kaynak_sinifi not in SINIFLAR:
            raise GenisHata(f"bilinmeyen kaynak sınıfı: {self.kaynak_sinifi}")


def model_girdisi_denetle(o, yol: str = "girdi") -> None:
    """Model girdisinde dış görüş ya da karantina sayısı varsa durdurur (girdi.oransiz_mi'nin tamamlayıcısı)."""
    if isinstance(o, DisGorus):
        raise GenisHata(f"dış görüş model girdisine sızdı: {yol}")
    if isinstance(o, dict):
        for k, v in o.items():
            if any(p in str(k).casefold() for p in KARANTINA_ANAHTARLARI):
                raise GenisHata(f"karantina alanı model girdisine sızdı: {yol}.{k}")
            model_girdisi_denetle(v, f"{yol}.{k}")
    elif isinstance(o, (list, tuple)):
        for i, v in enumerate(o):
            model_girdisi_denetle(v, f"{yol}[{i}]")


# ------------------------------------------------------------------------------------------------- değerlendirme
OLUMSUZ = {"yok", "oynamaz", "sakat", "cezali", "kadro_disi", "suphe"}
OLUMLU = {"var", "oynar", "hazir", "cezasiz", "kadroda", "donuyor"}


def _zit(a: str | None, b: str | None) -> bool:
    """'oynamayacak' grubu ile 'oynayacak' grubu aynı kişi için birlikte görülürse çelişki ('suphe' tek başına değil)."""
    if not a or not b or a == b:
        return False
    if (a, b) in DURUM_ZITLARI or (b, a) in DURUM_ZITLARI:
        return True
    # 'suphe' ile 'oynamaz' çelişmez (ikisi de belirsizlik/olumsuz); 'suphe' ile 'hazir/oynar' çelişir
    return bool({a, b} & OLUMSUZ) and bool({a, b} & OLUMLU)


def iddia_degerlendir(iddialar: list[Iddia], baslama_utc: str) -> list[dict]:
    """Aynı (maç, konu, takım, kişi) iddialarını gruplar; zincir sayısı, doğrulama düzeyi, çelişki ve zaman."""
    gruplar: dict[tuple, list[Iddia]] = {}
    for i in iddialar:
        gruplar.setdefault(i.anahtar, []).append(i)
    out = []
    for k, ss in gruplar.items():
        gecerli = [s for s in ss if s.mac_oncesi(baslama_utc) == "mac_oncesi"]
        dislanan = [{"url": s.url, "neden": s.mac_oncesi(baslama_utc)} for s in ss if s not in gecerli]
        durumlar = sorted({s.durum for s in gecerli if s.durum})
        celiski = any(_zit(a, b) for a in durumlar for b in durumlar)
        zincirler: dict[str, list[Iddia]] = {}
        for s in gecerli:
            zincirler.setdefault(s.zincir, []).append(s)
        en_iyi = {z: min(v, key=lambda s: s.katman).katman for z, v in zincirler.items()}
        if not gecerli:
            duzey = "mac_oncesi_kanit_yok"
        elif celiski:
            duzey = "celiskili"
        elif any(v == "A" for v in en_iyi.values()):
            duzey = "resmi"
        elif len(zincirler) >= 2 and min(en_iyi.values()) <= "B":
            duzey = "iki_bagimsiz"
        else:
            duzey = "dogrulanmadi"
        son = max(gecerli, key=lambda s: s.arastirma_utc) if gecerli else None
        veri = sorted({s.veri_dogrulamasi for s in gecerli if s.veri_dogrulamasi})
        if "celisiyor" in veri:
            duzey = "celiskili"
        out.append({"mac_id": k[0], "konu": k[1], "takim": k[2], "kisi": k[3] or None, "dogrulama": duzey,
                    "veri_dogrulamasi": veri, "ozetler": [s.ozet for s in gecerli][:3],
                    "durumlar": durumlar, "son_durum": son.durum if son else None, "zincir_sayisi": len(zincirler),
                    "zincirler": {z: [s.url for s in v] for z, v in zincirler.items()},
                    "kopya_sayisi": sum(len(v) - 1 for v in zincirler.values()),
                    "dislanan": dislanan, "nicel_etki": NICEL_ETKI})
    return sorted(out, key=lambda r: ({"resmi": 0, "iki_bagimsiz": 1, "celiskili": 2, "dogrulanmadi": 3}.get(
        r["dogrulama"], 4), r["konu"]))


def tur_karsilastir(iddialar: list[Iddia], baslama_utc: str) -> list[dict]:
    """Turlar arasında (T-24s → T-6s → T-90dk) değişen iddialar: yeni, durum değişti, son turda görülmedi."""
    sira = {t: i for i, t in enumerate(TURLAR)}
    by: dict[tuple, dict[str, set]] = {}
    for s in iddialar:
        if s.mac_oncesi(baslama_utc) != "mac_oncesi":
            continue
        by.setdefault(s.anahtar, {}).setdefault(s.tur, set()).add(s.durum)
    out = []
    for k, t in by.items():
        sirali = sorted(t, key=lambda x: sira[x])
        if len(sirali) == 1:
            out.append({"anahtar": list(k), "degisim": "tek_turda_goruldu", "tur": sirali[0], "durum": sorted(t[sirali[0]] - {None})})
            continue
        for a, b in zip(sirali, sirali[1:]):
            if t[a] != t[b]:
                out.append({"anahtar": list(k), "degisim": "durum_degisti", "once": [a, sorted(t[a] - {None})],
                            "sonra": [b, sorted(t[b] - {None})]})
    return out


def arastirma_turu(baslama_utc: str, simdi: datetime) -> str:
    kalan = _utc(baslama_utc) - simdi
    if kalan <= timedelta(0):
        raise GenisHata("maç başlamış: maç öncesi araştırma turu açılamaz")
    if kalan <= timedelta(minutes=90):
        return "T-90dk"
    if kalan <= timedelta(hours=6, minutes=30):
        return "T-6s"
    if kalan <= timedelta(hours=26):
        return "T-24s"
    return "diger"


# ------------------------------------------------------------------------------------------------- rapor
def _favori(model: dict | None) -> tuple[str | None, str]:
    p = (model or {}).get("olasiliklar") or {}
    if model is None or model.get("durum") != "hesaplandi" or not {"MS_1", "MS_2"} <= set(p):
        return None, "bağımsız model 1X2 olasılığı yok → favori bağımsız olarak belirlenemedi (oranlarla belirlenmez)"
    if max(p["MS_1"], p["MS_2"]) < 0.5:
        return None, f"bağımsız modelde belirgin favori yok (MS1 {p['MS_1']:.2f}, MS2 {p['MS_2']:.2f})"
    return ("ev" if p["MS_1"] > p["MS_2"] else "dep"), "bağımsız model"


def mac_raporu(mac: dict, iddialar: list[Iddia], gorusler: list[DisGorus], model: dict | None,
               fiyat: dict | None = None, aramalar: list[dict] | None = None,
               yorumlar: list[dict] | None = None) -> dict:
    """10 bölümlük rapor (madde 8). `model` = is_akisi.bagimsiz_tahmin çıktısı ya da donmuş kayıt; `fiyat` =
    is_akisi.fiyat_karsilastir çıktısı (yalnızca dondurmadan sonra)."""
    bas = mac["baslama_utc"]
    model_girdisi_denetle({k: v for k, v in (model or {}).items()}, "model")
    deg = iddia_degerlendir(iddialar, bas)
    fav, fav_kaynak = _favori(model)
    favori_aleyhine = [r for r in deg if fav and r["takim"] == fav and r["dogrulama"] in ("resmi", "iki_bagimsiz")
                       and r["konu"] in ("sakatlik", "ceza", "kadro_disi", "td_degisimi") and r["son_durum"] in
                       ("yok", "oynamaz", "sakat", "cezali", "kadro_disi", None)]
    analist_yonleri = {}
    for g in gorusler:
        analist_yonleri.setdefault(g.beklenen, []).append(g.kaynak_adi)
    p = (model or {}).get("olasiliklar") or {}
    farklar = []
    for g in gorusler:
        b = g.beklenen.casefold()
        if "beraber" in b and "MS_X" in p:
            farklar.append({"gorus": g.kaynak_adi, "beklenen": g.beklenen, "model": f"MS X {p['MS_X']:.3f}"})
        elif "kg var" in b and "KG_var" in p:
            farklar.append({"gorus": g.kaynak_adi, "beklenen": g.beklenen, "model": f"KG var {p['KG_var']:.3f}"})
        else:
            farklar.append({"gorus": g.kaynak_adi, "beklenen": g.beklenen,
                            "model": "bu market için bağımsız olasılık yok (hesaplanamaz)"})
    aramalar = aramalar or []
    zamanlar = [i.arastirma_utc for i in iddialar] + [g.arastirma_utc for g in gorusler] + [a["utc"] for a in aramalar]
    return {
        "mac": {k: mac.get(k) for k in ("mac_id", "karsilasma", "lig", "baslama_utc", "baslama_tr")},
        "1_dogrulanmis_son_dakika": [r for r in deg if r["dogrulama"] in ("resmi", "iki_bagimsiz")],
        "2_dogrulanamayan_veya_celiskili": [r for r in deg if r["dogrulama"] in ("dogrulanmadi", "celiskili",
                                                                                  "mac_oncesi_kanit_yok")],
        "3_basin_gorusleri": [{"kaynak": i.url, "sinif": i.kaynak_sinifi, "ozet": i.ozet, "yayin": i.yayin_utc}
                              for i in iddialar if i.kaynak_sinifi in ("ulusal_basin", "yerel_basin", "haber_ajansi",
                                                                       "guvenilir_muhabir")],
        "4_analist_senaryolari": {"yonler": analist_yonleri,
                                  "gorusler": [{"kaynak": g.kaynak_adi, "beklenen": g.beklenen, "gerekce": g.gerekce,
                                                "sinif": g.kaynak_sinifi, "surpriz": g.surpriz_bekliyor,
                                                "karantina_sayilar": g.karantina_sayilar} for g in gorusler],
                                  "gorus_ayriligi": len(analist_yonleri) > 1,
                                  "not": "Dış görüşler ve yüzdeleri KARANTİNADA; model girdisi değildir."},
        "5_bagimsiz_model": model if model else {"durum": "hesaplanamaz", "nedenler": ["model çalıştırılmadı"]},
        "6_hesaplanamayan_marketler": (model or {}).get("hesaplanamaz_pazarlar") or "bütün marketler (model yok)",
        "7_model_analist_farki": farklar,
        "8_en_onemli_surpriz_sinyali": ({"favori": fav, "favori_kaynagi": fav_kaynak, "sinyal": favori_aleyhine[0],
                                         "not": "Sinyalin olasılık etkisi ölçülmedi (hesaplanamaz); ileriye dönük test "
                                                "ON_KAYIT_J.md"} if favori_aleyhine else
                                        {"favori": fav, "favori_kaynagi": fav_kaynak,
                                         "sinyal": None, "not": "doğrulanmış favori aleyhine sinyal yok" if fav else
                                         "favori bağımsız modelle belirlenemedi"}),
        "9_fiyat_karsilastirmasi": fiyat if fiyat else {"durum": "yapılmadı",
                                                         "neden": "donmuş bağımsız tahmin ya da sonradan alınmış bülten yok"},
        "11_sportif_cikarimlar_yorum": [{**y, "tur": "YORUM (doğrulanmış gerçek değil)", "model_etkisi": "uygulanmadı"}
                                        for y in (yorumlar or [])],
        "10_son_arastirma_ve_kaynaklar": {"son_arastirma_utc": max(zamanlar) if zamanlar else None,
                                          "turlar": sorted({i.tur for i in iddialar} | {a["tur"] for a in aramalar}),
                                          "arama_gunlugu": aramalar,
                                          "tur_degisimleri": tur_karsilastir(iddialar, bas),
                                          "baglantilar": sorted({i.url for i in iddialar} | {g.url for g in gorusler})},
    }


def rapor_md(r: dict) -> str:
    m = r["mac"]
    s = [f"# {m['karsilasma']} — {m.get('lig')} — {m.get('baslama_tr')}", "",
         "> Haberler olasılığı değiştirmez (nicel etki: hesaplanamaz). Dış görüş yüzdeleri model girdisi değildir.", ""]
    def bolum(no, ad, satirlar):
        s.extend([f"## {no}. {ad}", ""] + (satirlar or ["— (bulunamadı)"]) + [""])
    bolum(1, "Doğrulanmış son dakika haberleri", [
        f"- [{x['dogrulama']}] {x['konu']} · {x['takim']} · {x['kisi'] or ''} → {x['son_durum']} "
        f"({x['zincir_sayisi']} bağımsız zincir, {x['kopya_sayisi']} kopya; veri: {x.get('veri_dogrulamasi') or '—'}) — "
        f"{(x.get('ozetler') or [''])[0]}" for x in r["1_dogrulanmis_son_dakika"]])
    bolum(2, "Doğrulanamayan veya çelişkili iddialar", [
        f"- [{x['dogrulama']}] {x['konu']} · {x['takim']} · {x['kisi'] or ''} → {', '.join(x['durumlar']) or '?'} — "
        f"{' | '.join(x.get('ozetler') or [])}"
        + (f" (dışlanan: {x['dislanan']})" if x["dislanan"] else "") for x in r["2_dogrulanamayan_veya_celiskili"]])
    bolum(3, "Yerel ve uluslararası basın", [f"- ({x['sinif']}) {x['ozet']} — {x['kaynak']}" for x in r["3_basin_gorusleri"]])
    a = r["4_analist_senaryolari"]
    bolum(4, "Analist senaryoları (karantina)", [f"- {g['kaynak']} ({g['sinif']}): **{g['beklenen']}** — {g['gerekce']}"
                                                 + (" · sürpriz bekliyor" if g["surpriz"] else "") for g in a["gorusler"]]
          + ([f"- Görüş ayrılığı: {a['yonler']}"] if a["gorus_ayriligi"] else []))
    md = r["5_bagimsiz_model"]
    bolum(5, "Bağımsız sportif model", [f"- Durum: **{md.get('durum')}**"] + (
        [f"- {k}: {v:.3f}" for k, v in (md.get("olasiliklar") or {}).items()] +
        [f"- Veri kesimi: {md.get('veri_kesimi')} · model: {md.get('model_adi')}"] if md.get("durum") == "hesaplandi"
        else [f"- Neden: {n}" for n in md.get("nedenler", [])]))
    hm = r["6_hesaplanamayan_marketler"]
    bolum(6, "Modelin hesaplayamadığı marketler", [f"- {hm}"] if isinstance(hm, str) else
          [f"- {k}: {'; '.join(v)}" for k, v in list(hm.items())[:25]])
    bolum(7, "Model ile analist farkı", [f"- {x['gorus']}: {x['beklenen']} ↔ {x['model']}" for x in r["7_model_analist_farki"]])
    sp = r["8_en_onemli_surpriz_sinyali"]
    bolum(8, "En önemli sürpriz sinyali", [f"- Favori: {sp['favori']} ({sp['favori_kaynagi']})",
                                          f"- Sinyal: {sp['sinyal']}" if sp["sinyal"] else f"- {sp['not']}"])
    fy = r["9_fiyat_karsilastirmasi"]
    bolum(9, "Fiyat karşılaştırması (dondurmadan sonra)", [f"- {fy.get('durum', 'yapıldı')}: {fy.get('neden', '')}"]
          if "satirlar" not in fy else [f"- {x['market_adi']} {x['secenek_adi']}: oran {x['oran']}, bağımsız p "
                                        f"{x['bagimsiz_olasilik']}, başabaş {x.get('basabas_esigi', '—')}"
                                        for x in fy["satirlar"][:30]])
    k = r["10_son_arastirma_ve_kaynaklar"]
    bolum(10, "Son araştırma zamanı ve kaynaklar", [f"- Son araştırma: {k['son_arastirma_utc']} · turlar: {k['turlar']}"]
          + [f"- Tur değişimi: {d}" for d in k["tur_degisimleri"] if d["degisim"] == "durum_degisti"]
          + [f"- Arama ({a['tur']}, {a['utc']}): \"{a['sorgu']}\" → {a['sonuc']}" for a in k.get("arama_gunlugu", [])]
          + [f"- {u}" for u in k["baglantilar"]])
    bolum(11, "Sportif çıkarımlar — YORUM (gerçeklerden ayrı; modele uygulanmadı)",
          [f"- {y['mekanizma']} (dayanak: {', '.join(y.get('dayanak', []))})" for y in r.get("11_sportif_cikarimlar_yorum", [])])
    return "\n".join(s)


def kaydet(mac: dict, iddialar: list[Iddia], gorusler: list[DisGorus], hedef: Path,
           aramalar: list[dict] | None = None) -> dict:
    """Ham iddia/görüş kayıtları + arama günlüğü (sorgu, zaman, tur, sonuç) + SHA-256."""
    hedef.mkdir(parents=True, exist_ok=True)
    govde = {"mac": mac, "iddialar": [i.kayit() for i in iddialar], "gorusler": [asdict(g) for g in gorusler],
             "arama_gunlugu": aramalar or [],
             "kayit_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    b = json.dumps(govde, ensure_ascii=False, sort_keys=True, indent=1).encode()
    (hedef / "arastirma.json").write_bytes(b)
    oz = hashlib.sha256(b).hexdigest()
    (hedef / "arastirma.sha256").write_text(oz)
    return {"yol": str(hedef / "arastirma.json"), "sha256": oz}


def sinif_kaydi(yol: Path = SINIF_DOSYASI) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8")) if Path(yol).exists() else {"hostlar": {}}


def kaynak_sinifi(url: str, kayit: dict | None = None) -> str:
    return (kayit or sinif_kaydi())["hostlar"].get(host(url), "bilinmeyen")


def sayfa_acilabilir_mi(url: str) -> tuple[bool, str]:
    """Okuma izni yalnızca haber_kaynaklari.json 'kullanilabilir' sınıfından gelir; diğerleri kapalı (varsayılan)."""
    from .kaynak import KaynakKaydi
    h = host(url)
    if h in YASAK_HOSTLAR:
        return False, "bahis sitesi (MK-1)"
    k = KaynakKaydi.yukle()
    if k.okunabilir_mi(h):
        return True, "haber_kaynaklari.json: kullanilabilir"
    not_ = sinif_kaydi().get("otomatik_okuma_notlari", {}).get(h)
    return False, not_ or "koşullar/robots bu host için denetlenmedi: yalnızca arama özeti + bağlantı"
