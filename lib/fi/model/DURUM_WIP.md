# DURUM: PROTOTİP TAMAMLANDI — KULLANICI ONAYI BEKLİYOR (main'e alınmadı)

Güncelleme: 24.11.2026. Kapsam: tek lig (İngiltere Premier Lig, OpenFootball `en.1`), yalnızca tarihsel backtest.
Bu modeller canlı tahmin ya da kupon için kullanılmaz; yalnızca geçmiş maçlardaki başarı ölçülür.

## Dosyalar
| Dosya | Durum |
|---|---|
| `lib/fi/kaynaklar/openfootball.py` | OpenFootball okuyucusu + anlık görüntü (commit, dosya SHA-256). Test: D1. |
| `lib/fi/model/__init__.py` | `pazar_destegi()`: korner/kart/oyuncu → "hesaplanamaz". Test: D5. |
| `lib/fi/model/optim.py` | Nelder–Mead, altın oran (scipy yok). Test: D2. |
| `lib/fi/model/elo.py` | Özgün Elo + sıralı lojistik 1X2 (numpy ile vektörleştirildi). Test: D3. |
| `lib/fi/model/goller.py` | Poisson / Dixon–Coles; **ρ sınır hatası DÜZELTİLDİ** (`rho_sinirlari`); `PoissonGorunumu`. Test: D4. |
| `lib/fi/model/metrikler.py` | Log-loss, Brier, RPS, kalibrasyon/ECE, bootstrap, AUC. Test: D6. |
| `lib/fi/model/surpriz.py` | Model favorisine göre sürpriz alarmı, yanlış alarm oranı; favori serisi × rakip gücü. Test: D7. |
| `lib/fi/model/backtest.py` | Yürüyen test motoru, sızıntı denetimleri, MK-1 oran reddi. Test: D5. |
| `lib/fi/model/calistir.py` | Prototip komut satırı (ayar → doğrulama → test → ek test 2026-27). |

## Backtest sonucu (24.11.2026, `en.1`, kullanıcı tarafından kabul edildi)
- Test 2022-23…2025-26 (1.520 maç) log-loss: taban 1,067 · Elo 0,984 · Poisson 0,983 · Dixon–Coles 0,983
  (tabana göre −0,084, %95 GA −0,105/−0,065). Elo/Poisson/Dixon–Coles arasındaki fark ihmal edilebilir.
- Ek test 2026-27 (110 maç, 50'si OpenFootball, 60'ı football-data.org): fark anlamlı değil.
- Bilinen sapmalar: güçlü deplasman favorilerinde aşırı güven (%70–80 tahmin → %61 gerçekleşen, n=33);
  yeni çıkan takımlara karşı aşırı güvenli tahminler; beraberlik hiçbir maçta en olası sonuç değil; 2020-21 ve
  2025-26'da performans düşüşü.

## ⚠ SÜRPRİZ TAHMİNLERİ HENÜZ GÜVENİLİR DEĞİL
Model favorisinin kaybetmesini ayırt etme gücü zayıf (AUC: Dixon–Coles 0,60, Elo 0,64). En iyi eşikte (zayıf tarafın
kazanma olasılığı ≥ %25) 46 alarmın yalnızca 13'ü doğru çıktı (isabet %28, yanlış alarm oranı %72, yakalama %10).
Bu çıktılar sürpriz uyarısı, favori eleme ya da kupon için KULLANILMAMALIDIR. Favori galibiyet serisinin model
olasılığına ek bilgi kattığına dair kanıt bulunamadı (bütün farklar güven aralığı içinde; güçlü rakip grubu n=25).

## Plan: Tarihsel Sürpriz Vakaları (ayrı test bölümü; ana modele eklenmez)
Vaka listesi (kullanıcı tarafından verildi):
1. 22.10.2022 Nottingham Forest 1-0 Liverpool (Premier League)
2. 29.10.2022 Liverpool 1-2 Leeds United (Premier League)
3. 12.11.2022 Manchester City 1-2 Brentford (Premier League)
4. 14.11.2026 Portekiz 1-4 Danimarka (milli takımlar)
5. 14.11.2026 Romanya 2-1 Polonya (milli takımlar)

Protokol:
- **A. Kör test:** analiz zamanı maç başlangıcından önceye sabitlenir; yalnızca o zamana kadarki sonuçlar ve yayın tarihi
  maç öncesi olarak DOĞRULANMIŞ haber/kadro bilgisi kullanılır; sonuç ve maç sonrası içerik girdilerden çıkarılır.
  Elo / Poisson / Dixon–Coles olasılıkları (favori kazanır / beraberlik / favori kaybeder) ayrı gösterilir.
  Milli takım maçları Premier League kulüp modeliyle TAHMİN EDİLMEZ → ayrı, test edilmiş milli takım modeli olmadan
  olasılık "hesaplanamaz".
