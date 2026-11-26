# Katman 2 — Güncel ve tarihsel haber araştırması: teknik tasarım (taslak, 24.11.2026)

Durum: **İLK UYGULAMA (25.11.2026)** — `lib/fi/haber/` (kaynak kaydı ve uyum sınıflandırması, iki işaretle kulüp
kimliği, güvenli okuyucu, yayın zamanı ↔ başlama karşılaştırması, yapılandırılmış kanıt + durum kayıtları, tarihsel/güncel
oturumlar) ve `veri/haber_kaynaklari.json` (40 host). Testler: `tests/test_haber.py` (ağsız). Haberler modele OTOMATİK
GİRMEZ; nicel etki her zaman "hesaplanamaz". Aşağıdaki tasarımdan farkı: aynı gün saati doğrulanmamış içerik
maç öncesi DOĞRULANMIŞ kanıt sayılmaz (durum kaydı olur). Bu belge `docs/VERI_KAYNAKLARI.md` "İki katmanlı mimari"
bölümünün ve `lib/fi/model/DURUM_WIP.md` içindeki "Sonraki aşama kapsamı" maddesinin teknik karşılığıdır.

## 1. Amaç ve sınırlar
- **Amaç:** Belirli bir maç için maç öncesinde bilinebilen takım istihbaratını toplamak, kaynağıyla birlikte kaydetmek
  ve hangi tahmini etkileyebileceğini işaretlemek. Toplanan bilgiler:
  - kadro, sakatlık, ceza;
  - antrenman, rotasyon, yorgunluk, seyahat;
  - teknik direktör açıklamaları;
  - taktik eşleşme, motivasyon.

  Ayrıca favorinin neden kazanamayabileceği bilinçli olarak araştırılır (karşı senaryo).
- **Sınırlar:**
  - MK-1: Nesine ve bahis içerikleri kaynak olamaz. `kanit.py` bunu zaten reddediyor.
  - Toplu tarama ya da kazıma yok. Bot koruması ve giriş duvarı aşılmaz, tarayıcı taklidi yapılmaz.
  - Ücretli API kullanılmaz.
  - Doğrulanmış bir etki modeli olmadan haberden olasılık üretilmez.

## 2. Kaynak katmanları ve güvenilirlik
| Seviye (`kanit.DOGRULAMA`) | Kaynak türü | Örnek | Kullanım |
|---|---|---|---|
| `resmi` | Kulüp, lig ya da federasyonun kendi sitesi, resmî basın toplantısı dökümü, resmî kadro listesi | kulüp sitesi, lig sitesi, UEFA/FIFA | Doğrudan kanıt |
| `cok_kaynak` | İki bağımsız, saygın medya kaynağının aynı bilgiyi vermesi | ulusal spor basını + takım muhabiri | Kanıt |
| `tek_kaynak` | Tek bir saygın medya kaynağı | yerel gazete, takım muhabiri | Kanıt; "tek kaynak" diye işaretlenir |
| `tahmin` | Muhtemel 11, söylenti, "bekleniyor" | önizleme yazıları | Yalnızca nitel not |
| `dogrulanamadi` | Aranıp doğrulanamayan, yayın zamanı belirsiz | — | Değer taşımaz |

**Sosyal medya (X, Reddit, taraftar forumları):** Yalnızca **haber adayı** üretir. Bir aday ancak `resmi`, `cok_kaynak`
ya da `tek_kaynak` düzeyinde bir kaynakla teyit edilirse kanıt olur. Bunun tek istisnası kulübün kendi doğrulanmış
hesabıdır; onun gönderisi `resmi` sayılır. Giriş gerektiren içerik okunmaz.

**Arama motoru özeti hiçbir seviyede kanıt değildir.** Özet yalnızca hangi sayfanın okunacağını gösterir. Bu projede
bir özetin maç sonucunu yanlış verdiği ve maç sonrası bilgi içerdiği görüldü (bkz. `VAKA_RAPORU.md`).

