# Football Intelligence V1 — yerel arayüz

## Çalıştırma
```bash
PYTHONPATH=lib python3 -m uygulama --port 8765
```
Tarayıcıda `http://127.0.0.1:8765` açılır. Sunucu yalnızca 127.0.0.1'e bağlanır. İşlem düğmeleri (POST) başka bir kökenden gelen isteği reddeder.

Ek paket gerekmez; yalnızca Python standart kütüphanesi kullanılır. Streamlit ya da Flask kurulu değildir ve proje kuralları paket kurulumunu yasaklar.

## Katmanlar
- `uygulama/` arayüz katmanıdır.
  - `veri.py`: salt okunur veri erişimi.
  - `islemler.py`: mevcut modülleri çağıran işlemler.
  - `sunucu.py`: sayfalar.
- `lib/fi` analiz kütüphanesi olarak kalır. Nesine bülten çekicisine atıf yapmaz (test B6); bülten çekme yalnızca `uygulama/islemler.py` içinden çağrılır.
- Yeni model yoktur. E2, kapsam kaydı, hazırlık kapısı, dondurma, fiyat eşdeğerliği ve haber raporları olduğu gibi kullanılır.

## Sayfalar
| Sayfa | İçerik |
|---|---|
| `/` | Türkiye saatine göre günün maçları (bülten ve gün seçimi). **Oran gösterilmez.** Her maçta bağımsız tahmin durumu: dondurulmuş / hazırlanabilir / hesaplanamaz (neden fareyle üzerine gelince görünür). |
| `/mac/<kod>` | Bölümler: hazırlık kapısı · son 10 maç (football-data.org; yalnızca kesin/onaylı takım eşlemesiyle) · donmuş bağımsız olasılıklar (yalnızca kapsamdaki marketler; diğerleri "hesaplanamaz" ve nedeni) · haberler, sakatlık ve cezalar (doğrulama seviyesiyle) · analistlerin beklentileri, gerekçeleri ve donmuş modelde o skorun olasılığı · sürpriz riskleri (YORUM; olasılığa eklenmez) · fiyat karşılaştırması · eşdeğer marketlerde en yüksek fiyat · analiz raporları |
| `/arsiv` | Donmuş tahminler, SHA-256 bütünlüğü, gerçekleşen skor (football-data.org, normal süre), log-kayıp ve Brier |
| `/arastirma/surpriz` | 10+10 sürpriz pilotu (bilgi ve araştırma bölümü; sinyaller kanıtlanmadı) |

## İşlemler (MK-1 sırası)
1. **Güncel veri çek:** `fi.kaynaklar.guncel.guncelle`. Sonuçlar, son maçlar ve arşiv puanlaması buradan gelir.
2. **Bülten çek:** Yalnızca seçili TR günü, 00:00–23:59 (`--baslangic/--bitis`).
   - `--bugun` ve `--tarih` kullanılmaz: ikisi de pencereyi ertesi gün 03:00'e uzatır, `--bugun` ayrıca gece 03:00'e kadar önceki günü "bugün" sayar.
3. **Bağımsız tahmini hesapla ve dondur:**
   - Yalnızca hazırlık kapısını geçen maçlarda yapılır.
   - Oransız bülten satırı → `lig_guncel` → `bagimsiz_tahmin` → `dondur`.
   - football-data.org maç kimliği aynı UTC dakikası ve iki takımla doğrulanır.
   - Donmuş tahmin yeniden dondurulmaz.
4. **Fiyat karşılaştır:**
   - Yalnızca SHA-256'sı doğrulanmış donmuş tahmin ve dondurmadan **sonra** çekilmiş bülten ile yapılır; maç başladıysa reddedilir.
   - Var olan karşılaştırmanın üzerine yazılmaz.

**Haber araştırması** uygulamada otomatik yapılmaz (ücretsiz ve izinli bir arama API'si yok). Claude oturumunda yapılır, `output/arastirma/genis_pilot/` altına kaydedilir ve arayüz onu okur. Sayfa şu anki turu (T−24s / T−6s / T−90dk) gösterir.

## Gün kuralı
- Seçilen gün = o gün 00:00–23:59 (TR). Ertesi gün 00:00–03:00 arasındaki maçlar dahil edilmez; sayfada sayıları gösterilir.
- Gün seçicide yalnızca bülten penceresinin tamamen kapsadığı günler çıkar. Kısmi bir gün istenirse "Bu gün seçilemez" uyarısı ve o gün için bülten çekme düğmesi gösterilir.
- Varsayılan açılış: bugünü tam kapsayan en yeni bülten.

## Fiyat ve EV gösterimi
- Pozitif EV hiçbir zaman yeşil "avantaj" olarak gösterilmez. Bu satırlar "model–piyasa ayrışması · doğrulama gerekli" olarak ayrılır.
- Neden: piyasaya karşı kazanç ileriye dönük olarak doğrulanmadı, kalibrasyon sınırlı, güncel form ve sezon kayması denetimi yok.

## Haberler
- Sayfada "Manuel araştırma" uyarısı görünür.
- Her iddia için araştırma zamanı, tur, doğrulama seviyesi, kaynak sınıfı, erişim yolu ve yayın zamanı gösterilir.
- Araştırma şu anki turda yapılmadıysa ya da 6 saatten eskiyse **GÜNCEL DEĞİL** rozeti çıkar.

## Hazırlık rozetleri
- **hazırlanabilir:** lig onaylı, model kapsamda ve iki takım eşlemesi kesin.
- **takım onayı gerekli:** en az bir takım adı belirsiz; benzer ada göre otomatik eşlenmez.
- **hesaplanamaz:** lig onayı ya da model yok.

## Deneme kökü
`FI_OUTPUT=<klasör>` verilirse uygulama bütün çıktıları o klasörden okur ve oraya yazar. Bu, gerçek arşive dokunmadan deneme yapmak içindir.

## Doğrulama (26–27.11.2026)
- SOU–MID yeniden üretimi scratchpad'de yapıldı: dondurma → bülten (27.11) → fiyat karşılaştırması.
  - Olasılıklar donmuş tahminle birebir aynı çıktı (en büyük fark 0,0).
  - 238 karşılaştırma satırı, 20 eşdeğer grup.
  - Gerçek arşiv değişmedi.
- Testler:
  - `tests/test_arayuz.py`: birim testleri.
  - `tests/test_arayuz_entegrasyon.py`: ayrı süreçte gerçek HTTP sunucusu. Kapsam: gece yarısı, kısmi gün, MK-1, dondurmalı fiyat gösterimi, geçersiz işlemler (403/404/409), bozulmuş donmuş tahmin.
- Chromium ile yerel sunucuda (127.0.0.1, ayrı `FI_OUTPUT` kopyası) denenenler:
  - dört sayfa;
  - fiyat karşılaştırma, bülten çekme, dondurma (başarılı: Wrexham–Portsmouth; reddedilen: takım onaysız) ve güncel veri düğmeleri;
  - tekrar ve geçersiz istek retleri;
  - 404 sayfası;
  - 390 px telefon genişliği (yatay taşma yok).