- **B. Önceden görülebilen işaretler:** favorinin rakip gücüne göre düzeltilmiş son 5–10 maçı, yanıltıcı seri/skorlar,
  eksikler/rotasyon/yorgunluk, motivasyon/fikstür, teknik direktör açıklamaları, rakibin taktik avantajı. Her bilgi
  kaynak + yayın tarihiyle; doğrulanamayan bilgi uydurulmaz.
- **C. Sonuç sonrası:** maç öncesi kayıt önce SHA-256 + zaman damgasıyla dondurulur, sonra sonuç açılır; öngörülebilir
  zayıflıklar ile yalnızca maç sonrası açıklanabilenler ayrılır; aşırı güven ve sürpriz uyarısının doğruluğu raporlanır.
- **D. Örneklem yanlılığı:** bu beş maç yalnızca VAKA ANALİZİDİR; aynı dönemlerden benzer olasılıklı ve sürpriz
  yaşanmayan favori maçları karşılaştırma grubudur; başarı ölçümü yalnızca bütün kronolojik test maçlarında yapılır;
  model bu beş maça göre ayarlanmaz.
- **E. Kurallar:** MK-1 (Nesine oranları yok), gerçek yayın tarihi doğrulaması, eksik veri → "hesaplanamaz", kupon yok.

## Veri bütünlüğü (24.11.2026)
- en.1 2019-20: yılı hatalı 66 maç (Temmuz 2020, kaynakta 2019) okuyucu katmanında kanıtlı kayıtlarla düzeltildi
  (`veri/tarih_duzeltmeleri.json`; kanıt: openfootball/england özgün metnindeki haftanın günü). İkinci bağımsız kaynak
  (resmî Premier League arşivi) ile doğrulama BEKLİYOR — host izni gerekiyor.
- es.1 / it.1 2024-25: skorsuz 38. hafta (10+10 maç) iki kaynağın tam uyuşmasıyla tamamlandı
  (`veri/skor_tamamlamalari.json`; football-data.org + openfootball/espana, openfootball/italy).
- Okuyucu düzeltilmemiş sert tarih tutarsızlığında durur (`VeriTutarsizligi`). Rapor: `output/veri_butunlugu/`.

## SONRAKİ AŞAMA KAPSAMI: Güncel internet araştırması (Katman 2) — KULLANICI GEREKSİNİMİ, UNUTULMAYACAK
Nihai hedefte güncel internet araştırması istatistiksel modelleme kadar önemlidir. Henüz GELİŞTİRİLMEDİ; mevcut veri
düzeltme ve D aşaması tamamlandıktan sonra, kullanıcı onayıyla başlanır.

Kapsam (maç öncesi):
- Resmî kulüp ve federasyon haberleri.
- Yerel ve uluslararası spor basını, takım muhabirleri.
- Sakatlıklar, cezalılar, kadro, beklenen ve kesin ilk 11.
- Son antrenmanlar, seyahat, rotasyon, yorgunluk.
- Teknik direktör ve oyuncu açıklamaları.
- Motivasyon, puan ihtiyacı, fikstür yoğunluğu.
- Rakiplerin oyun tarzı ve taktik eşleşmeler.
- X, Reddit ve taraftar forumlarındaki doğrulanabilir haber ADAYLARI (tek başına kanıt değildir).
- Karşı senaryo: favorinin neden kazanamayabileceğine dair özel araştırma.

Kayıt kuralları (her önemli bilgi için `Kanit` kaydı):
- Kaynak URL'si, yayın zamanı (orijinal sayfadan doğrulanmış), erişim zamanı, doğrulama düzeyi, hangi tahminleri
  etkileyebileceği (ör. 1X2, gol beklentisi, belirli takımın hücum/savunması).
- Arama motoru özetleri ASLA kanıt sayılmaz; resmî kaynak ve orijinal haber metni mümkün olduğunca doğrulanır.
  Sayfa okumak için gereken her host kullanıcı onayıyla açılır; bot koruması/erişim engeli aşılmaz.
- Maç öncesi kayıt, sonuç görülmeden SHA-256 + zaman damgasıyla dondurulur.