## 3. Zaman kuralları (sızıntı önleme)
- Her araştırmanın bir **kesim zamanı** vardır:
  - güncel maçta araştırma ve dondurma anı;
  - tarihsel maçta maç başlama saati (UTC).
- Kanıt olarak yalnızca **yayın zamanı kesimden önce olduğu orijinal sayfadan doğrulanan** içerik kullanılır. Yayın zamanının okunduğu yerin önceliği:
  1. sayfanın görünür tarih ve saati;
  2. sayfa üst verisi (`article:published_time`, JSON-LD `datePublished`);
  3. arşiv kopyası (ör. Wayback Machine; ayrı host izni gerekir).

  Bunların hiçbiri yoksa kanıt `dogrulanamadi` olur.
- **Güncellenmiş haber** (`dateModified` kesimden sonra): Yalnızca kesimden önceki sürüm doğrulanabiliyorsa kullanılır, ör. arşiv kopyasıyla. Doğrulanamıyorsa maç öncesi analizde kullanılmaz.
- **Tarihsel vakalar:** Maç sonrası haberler, maç raporları, kırmızı kart, penaltı ve maç içi sakatlık **maç öncesi analize hiç girmez**. Bunlar ayrı bir "maç sonrası açıklama" bölümünde tutulur.
- **Önyargı uyarısı:** Sonucu bilinen maçlarda araştırma yapan kişi sonucu bilir. Bu yüzden tarihsel vakalar
  bağımsız kör test sayılmaz. Arama sorguları sonuca göre değil, sabit bir kontrol listesine göre yapılır (bkz. 6).

## 4. Kanıt şeması (öneri — `kanit.Kanit` genişletmesi, henüz uygulanmadı)
Mevcut alanlar korunur: `mac_id`, `konu`, `iddia`, `deger`, `kaynak_adi`, `kaynak_url`, `erisim_zamani`, `dogrulama`, `yayin_tarihi`, `takim`, `ham_sha256`, `notlar`. Önerilen ek alanlar:

| Alan | Açıklama |
|---|---|
| `yayin_zamani` | ISO, saat dilimli (yalnızca gün değil) |
| `yayin_zamani_kaynagi` | `sayfa_metni` / `sayfa_ust_verisi` / `arsiv` / `dogrulanamadi` |
| `kesim_zamani` | Araştırmanın kesim anı; `yayin_zamani < kesim_zamani` zorunlu denetim |
| `kaynak_turu` | `resmi_kulup`, `resmi_lig`, `ulusal_basin`, `yerel_basin`, `muhabir`, `sosyal_medya_aday` |
| `kategori` | `sakatlik`, `ceza`, `kadro`, `ilk11_beklenen`, `ilk11_kesin`, `antrenman`, `rotasyon`, `yorgunluk`, `seyahat`, `td_aciklama`, `oyuncu_aciklama`, `motivasyon`, `taktik`, `karsi_senaryo` |
| `etki` | `{takim, oyuncu?, yon: olumsuz/olumlu/belirsiz, etkilenen_tahminler: ["1X2","gol_beklentisi","kg","alt_ust"], nicel: "hesaplanamaz"}` |
| `teyit` | Bu bilgiyi teyit eden diğer kanıtların kimlikleri (`cok_kaynak` için zorunlu) |
| `sayfa_sha256` | Okunan sayfa metninin özeti; içerik sonradan değişirse fark edilir |

Ek denetimler önerilir:
- Kesimden sonra yayımlanan içerik reddedilir.
- `cok_kaynak` en az iki farklı yayıncı alan adı ister.
- `sosyal_medya_aday` en fazla `tahmin` seviyesinde olabilir.
- Nesine ya da bahis alan adları reddedilir (mevcut kural).

