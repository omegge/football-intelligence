# Aşama raporu — 26.11.2026 (dal: wip/model-prototip, temel a57e9e3)

MK-1 bütün aşamalarda korundu: hiçbir model girdisinde oran yok (D8, LA5, FA4, K7 testleri). Ayrıntılı sayısal çıktılar
`output/` altında (git dışı): `bulten_20261126_030249/esdegerlik/`, `veri_uygunlugu/`, `ligler_arasi/`,
`model/e_asamasi_20261126_161011/`, `model/f_asamasi_20261126_161200/` (v1), `model/f_asamasi_20261126_161302/` (v2),
`model/h_asamasi/`.

## Durum tablosu
| Aşama | Durum | Özet |
|---|---|---|
| A Depo + testler | tamamlandı | a57e9e3, temiz ağaç, 150/150. Tutarsızlık: "104 kodluk sözlük" = 104 kod+çizgi anahtarı; 86 benzersiz market kodu. |
| B Sözlük + eşdeğerlik | tamamlandı (329 için veri bekliyor) | `fi.pazar.esdegerlik`; periyot/doğrulama seviyesi/turnuva kodu alanları; 75 kod arayüz kaydı. 329 aday kaldı. |
| C Veri matrisi | tamamlandı | 27 lig; DK/NO/SE veri yok; korner/şut/xG yok; okuyucu denetimi sütunu. |
| D Ligler arası | kısmi | M1 > B1 (−0,013 log loss, GA [−0,025; −0,001]); büyük-5 farkını eksik veriyor; iki pilot maç hesaplanamaz. |
| E Sonuç/gol | tamamlandı (değerlendirme); model düzeltmesi başlanmadı | Sonuç marketleri taban üstü; toplam gol/KG taban altı ve aşırı yayılmış. |
| F Devre | kısmi | v1 seçilim yanlılığı bulundu → sapma kaydı + v2. Marjinaller tabanı geçmiyor; 1Y KG×2Y KG bağımsızlığı reddedildi. |
| G Korner | veri bekliyor | İzinli korner kaynağı yok (football-data.co.uk pasif). |
| H Kart/hakem | kısmi | Tek sezon, 3 lig: takım/hakem etkisi lig ortalamasını geçmiyor; Nesine kart puanı kuralı doğrulanmadı. |
| I Oyuncu | veri bekliyor | Beklenen 11/süre/şut verisi için izinli kaynak yok; yalnızca 3 '-full' dosyada gol atan/dakika. |
| J Haber/sürpriz | başlanmadı (bu oturumda) | Mevcut haber modülü ve geriye dönük 30+30 set korunuyor; ileriye dönük test yapılmadı. |
| K Tek maç akışı | tamamlandı (iskelet) | `fi.is_akisi`: TR gün filtresi, kapsam, dondurma+SHA-256, sonradan fiyat, EV yalnızca doğrulanmış markette. |
| L İleri doğrulama | kısmi | Dondurma defteri + `ileri_puanla`; henüz gerçek dondurulmuş tahmin yok (güncel veri yok). |