Modele etki (yalnızca yazılı rapor değil):
- Yeterli veri ve geçmiş doğrulama olduğunda haber kategorilerinin (ör. kilit oyuncu eksikliği, rotasyon) model
  tahminleri üzerindeki etkisi kronolojik backtest ve kalibrasyonla ölçülür; doğrulanmadan modele eklenmez.
- Doğrulanmış etki modeli yokken haber yalnızca nitel not olarak raporlanır; olasılık uydurulmaz.
- MK-1 geçerli: olasılıklar Nesine oranlarından bağımsız üretilir; oranlar ancak tahmin dondurulduktan sonra açılır.

## SONRAKİ AŞAMA KAPSAMI: Alt Ligler ve Özel Marketler Altyapısı — KULLANICI GEREKSİNİMİ (mimari; henüz uygulanmadı)
Nihai hedef: Nesine bültenindeki mümkün olduğunca çok lig ve pazar. Yeni lige veri çekme ya da model geliştirme, ayrı
onay olmadan başlamaz; Katman 2 haber pilotu (16 maç) önceliğini korur.

Gereksinimler:
1. **Modüler kaynak sistemi.** Her kaynak bir bağdaştırıcıdır (mevcut `kaynaklar/` düzeni). Her lig × kaynak için ayrı
   bir yeterlilik kartı tutulur:
   - kapsanan sezonlar, maç sayısı, skor ve ilk yarı oranı;
   - korner, kart, oyuncu, olay dakikası alanlarının bulunup bulunmadığı;
   - güncellik (son maç tarihi, gecikme);
   - bilinen eksikler ve tutarsızlıklar (tarih denetimi, `VeriTutarsizligi`).
2. **Ayrı matematiksel olay tanımları.** Her pazar, maçın sonuç değişkenleri üzerinde bir olay olarak tanımlanır. Gol
   ve devre pazarları skor ile iki devre skorunun ortak dağılımı üzerinde tanımlanır (ilk yarı / ikinci yarı gol
   istatistikleri SONRAKİ AŞAMADA ÖNCELİKLİ). Ayrıca korner, kart, oyuncu
   (gol, asist, kart), zaman aralığı (ör. 0–15. dakika golü) ve birleşik pazarlar (ör. MS + Alt/Üst, İY/MS) için ayrı
   olay tanımları vardır. Nesine pazar sözlüğü (`market_sozlugu_v3.json`, 104 kod) bu olay tanımlarına eşlenir.
   Eşlenemeyen kod "tanımsız" sayılır.
3. **Veri gereksinimleri tablosu.** Pazar → gereken istatistikler → en az veri miktarı (maç, sezon) → doğrulanmış model
   gerekip gerekmediği. Örnekler:
   - İY/MS → devre skorları;
   - korner → takım başına korner sayıları;
   - oyuncu → dakika, ilk 11 ve olay verisi.
4. **Hesaplanamaz.** Gereksinim karşılanmıyorsa ya da modelin geçmiş kalibrasyonu yoksa sonuç "hesaplanamaz" olur
   (`model.pazar_destegi` genişletilir). Olasılık uydurulmaz.
5. **Belirsizlik ayrıca ölçülür.** Kaynaklar: az maç, yeni ya da düşen takım, kadro belirsizliği, eksik haber.
   - Parametre belirsizliği bootstrap/posterior ile, model belirsizliği alternatif modellerin farkıyla ölçülür.
   - Raporda olasılık aralığı ve bir "veri yeterliliği" düzeyi verilir. Aralık çok genişse "hesaplanamaz" denir.
   - Belirsizlik kalibrasyonu da backtest'le denetlenir.
6. **Olay ailesine göre ayrı modeller ve pazarlar arası tutarlılık (kullanıcı düzeltmesi, 25.11.2026).**
   - Gol, korner, kart ve oyuncu pazarları doğrulanmamış TEK bir olasılık dağılımından hesaplanmaz.
   - Her olay ailesinin kendi modeli vardır ve her model o aile için ayrıca backtest ve kalibrasyonla doğrulanır:
     - gol: skor ve devre skoru modeli;
     - korner: sayım modeli;
     - kart: sayım/hakem etkili model;
     - oyuncu: dakika ve olay modeli.
   - Aile içindeki pazarlar o ailenin ortak dağılımından türetilir. Örnekler: MS, Alt/Üst ve İY/MS gol modelinden;
     korner Alt/Üst ve handikap korner modelinden.
   - Aileler arası birleşik pazarlarda (ör. MS + korner Alt/Üst, oyuncu golü + MS) bağımlılık ayrıca modellenir ve
     doğrulanır (ör. kopula ya da ortak gizli değişken, ortak geçmiş veriden kestirilmiş korelasyon). Doğrulanmış bir
     bağımlılık modeli yoksa birleşik pazar "hesaplanamaz" olur. Bağımsızlık varsayılmaz.
   - Otomatik matematiksel tutarlılık denetimleri:
     - tamamlayıcı olayların toplamı 1;
     - alt küme olayın olasılığı üst küme olaydan büyük değil (ör. 2-1 ≤ MS1);
     - birleşik pazar olasılığı en fazla, içerdiği her tek pazarın olasılığı kadar (Fréchet sınırları:
       max(0, P(A)+P(B)−1) ≤ P(A∩B) ≤ min(P(A), P(B)));
     - aynı olayın farklı ailelerdeki tahminleri (ör. gol modelinden ve oyuncu modelinden "takım gol atar") birbiriyle
       karşılaştırılır; uyumsuzluk raporlanır.