## 5. Bileşenler ve akış
1. **Maç dosyası.** Maç kimliği, takımlar, başlama saati (UTC) ve kesim zamanı belirlenir. Bağımsız model tahmini (Katman 1) **önce** üretilir ve SHA-256 ile dondurulur.
2. **Sorgu planı.** Sabit kontrol listesinden (bölüm 6) sorgular üretilir: takım adı + kategori + yerel dil. Örnek: "Bayern injury update", "Bayern Verletzung", "Pressekonferenz". Maç başına arama ve sayfa okuma bütçesi sınırlıdır; ilk öneri 8 arama ve 10 sayfa.
3. **Arama.** Claude'un web arama aracı kullanılır. Sonuçlar yalnızca aday URL listesidir.
4. **Sayfa okuma.**
   - Yalnızca izin listesindeki hostlar okunur. Yeni bir host için kullanıcıya tek seferlik izin önerilir. İlk okumada o hostun `robots.txt` dosyası ve kullanım koşulları kaydedilir.
   - Koşullar veritabanı kurmayı ya da yeniden kullanımı yasaklıyorsa, örneğin premierleague.com, o kaynaktan **içerik saklanmaz**; yalnızca URL ve kısa iddia tutulur. Gerekirse kaynak hiç kullanılmaz.
5. **Çıkarım.** Claude sayfadan iddiayı, yayın zamanını ve kategoriyi çıkarır. Uzun alıntı yapılmaz, kısa iddia cümlesi yazılır. Telif nedeniyle sayfa metni depoya kopyalanmaz; yalnızca özeti (`sayfa_sha256`) tutulur.
6. **Teyit.** Aynı iddia için ikinci bir bağımsız kaynak aranır ve seviye buna göre atanır.
7. **Karşı senaryo.** Favorinin kazanamamasını açıklayabilecek her kategori için en az bir sorgu yapılır. Bulunamayan kategori "aranmadı" değil, "aranıp bulunamadı" diye kaydedilir.
8. **Dondurma.** Haber kanıtları JSONL olarak yazılır ve dosya SHA-256 ile zaman damgasıyla dondurulur. Nesine fiyat karşılaştırması ancak bundan sonra açılabilir (MK-1).
9. **Rapor.** Her önemli bilgi için kaynak URL'si, yayın zamanı, doğrulama seviyesi ve hangi tahmini etkileyebileceği yazılır. Model olasılıkları haberle **değiştirilmez**; yanlarına "haber etkisi: hesaplanamaz (doğrulanmış etki modeli yok)" notu düşülür.