## B — Market sözlüğü ve eşdeğerlik
- **Yapılan değişiklikler:** `lib/fi/pazar/esdegerlik.py` (seçenek → 4 boyutlu devre skoru ızgarasında olay; kesin /
  kontrol gerekli; eşdeğer gruplar, en yüksek oynanabilir fiyat, bölümleme 1/oran toplamı, alt küme fiyat tutarsızlığı);
  `bulten_dogrulama.py` dışa aktarımına `periyot`, `periyot_kaynagi`, `dogrulama_seviyesi`, `turnuva_kodu`;
  `data/market_arayuz_dogrulamalari.json` (arayüz referansıyla adıyla eşleşen 75 kod, referans dosyalarının SHA-256'sı).
- **Veri kaynakları / erişim:** mevcut Nesine çekimi (ham değiştirilmedi) ve kullanıcının arayüz referansı. Yeni istek yok.
- **Gerçek gözlem:** 2 doğrulanmış maç (1.208 seçenek) + bütün bülten 102 maç, 30.262 seçenek (13.388 skor uzayına
  eşlendi: 13.245 kesin, 143 kontrol gerekli). Seçenek adı uyuşmazlığı: 0.
- **Yöntem:** olay = boolean maske; eşdeğerlik = maskelerin birebir eşitliği. "Uzt. Dahil", tam çizgi (iade), adsız,
  korner/kart/oyuncu marketleri eşlenmez. 291 "Olmaz", 777/779 "diğer", 329 aday → kontrol gerekli.
- **Sonuçlar:** Olympiakos–Milan 19, Escaldes–Kopenhag 18 çok marketli eşdeğer grup; ör. 0-0 ≡ 0,5 alt ≡ MS X&1,5 alt ≡
  MS X&KG yok (+ İlk gol Olmaz, kontrol gerekli); 1-1 ≡ 2,5 alt&KG var; MS X&2,5 üst ≡ MS X&3,5 üst. Alt küme fiyat
  tutarsızlığı: 0 ve 9 (bütün bülten 126) — arbitraj/+EV olarak nitelenmez.
- **Riskler:** kapsam (90 dk) varsayımdır, Nesine kural metni okunmadı. 329 ikinci arayüz doğrulaması bekliyor.
- **Testler:** PE1–PE15.

## C — Veri uygunluğu
- `lib/fi/kaynaklar/uygunluk.py` (yalnızca yerel önbellek). Matris: `output/veri_uygunlugu/MATRIS.md`.
- OpenFootball son skorlu maç 2026-09-20 (8 lig), alt liglerde 2025-11; Türkiye 2021–24 yok; İsviçre 2021'de bitiyor.
- **Bulunan hata:** okuyucu, İskoçya/Avusturya/İsviçre/Macaristan liglerini (aynı eşleşme 2 kez evde) ve UEFA
  kupalarını (grup + eleme tekrarı) hiç okuyamıyordu. Düzeltme: lig biçimi üst sınırı + kupa aşaması kuralı (LA6–LA7).
  Kalan gerçek tarih hataları (en.2/at.1/at.2 2019-20, en.3 2025-26) düzeltilmedi; o sezonlar kullanılmıyor.
- OpenLigaDB: 6 adil kullanım isteği (bkz. VERI_KAYNAKLARI.md).

## D — Ligler arası güç
- `lib/fi/model/ligler_arasi.py` (ön kayıt docstring'de; tek çalıştırma). 16 üst lig (40.369 maç) + UCL 1.307 maç;
  değerlendirme 2013-14…2024-25, ortak küme 556 maç. UCL→yurt içi ad eşleme: 1.674 kesin, 932 veri yok, 8 yok.
- Log loss: B0 1,0419 · B1 1,0003 · M1 0,9872. M1−B1 −0,0130 [−0,0253; −0,0010]. Büyük-5 vs diğer (n=143): B1 1,0649
  (tabandan kötü), M1 1,0226. Büyük-5 beklenen puan: gözlenen 0,671; M1 0,516 → aktarım yönü doğru, büyüklüğü yetersiz.
- Inter Escaldes–Kopenhag ve Olympiakos–Milan: **hesaplanamaz** (Andorra/Danimarka verisi yok; Olympiakos yurt içi verisi
  2025-11'de kesik; M1 kalibrasyonu doğrulanmadı). Testler LA1–LA7.

## E — Sonuç ve gol modelleri
- Ön kayıt `ON_KAYIT_E.md` (SHA-256 c395befc…). fr.1, nl.1, pt.1, de.2, es.2; 2019-07 sonrası 10.158 maç; tutarlılık ihlali 0.
- Taban üstü (E1): 1X2, ÇŞ, H−1, takım gol AÜ, MS&AÜ/MS&KG bileşenlerinin çoğu, doğru skorların çoğu.
- Taban üstü DEĞİL: toplam gol AÜ 0,5–4,5, gol aralığı, tek/çift; KG taban altı (+0,0043 [+0,0010; +0,0077]).
  Kalibrasyon: AÜ 2,5 ECE 0,049, KG 0,041 — tahminler aşırı yayılmış (0,26 tahmin → 0,37 gerçek; 0,74 → 0,66).
- DC − Poisson: 0-0 için +0,0038 [+0,0002; +0,0102] (DC kötü); diğerlerinde fark yok.
- Sonraki adım (yeni ön kayıtla, başka liglerde): toplam gol için ayrı büzülme/dağılım modeli.

## F — Devre modelleri
- Ön kayıt `ON_KAYIT_F.md`; sapma `ON_KAYIT_F_SAPMA.md`. it.2, fr.2, en.3, en.4.
- v1: ilk yarı skoru eksik 504 maçın gol ortalaması ≈ 0 → kaynak 0-0 maçlarda İY yazmıyor (seçilim yanlılığı).
  v2: yalnızca maç sonu 0-0 → İY 0-0 mantıksal tamamlama (501 maç); kalan eksik 3.
- v2 (5.877 maç): marjinal devre marketlerinin hiçbiri "kalibre" değil; yalnızca 2Y 1 tabanı geçiyor.
  Bağımsızlık reddedilen birleşik seçenekler: 801 Evet/Evet, Evet/Hayır, Hayır/Hayır; İY/MS 1/X, 2/1, 2/X, 2/2;
  295, 584/…; 1Y KG–2Y KG olasılık oranı gözlenen 1,20, model 1,12. → Bu seçenekler **hesaplanamaz**.

## G, H, I, J
- G: izinli korner verisi yok → veri bekliyor. Korner olay uzayı (216/338/798/220 eşdeğerliği) sonraki iş.
- H: `h_asamasi.py`; 881 maç, 28 kart kaydı yok (0 sayılmadı); test 446 maç. H1−H0 +0,008 [−0,013; +0,028];
  H2−H1 −0,016 [−0,039; +0,006]; varyans 3,86 ≈ ortalama 3,98. Kart marketleri hesaplanamaz.
- I: veri bekliyor. J: bu oturumda başlanmadı.

## K, L
- `lib/fi/is_akisi.py`: gun filtresi (26.11 bülteninde 94 maç; 00:00 sonrası 8 maç dışarıda), lig eşlemesi yalnızca
  `veri/lig_eslemeleri.json` (boş, kullanıcı onayı gerekir), 14 günden eski veri → hesaplanamaz, takım eşlemesi kesin/onaylı,
  dondurma (SHA-256, git commit, veri kesimi), değiştirilmiş kaydı reddetme, maç başladıktan sonra dondurmama,
  fiyat karşılaştırması yalnızca dondurmadan sonra; EV yalnızca E'de doğrulanmış ve oynanabilir seçenekte.
- Canlı skor/dakika/kırmızı kart: bülten alan eşlemesi doğrulanmadı → gösterilmez.
- Testler K1–K7, L1.

## Çalıştırılan testler
`PYTHONPATH=lib python3 -m unittest discover -s tests` → 195 test, hepsi geçti (150 eski + 45 yeni).