7. **MK-1.** Bütün olasılıklar Nesine oranlarından tamamen bağımsız hesaplanır. Oran alanı içeren girdi model ve
   kanıt katmanında reddedilir (mevcut `girdi.oransiz_mi` ve `kanit` denetimleri genişletilir).
8. **Dondur, sonra karşılaştır.** Tahmin SHA-256 ve zaman damgasıyla dondurulduktan SONRA fiyat karşılaştırması yapılır
   (model olasılığı ve fiyattan türetilen oran yan yana). Fiyat oranları gerçek ya da koşullu olasılık olarak sunulmaz;
   modeli düzeltmek için kullanılmaz.
9. **Genişleyebilirlik.** Yeni lig ya da pazar eklemek yalnızca şu adımları gerektirir: yeni kaynak bağdaştırıcısı,
   yeterlilik kartı, olay tanımı ve gereksinim satırı. Ardından o lig ya da pazar için ayrı bir backtest yapılır.
   Kapsam tablosu otomatik üretilir.
10. **Kaynak künyesi.** Her kaynak için kaydedilir:
    - lisans ve yeniden kullanım izni (erişim izninden ayrı);
    - kullanım koşullarının okunma tarihi;
    - güncellik;
    - kapsanan lig ve sezonlar;
    - bilinen eksikler.

    Mevcut `docs/VERI_KAYNAKLARI.md` lig boşluk tablosu bu künyeye taşınır.

Öncelik sırası (öneri):
1. **Önce, haber pilotuyla çakışmadan:** olay tanımları, pazarlar arası tutarlılık denetimleri ve "hesaplanamaz"
   kuralının genişletilmesi. Bunlar mevcut veriyle (4 lig, skor ve ilk yarı) yapılabilir. İlk yarı ve ikinci yarı gol
   aşamasıyla birleşir: İY/MS, devre Alt/Üst, "hangi yarı daha çok gol".
2. **Kaynak künyesi ve lig yeterlilik kartları:** Mevcut kaynaklar için (OpenFootball, football-data.org, OpenLigaDB,
   martj42). Ağ isteği gerekmez.
3. **Nesine bültenindeki liglerin kapsam eşlemesi:** Bülten ligleri kaynak kartlarına eşlenir; hangi ligde hangi
   pazarın hesaplanabileceğini gösteren bir matris çıkar.
4. **Belirsizlik ölçümü:** Önce 4 büyük ligde; ardından düşük veri koşullarının simülasyonu (az maç, yeni takım).
5. **Yeni alt lig verisi** (kullanıcı onayıyla): OpenFootball'daki ikinci ligler (en.2, de.2, es.2, it.2 vb.) lisans
   açısından en kolay aday. Her biri için ayrı backtest.
6. **Korner, kart ve oyuncu pazarları:** Lisans açısından uygun, ücretsiz ve yapılandırılmış bir kaynak bulunana kadar
   "hesaplanamaz". Kaynak araştırması ayrı onayla yapılır.

## Doğrulanmamış varsayımlar
- Yeni çıkan takım önseli: hücum ×0.8, savunma ×1.2 (gol modeli); Elo'da düşen takımların ortalaması.
- Sıralı lojistik yeniden kestirimi için en az 200 geçmiş maç eşiği.
- Ceza katsayısı (2.0) ve 3 yıllık pencere ayarlanmadı; yalnızca ξ ve Elo (K, ev avantajı, sezon çekimi) ayar döneminde seçildi.
- Elo yalnızca lig maçlarını görür (kupa/Avrupa maçları yok); kadro, sakatlık, haber bilgisi yok.

## Kurallar
MK-1: Nesine oranları hiçbir model girdisine giremez (backtest motoru oran alanlı girdiyi reddeder).