## 6. Sabit kontrol listesi (her maç, iki takım için)
- Resmî kulüp ve lig açıklamaları: sakatlık raporu, ceza listesi, kadro.
- Basın toplantısı: teknik direktörün oyuncu durumu, rotasyon ve motivasyon üzerine sözleri.
- Ceza durumu: kart birikimi, kırmızı kart cezası.
- Antrenman raporları (son 48 saat).
- Fikstür ve yorgunluk: son 10 günde kupa ve Avrupa maçları (Katman 1'de veri yok), uzun seyahat, milli ara dönüşü.
- Motivasyon: puan ihtiyacı (şampiyonluk, Avrupa, düşme), derbi, önemli maç öncesi rotasyon.
- Taktik eşleşme: rakibin oyun tarzı, favorinin zorlandığı profil (yalnızca kaynaklı analiz).
- Sosyal medya adayları (yalnızca teyit için iz).
- Karşı senaryo özeti.

## 7. Modele etki: ileride ve ancak doğrulamayla
Haberler nitel nottan sayısal girdiye ancak şu sırayla geçebilir:
1. **Yapılandırılmış ve tarihsel veri gerekir.** Örnek: oyuncu dakikaları ve kesin ilk 11'ler. Bu veri şu an elimizde yok; lisanslı ve ücretsiz bir kaynak araştırılmalı. Haber metinlerinden geçmişe dönük veri üretmek tutarlı ve sızıntısız olmaz.
2. **Önceden kayıtlı hipotez gerekir.** Örnek: "ilk 11'de Elo katkısı yüksek 2+ oyuncu eksik → favori kazanma olasılığı düşer".
3. **Kronolojik backtest ve kalibrasyon gerekir.** Değerlendirme dokunulmamış bir dönem ya da ligde yapılır, ileriye dönük test ayrıca yapılır.
4. Ancak bundan sonra bir düzeltme katsayısı önerilir ve kullanıcı onayıyla modele eklenir.

Oranlardan türetilmiş bilgi bu sürecin hiçbir adımına girmez (MK-1).

## 8. İzinler ve uyum
- **Web arama:** Ortam iznine tabi değil.
- **Sayfa okuma:** Her host kullanıcı onayıyla izin listesine eklenir. Liste şu an bülten, istatistik ve federasyon hostları ile `en.wikipedia.org`'dan oluşuyor.
- **Önerilecek ilk hostlar:** Lig başına 1–2 resmî kaynak (lig ve kulüp siteleri) ve 1–2 ulusal yayın. Her biri için önce kullanım koşulları okunur ve kaydedilir.
- **Kişisel veri:** Oyuncu sağlık bilgisi yalnızca kamuya açıklanmış haliyle ve maç bağlamında tutulur. Taraftar hesaplarının kişisel bilgileri saklanmaz.

## 9. Testler (uygulama aşamasında yazılacak)
- Kesimden sonra yayımlanan kanıt reddedilir.
- Yayın zamanı kaynağı `dogrulanamadi` olan kanıt maç öncesi rapora "kanıt" olarak giremez.
- Sosyal medya adayı tek başına `tek_kaynak` veya üstü olamaz.
- `cok_kaynak` için iki farklı yayıncı alan adı gerekir.
- Nesine ya da bahis alan adları reddedilir.
- Model olasılık dosyası haber kanıtlarından önce dondurulmuş olmalıdır (zaman damgası sırası).

## Geniş (açık internet) araştırma — `lib/fi/haber/genis.py` (26.11.2026)
Kullanıcı talimatıyla haber araştırması resmî sitelerle sınırlı değildir: ulusal/yerel basın, muhabirler, basın
toplantıları, istatistik platformları, bağımsız analistler, önizleme/tahmin siteleri ve topluluklar (Reddit vb.).
- **Sınıf ≠ izin.** `veri/genis_kaynak_siniflari.json` yalnızca kaynak türünü (A resmî · B basın/ajans/muhabir/
  istatistik · C analist/önizleme · D forum/bilinmeyen · E arama özeti) verir. Sayfa ancak `haber_kaynaklari.json`'da
  `kullanilabilir` ise açılır; diğerlerinde web arama özeti + bağlantı + zaman saklanır. Koruma/koşul aşılmaz;
  uzun metin kopyalanmaz (özet ≤ 300 karakter).
- **Kanıt zinciri:** aynı ilk kaynak ya da yayıncı grubu = tek zincir. Düzeyler: resmi · iki_bagimsiz (≥2 zincir, biri
  ≤ B) · dogrulanmadi · celiskili · mac_oncesi_kanit_yok. Arama özeti tek başına doğrulamaz.
- **Zaman turları:** T-24s, T-6s, T-90dk (ilk 11), diger; her kayıtta araştırma zamanı; turlar arası durum değişimi
  raporlanır. Maçtan sonra ya da saatsiz maç günü yayını maç öncesi bilgi sayılmaz.
- **Dış görüş karantinası:** `DisGorus` (beklenen sonuç, sportif gerekçe, sitenin yüzde/oranları) model girdisi olamaz
  (`model_girdisi_denetle`); favori yalnızca bağımsız modelden belirlenir.
- **Rapor:** `mac_raporu` + `rapor_md` → 10 bölüm (madde 8). Bulunamayan bilgi uydurulmaz; arama günlüğü raporda.
- Pilot: `output/arastirma/genis_pilot/sou_mid_20261127/` — 4 arama, bu maça ait güncel haber/önizleme bulunamadı.
