"""Kanıt kaydı: araştırmada kullanılan her iddia kaynağıyla birlikte saklanır.

Bir kanıt; maç kimliği, konu, iddia metni, değer, kaynak adı ve URL'si, yayın tarihi, erişim zamanı, doğrulama
seviyesi ve (istatistiklerde) ölçüm dönemi taşır. Kaynağı olmayan bir sayı kayda giremez. Bahis oranları ve
bahis piyasası verileri bu kayda HİÇ giremez (oranlar yalnızca sonradan, dondurulmuş tahminle karşılaştırılır).

Depo JSON Lines biçimindedir ve yalnızca eklenir (append-only); aynı kanıt iki kez yazılmaz.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

# Doğrulama seviyeleri (güçlüden zayıfa)
DOGRULAMA = {
    "resmi": "kulüp, lig ya da federasyonun kendi açıklaması / resmî veri",
    "veri_kaynagi": "yapılandırılmış istatistik kaynağı (ör. ClubElo, football-data.co.uk)",
    "cok_kaynak": "en az iki bağımsız medya kaynağı",
    "tek_kaynak": "tek bir medya kaynağı",
    "tahmin": "tahmini bilgi (ör. muhtemel 11)",
    "hesaplandi": "başka kanıtlardan hesaplandı (turetildigi alanı zorunlu)",
    "dogrulanamadi": "aranıp doğrulanamadı; değer taşımaz",
}

# Oran / bahis piyasası verisi kanıt kaydına giremez
YASAK_KONULAR = {"oran", "oranlar", "bahis", "bahis_piyasasi", "piyasa_olasiligi", "kupon"}
YASAK_HOSTLAR = {"cdnbulten.nesine.com", "bulten.nesine.com", "www.nesine.com", "nesine.com"}
YASAK_ANAHTARLAR = {"oran", "oran_ham", "odds", "fair_pct", "implied_pct", "market_implied", "mbs", "mac_mbs"}


class KanitHatasi(ValueError):
    pass


def _iso(deger, alan: str, gerekli: bool = False):
    if deger in (None, ""):
        if gerekli:
            raise KanitHatasi(f"'{alan}' zorunlu")
        return None
    try:
        if len(str(deger)) == 10:
            date.fromisoformat(str(deger))
        else:
            datetime.fromisoformat(str(deger))
    except ValueError:
        raise KanitHatasi(f"'{alan}' ISO tarih değil: {deger!r}")
    return str(deger)


def _karsilastirilabilir(s: str) -> str:
    return s[:10] if s else s


def _yasak_anahtar_ara(o, yol="deger"):
    if isinstance(o, dict):
        for k, v in o.items():
            if str(k).casefold() in YASAK_ANAHTARLAR:
                raise KanitHatasi(f"oran/bahis alanı kanıta giremez: {yol}.{k}")
            _yasak_anahtar_ara(v, f"{yol}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _yasak_anahtar_ara(v, f"{yol}[{i}]")


@dataclass
class Kanit:
    mac_id: str                    # ör. "nesine:3318905" ya da "genel" (maça bağlı olmayan kaynak verisi)
    konu: str                      # ör. "elo", "form", "sakatlik", "kadro", "hakem", "haber", "istatistik"
    iddia: str                     # insan okunur cümle
    deger: object                  # sayı, metin ya da küçük JSON yapısı
    kaynak_adi: str
    kaynak_url: str | None
    erisim_zamani: str             # ISO, saat dilimli
    dogrulama: str
    yayin_tarihi: str | None = None
    olcum_baslangic: str | None = None
    olcum_bitis: str | None = None
    birim: str | None = None
    takim: str | None = None       # kaynaktaki takım adı
    ham_sha256: str | None = None  # kaynak yanıtının özeti (önbellek dosyasıyla eşleşir)
    turetildigi: list = field(default_factory=list)   # hesaplanan kanıtların dayandığı kanıt kimlikleri
    notlar: str | None = None
    kimlik: str | None = None

    def dogrula(self) -> "Kanit":
        for a in ("mac_id", "konu", "iddia", "kaynak_adi"):
            if not str(getattr(self, a) or "").strip():
                raise KanitHatasi(f"'{a}' boş olamaz")
        if self.konu.casefold() in YASAK_KONULAR:
            raise KanitHatasi(f"'{self.konu}' konusu kanıt kaydına giremez (oranlar modelin girdisi değildir)")
        if self.dogrulama not in DOGRULAMA:
            raise KanitHatasi(f"geçersiz doğrulama seviyesi: {self.dogrulama!r} (geçerli: {', '.join(DOGRULAMA)})")
        _iso(self.erisim_zamani, "erisim_zamani", gerekli=True)
        _iso(self.yayin_tarihi, "yayin_tarihi")
        _iso(self.olcum_baslangic, "olcum_baslangic")
        _iso(self.olcum_bitis, "olcum_bitis")
        if self.yayin_tarihi and _karsilastirilabilir(self.yayin_tarihi) > _karsilastirilabilir(self.erisim_zamani):
            raise KanitHatasi("yayın tarihi erişim zamanından sonra olamaz")
        if self.olcum_baslangic and self.olcum_bitis and \
                _karsilastirilabilir(self.olcum_baslangic) > _karsilastirilabilir(self.olcum_bitis):
            raise KanitHatasi("ölçüm başlangıcı bitişten sonra olamaz")
        if self.dogrulama == "hesaplandi":
            if not self.turetildigi:
                raise KanitHatasi("'hesaplandi' kanıtı dayandığı kanıtları (turetildigi) belirtmeli")
        elif not self.kaynak_url:
            raise KanitHatasi("kaynak URL'si olmayan kanıt yalnızca 'hesaplandi' olabilir")
        if self.kaynak_url:
            u = urllib.parse.urlparse(self.kaynak_url)
            if u.scheme not in ("http", "https") or not u.hostname:
                raise KanitHatasi(f"geçersiz kaynak URL'si: {self.kaynak_url!r}")
            if u.hostname.casefold() in YASAK_HOSTLAR:
                raise KanitHatasi("Nesine bülteni kanıt kaynağı olamaz (oranlar modelin girdisi değildir)")
        if self.dogrulama == "dogrulanamadi":
            if self.deger not in (None, ""):
                raise KanitHatasi("'dogrulanamadi' kanıtı değer taşıyamaz (sayı uydurma yasağı)")
        elif self.deger in (None, ""):
            raise KanitHatasi("değeri olmayan kanıt yalnızca 'dogrulanamadi' olabilir")
        _yasak_anahtar_ara(self.deger)
        return self

    def kimlik_hesapla(self) -> str:
        d = asdict(self)
        d.pop("kimlik", None)
        return hashlib.sha256(json.dumps(d, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]


class KanitDeposu:
    """JSON Lines kanıt deposu. Yalnızca ekler; aynı içerik ikinci kez yazılmaz."""

    def __init__(self, yol: Path):
        self.yol = Path(yol)

    def oku(self) -> list[Kanit]:
        if not self.yol.exists():
            return []
        out = []
        for i, satir in enumerate(self.yol.read_text(encoding="utf-8").splitlines(), 1):
            if satir.strip():
                try:
                    out.append(Kanit(**json.loads(satir)))
                except (TypeError, ValueError) as h:
                    raise KanitHatasi(f"{self.yol.name}:{i} okunamadı: {h}")
        return out

    def ekle(self, k: Kanit) -> str:
        k.dogrula()
        k.kimlik = k.kimlik_hesapla()
        if k.turetildigi:
            mevcut = {x.kimlik for x in self.oku()}
            eksik = [t for t in k.turetildigi if t not in mevcut]
            if eksik:
                raise KanitHatasi(f"turetildigi alanındaki kanıtlar depoda yok: {eksik}")
        if any(x.kimlik == k.kimlik for x in self.oku()):
            return k.kimlik
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(k), ensure_ascii=False, default=str) + "\n")
        return k.kimlik

    def filtrele(self, mac_id: str | None = None, konu: str | None = None, en_az: str | None = None) -> list[Kanit]:
        sira = list(DOGRULAMA)
        out = []
        for k in self.oku():
            if mac_id and k.mac_id != mac_id:
                continue
            if konu and k.konu != konu:
                continue
            if en_az and sira.index(k.dogrulama) > sira.index(en_az):
                continue
            out.append(k)
        return out

    def ozet(self) -> dict:
        ks = self.oku()
        s: dict = {"toplam": len(ks), "dogrulama": {}, "konu": {}}
        for k in ks:
            s["dogrulama"][k.dogrulama] = s["dogrulama"].get(k.dogrulama, 0) + 1
            s["konu"][k.konu] = s["konu"].get(k.konu, 0) + 1
        return s
