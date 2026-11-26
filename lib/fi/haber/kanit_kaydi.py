"""Yapılandırılmış haber kanıtı ve durum kayıtları.

`haber_kaniti(...)` yalnızca şu koşullarda bir fi.kanit.Kanit üretir:
  - kaynak hostu kayıtta 'kullanilabilir' (arama özeti, engelli/belirsiz/doğrulanmamış host kanıt olamaz),
  - zaman durumu 'mac_oncesi_dogrulandi' (maç sonrası, aynı gün saatsiz, tarihsiz, sonradan güncellenmiş reddedilir),
  - kategori tanımlı, nicel etki 'hesaplanamaz' (haberden keyfî olasılık etkisi verilmez).
Aksi halde kanıt yerine bir DurumKaydi döner (raporlanır, değer taşımaz).

Doğrulama seviyesi: kulübün kendi resmî sitesi kendi takımı hakkında → 'resmi'; diğer her şey → 'tek_kaynak'.
'cok_kaynak' yalnızca teyit_et() ile, FARKLI yayıncı gruplarından en az iki maç öncesi kanıt varsa verilir;
aynı grubun siteleri (ör. aynı medya grubunun iki gazetesi) ya da aynı sitenin iki sayfası bağımsız teyit sayılmaz.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..kanit import Kanit
from .kaynak import HostKaydi, KaynakKaydi
from .kimlik import kayitli_alan
from .zaman import GECERLI

KATEGORILER = ("kadro", "ilk11_beklenen", "ilk11_kesin", "sakatlik", "ceza", "td_aciklama", "td_degisimi",
               "td_cezasi", "oyuncu_aciklama", "antrenman", "rotasyon", "yorgunluk", "seyahat", "fikstur",
               "motivasyon", "taktik", "karsi_senaryo")
# Kategori durumları (açıkça ayrılır):
#   aranip_bulunamadi : erişilebilir kaynaklar okundu, bu kategoride bilgi YOK
#   erisim_engeli     : kaynak engelli / koşulları belirsiz / doğrulanmamış (okunmadı)
#   kaynak_yok        : bu takım için kayıtlı ve izinli hiçbir kaynak yok
#   dogrulanamadi     : bilgi bulundu ama doğrulanamadı (video, tarihsiz sayfa, tek işaret …)
#   arastirilmadi     : bu kategori hiç araştırılmadı (bütçe / kapsam dışı)
#   baska_kayitta     : bilgi haber kaydında değil, başka dondurulmuş kayıtta (ör. istatistik/fikstür dosyası)
#   zaman ret kodları : mac_sonrasi, ayni_gun_saat_yok, tarih_yok, guncelleme_mac_sonrasi
DURUMLAR = ("aranip_bulunamadi", "erisim_engeli", "kaynak_yok", "dogrulanamadi", "arastirilmadi", "baska_kayitta",
            "mac_sonrasi", "ayni_gun_saat_yok", "tarih_yok", "guncelleme_mac_sonrasi", "arama_ozeti_kanit_degil")
RET_KODLARI = ("mac_sonrasi", "ayni_gun_saat_yok", "tarih_yok", "guncelleme_mac_sonrasi", "arama_ozeti_kanit_degil")
NICEL_ETKI = "hesaplanamaz"


@dataclass
class DurumKaydi:
    mac_id: str
    kategori: str | None
    durum: str
    aciklama: str
    url: str | None = None
    host: str | None = None

    def __post_init__(self):
        if self.durum not in DURUMLAR:
            raise ValueError(f"geçersiz durum: {self.durum}")


@dataclass
class HaberGirdisi:
    mac_id: str
    mod: str                    # tarihsel | guncel
    kesim_zamani: str
    baslama_utc: str
    kategori: str
    takim: str
    takim_rolu: str             # favori | rakip | ev | deplasman | iki_takim
    iddia: str                  # kendi cümlemizle kısa iddia (alıntı değil)
    url: str
    yayin_zamani: str | None
    yayin_zamani_kaynagi: str
    zaman_durumu: str
    sayfa_sha256: str | None
    etki: dict = field(default_factory=dict)   # {"etkilenen": [...], "yon": ..., "nicel": "hesaplanamaz"}
    kaynak_turu_beyan: str = "sayfa"           # 'arama_ozeti' gelirse reddedilir


def haber_kaniti(g: HaberGirdisi, kayit: KaynakKaydi, erisim_zamani: str) -> Kanit | DurumKaydi:
    import urllib.parse
    host = (urllib.parse.urlparse(g.url).hostname or "").casefold()
    if g.kaynak_turu_beyan != "sayfa":
        return DurumKaydi(g.mac_id, g.kategori, "arama_ozeti_kanit_degil", "arama özeti / ikincil özet kanıt sayılmaz",
                          g.url, host)
    if g.kategori not in KATEGORILER:
        raise ValueError(f"geçersiz kategori: {g.kategori}")
    if g.mod not in ("tarihsel", "guncel"):
        raise ValueError("mod 'tarihsel' ya da 'guncel' olmalı")
    if (g.etki or {}).get("nicel", NICEL_ETKI) != NICEL_ETKI or any(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in (g.etki or {}).values()):
        raise ValueError("haberin nicel olasılık etkisi yalnızca 'hesaplanamaz' olabilir (doğrulanmış etki modeli yok)")
    hk = kayit.get(host)
    if not hk or hk.sinif != "kullanilabilir":
        return DurumKaydi(g.mac_id, g.kategori, "erisim_engeli",
                          f"host '{host}' sınıfı: {hk.sinif if hk else 'kayıtsız'}", g.url, host)
    if g.zaman_durumu != GECERLI:
        aciklama = {"mac_sonrasi": "maç başladıktan sonra yayımlanmış — maç öncesi analize girmez",
                    "ayni_gun_saat_yok": "maç günü yayımlanmış, saati doğrulanamadı — doğrulanmış maç öncesi kanıt değil",
                    "tarih_yok": "yayın tarihi bulunamadı",
                    "guncelleme_mac_sonrasi": "sayfa başlamadan sonra güncellenmiş — mevcut sürüm maç öncesi değil"}
        return DurumKaydi(g.mac_id, g.kategori, g.zaman_durumu, aciklama.get(g.zaman_durumu, g.zaman_durumu), g.url, host)
    resmi = hk.tur in ("resmi_kulup", "resmi_lig", "resmi_federasyon") and (
        hk.tur != "resmi_kulup" or (hk.kulup and g.takim and hk.kulup.casefold() == g.takim.casefold()))
    deger = {"kategori": g.kategori, "takim_rolu": g.takim_rolu, "mod": g.mod, "kesim_zamani": g.kesim_zamani,
             "baslama_utc": g.baslama_utc, "yayin_zamani": g.yayin_zamani, "yayin_zamani_kaynagi": g.yayin_zamani_kaynagi,
             "zaman_durumu": g.zaman_durumu, "sayfa_sha256": g.sayfa_sha256, "kaynak_sinifi": hk.sinif,
             "kaynak_turu": hk.tur, "yayinci_grubu": hk.yayinci_grubu or kayitli_alan(host),
             "etki": {**(g.etki or {}), "nicel": NICEL_ETKI}, "teyit": []}
    return Kanit(mac_id=g.mac_id, konu=g.kategori, iddia=g.iddia, deger=deger, kaynak_adi=hk.host,
                 kaynak_url=g.url, erisim_zamani=erisim_zamani, dogrulama="resmi" if resmi else "tek_kaynak",
                 yayin_tarihi=g.yayin_zamani, takim=g.takim,
                 notlar=f"{g.mod}; kesim {g.kesim_zamani}; yayın kaynağı {g.yayin_zamani_kaynagi}").dogrula()


def bagimsiz_mi(a: Kanit, b: Kanit) -> bool:
    """İki maç öncesi kanıt bağımsız mı? Farklı yayıncı grubu + farklı kayıtlı alan adı gerekir."""
    ga, gb = a.deger.get("yayinci_grubu"), b.deger.get("yayinci_grubu")
    return bool(ga and gb and ga != gb and kayitli_alan(a.kaynak_url) != kayitli_alan(b.kaynak_url))


def teyit_et(kanitlar: list[Kanit]) -> dict:
    """Aynı iddia için kanıt listesi → bağımsız yayıncı grubu sayısı ve önerilen seviye ('cok_kaynak' ≥ 2 grup)."""
    gecerli = [k for k in kanitlar if k.deger.get("zaman_durumu") == GECERLI]
    gruplar = sorted({k.deger.get("yayinci_grubu") for k in gecerli if k.deger.get("yayinci_grubu")})
    seviye = "cok_kaynak" if len(gruplar) >= 2 else (gecerli[0].dogrulama if gecerli else "dogrulanamadi")
    return {"bagimsiz_grup": gruplar, "n_grup": len(gruplar), "onerilen_seviye": seviye,
            "not": "aynı yayıncı grubunun tekrarları tek kaynak sayılır"}


def durum_ozeti(durumlar: list[DurumKaydi]) -> dict:
    out: dict = {}
    for d in durumlar:
        out.setdefault(d.durum, []).append(asdict(d))
    return out
