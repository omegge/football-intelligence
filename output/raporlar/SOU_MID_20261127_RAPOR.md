# Southampton – Middlesbrough · İngiltere Championship · 27.11.2026 23:00 TR (20:00 UTC)

İlk gerçek günlük analiz. Sıra MK-1'e uygundur: bağımsız olasılık **26.11.2026 18:18 UTC'de donduruldu**
(SHA-256 `8d4b1a45…`), Nesine fiyatları **20:59 UTC'de, dondurmadan sonra** çekildi. Bahis oranları ve diğer
sitelerin yüzdeleri modele girmedi. Bu rapor kupon ya da bahis önerisi değildir.

## 0. Kimlik ve veri doğrulaması
| | Değer | Kaynak |
|---|---|---|
| Nesine | kod 3331002, "İngiltere Championship" [52], 23:00 TR | bülten 26.11 20:57 TR ve 23:59 TR |
| football-data.org | maç 561968, 2026-11-27T20:00Z, SCHEDULED | season=2026 çekimi (bütünlük temiz) |
| Kulüp (resmî) | Cuma 27 Kasım 20:00 GMT, St Mary's; hakem **Tony Harrington** | southamptonfc.com maç paketi |
| Lig eşlemesi | [52] → en.2, kullanıcı onaylı (fikstür hizalaması kanıtı) | veri/lig_eslemeleri.json |
| Veri kesimi | 2026-11-25 (son skorlu maç), 7.405 Championship maçı | OpenFootball + football-data.org |
| Takım eşlemesi | "Southampton" → Southampton FC, "Middlesbrough" → Middlesbrough FC (kesin) | — |

## 1. Güncel takım ve form analizi (maç verisinden)
| | Southampton | Middlesbrough |
|---|---|---|
| Sonuçlardan puan (17 maç) | 32 (4. sıra) — **bildirilen 4 puan silme ile 28, 6. sıra (doğrulanmadı)** | 35 (1.) |
| Gol | 32–16 | 34–20 |
| Son 5 maç | 8 puan (1,60/maç), 8–4; rakiplerin ort. 1,27 puan/maç | 10 puan (2,00/maç), 7–3; rakipler 1,21 |
| Son 10 maç | 18 puan (1,80/maç), 14–8; rakipler 1,31 | 21 puan (2,10/maç), 20–10; rakipler 1,41 |
| Ev / deplasman | Evde 8 maç 7G 1B 0M, 22–5; Championship'te iç saha lig serisi 19 maç yenilgisiz | Deplasmanda 8 maç 3G 3B 2M, 13–10 |
| Gol attığı maç / KG / 2,5 üst | 15/17 · 12/17 · 8/17 | 15/17 · 11/17 · 11/17 |
| Fikstür | 21, 24, 27.11 (7 günde 3. maç, ~72 sa) | 21, 24, 27.11 (aynı) |
Lig ortalaması 1,37 puan/maç. Boro'nun son 10 maçtaki rakipleri lig ortalamasının biraz üstünde; Southampton'ınkiler biraz
altında. Son 5 maçta iki takımın da rakipleri ortalamanın altında.

## 2. Bağımsız model (E2: ceza 16, hiyerarşik büzülme w = 0,65; yalnızca kapsamdaki 26 seçenek)
λ_ev 1,61 · λ_dep 1,15 · ligin son 365 gün ortalaması 2,71 gol. Model ev sahibini daha güçlü görüyor; **1X2'nin "1" ve
"2" seçenekleri E2'de kalibre olmadığı için yüzde verilmez.**

| Seçenek | Bağımsız p | Kalibrasyon (E2 sınaması) |
|---|---|---|
| MS X | 0,248 | kapsamda |
| Çifte şans 1-2 | 0,752 | kapsamda |
| KG Var / Yok | 0,546 / 0,454 | kapsamda (ECE 0,014) |
| 4,5 Alt / Üst | 0,854 / 0,146 | kapsamda |
| Ev 0,5 Üst / Alt | 0,800 / 0,200 | kapsamda |
| Ev 2,5 Üst / Alt | 0,218 / 0,782 | kapsamda |
| Handikap (0:1) X (= ev 1 farkla) | 0,230 | kapsamda |
| MS1&KG Var · MSX&KG Var · MS2&KG Var · MS2&KG Yok | 0,227 · 0,184 · 0,136 · 0,137 | kapsamda |
| MSX&2,5 Alt · MSX&2,5 Üst · MS2&2,5 Alt | 0,181 · 0,067 · 0,115 | kapsamda |
| Skor 1-0 · 0-1 · 1-1 · 2-0 · 0-2 · 2-1 · 1-2 · 2-2 | 0,102 · 0,073 · 0,117 · 0,082 · 0,042 · 0,094 · 0,068 · 0,054 | kapsamda |

## 3. Hesaplanamayan marketler (yüzde yok; nitel/istatistik not)
- **1X2 "1" ve "2", çifte şans 1-X / X-2, toplam 1,5 / 2,5 / 3,5:** E2'de tabanı geçti ama kalibre değil (bir ligde ECE > 0,04
  ya da sapmalı kutu). Not: bu sezon 2,5 üst Southampton maçlarında 8/17, Boro maçlarında 11/17.
- **Devre marketleri:** F/F2'de tabanı geçmedi; bağımlılık modellenemedi.
- **Korner, kart:** model yok. Hakem Harrington (resmî kaynak); hakem kart profili için izinli veri yok. Racing Post ve Sports
  Mole sert ve kartlı bir maç bekliyor (Spygate sonrası ilk karşılaşma) — ölçülmemiş nitel görüş.
- **Oyuncu:** model yok. Golcüler: Lankshear 14 lig golü, Larin 9 (resmî maç paketi).

## 4. Sakatlık, ceza, rotasyon, ilk 11
| Takım | Oyuncu | Durum | Doğrulama | Kaynak |
|---|---|---|---|---|
| SOU | (kadro) | "bazı dönüşler olacak"; Salı 6 değişiklik | **resmî** | southamptonfc.com |
| SOU | Caspar Jander | dönüş şansı (kas, son 5 maç yok) | doğrulanmadı (tek basın toplantısı zinciri, 3 kopya) | Hayters / Yahoo / Football Lowdown |
| SOU | Leo Scienza | dönüş şansı (fitness) | doğrulanmadı | Hayters |
| SOU | Cyle Larin | döndü, Derby'ye gol attı | doğrulanmadı (resmî pakette "önceki iç saha maçında gol" ifadesi var) | Hayters + kulüp |
| SOU | Schlotterbeck | yok (tek önizleme) | doğrulanmadı | önizleme |
| MID | Alfie Jones | yok / şüpheli (baldır; "2–3 hafta") | **iki bağımsız** | Teesside Live (arama özeti) + Southampton maç paketi |
| MID | Rokas Pukštas | yok (hamstring; ameliyat iddiası) | **iki bağımsız** (yok/şüpheli) | aynı |
| MID | Connor Barron | yok | doğrulanmadı | Teesside Live (arama özeti) |
| MID | Will Lankshear | **hazır ↔ şüpheli** | **çelişkili** | Teesside Live (Hellberg) ↔ the72 |
| MID | Marko Stamenic | cezalı (tek önizleme) | doğrulanmadı; Teesside listesinde yok | Hard Tackle |
| MID | Berhalter / Neto Borges | dönüş olası / ayak bileğine rağmen oynadı | doğrulanmadı (rakip kulüp yayını) | southamptonfc.com |
İlk 11 açıklanmadı (T−90dk turu: 27.11 21:30 TR).

## 5. Teknik direktör açıklamaları
- **Eckert:** kadroya dönüşler; Hellberg'e maç sonrası içki daveti; Spygate için 7.10'da 6 haftalık ertelenmiş men + 28.000 £
  (FA belgesi, arama özeti). "FA duruşması bu hafta" iddiası FA belgesiyle çelişiyor.
- **Hellberg:** Spygate sonrası "kin yok"; maç başına 2 puan hedefi, tablonun hızla değişebileceği (resmî pakette alıntı).

## 6. Yerel basın ve uzman yorumları — ortak ve karşıt gerekçeler
| Beklenti | Kim | Dayanak | Veri sınaması |
|---|---|---|---|
| **2-1 Southampton** | Sports Mole, ScoreGPT (AI) | maç yoğunluğu + ev avantajı; St Mary's formu | Ev formu doğrulandı (7G 1B, 22-5; 19 maç yenilgisiz) |
| **1-1** | Squawka, Sportskeeda, Statz, MightyTips | Boro'nun deplasman beraberlikleri, Southampton savunması, Boro'nun gol sürekliliği | Boro deplasman 3G 3B 2M ✔; Boro 15/17 maçta gol ✔; Southampton evde 5 gol yedi ✔ |
| **2-2** | The Hard Tackle | Southampton'ın iç saha rekoru ↔ Boro'nun lider formu, iki takım da gol atar | İki takımın KG oranı 12/17 ve 11/17 ✔ |
| **0-0** | Forebet (algoritma) | gerekçe yok | — |
| Taktik nokta | Charlie Hodgson (önizleme) | Southampton Lankshear'ı orta toplarda durdurmalı | Lankshear 14 gol ✔ (resmî) |
**Ortak payda:** dengeli, golsüz geçmesi beklenmeyen maç; Southampton'ın iç saha gücü ile Boro'nun lider formu karşı karşıya.
**Ayrışma:** kazananı söyleyenler ev avantajına, beraberlik diyenler Boro'nun deplasmanda beraberlik eğilimine ve iki
takımın da gol bulmasına dayanıyor. Statz'ın yüzdeleri ve tahmin sitelerinin oranları karantinadadır (kayıtlı, modelde yok).

## 7. Model ile uzman görüşleri / piyasa arasındaki ayrışmalar
1. **Favori yönü:** model ev sahibini güçlü görüyor (λ 1,61 – 1,15); Nesine 1X2 fiyatları (2,56 / 3,31 / 2,02) Boro'yu
   favori gösteriyor; analistlerin çoğu beraberlik ya da dar ev galibiyeti diyor. Modelin "1"/"2" yüzdesi kalibre değil →
   bu ayrışma sayısal olarak değerlendirilemez.
2. **Gol beklentisi (en büyük ayrışma):** model KG Var 0,546; Nesine KG Var 1,35 (başabaş 0,741; bu market 1/oran
   toplamı 1,187 → yüksek marj); iki takımın sezon KG oranı 12/17 ve 11/17; analistlerin 1-1 / 2-2 seçimi de KG'yi
   destekliyor. Olası neden: E2'nin bilinçli büzülmesi (w = 0,65) takım-özgü gol eğilimini lig ortalamasına (2,71) çekiyor;
   17 maçlık sezon oranı ise küçük örneklem. **Model düzeltilmedi**; bu ayrışma ileriye dönük değerlendirmede izlenecek.
3. **Kart/sertlik:** analistler kartlı maç bekliyor; modelde kart yok.

## 8. En önemli sürpriz senaryoları (yorum; olasılığa uygulanmadı)
- **Boro deplasmanda kazanır:** Nesine'nin favorisi; ligin en iyi gol averajı, Lankshear formu. Model bunu sürpriz sayıyor.
  Sinyal: Lankshear hazırsa (T−90dk'da teyit) Boro hücumu tam güçte.
- **Düşük skorlu Southampton galibiyeti (1-0 / 2-0):** modelin piyasaya göre en yüksek gördüğü sonuçlar; Southampton evde
  8 maçta 5 gol yedi. Karşı sinyal: Boro 17 maçın 15'inde gol attı.
- **Rotasyon şoku:** iki takım da 7 günde 3. maçında; Southampton Salı 6 değişiklik yaptı. Beklenmeyen ilk 11 değişimi
  T−90dk'nın en önemli sinyali.
- Somut, doğrulanmış favori aleyhine eksik: **yok** (favori bağımsız modelle belirlenemedi; Boro'da Jones/Pukštas eksikleri
  "iki bağımsız" düzeyinde).

## 9. Nesine fiyat karşılaştırması (donmuş tahminle; 20:59 UTC bülteni)
| Nesine seçeneği | Oran | Başabaş | Bağımsız p | EV (p×oran−1) |
|---|---|---|---|---|
| MS1 & 1,5 Alt (= 1-0) | 12,95 | 0,077 | 0,102 | +0,32 |
| Maç Skoru 2:0 | 14,90 | 0,067 | 0,082 | +0,22 |
| Maç Skoru 1:0 | 10,95 | 0,091 | 0,102 | +0,12 |
| KG Yok | 2,24 | 0,446 | 0,454 | +0,02 |
| Handikap (0:1) X | 4,34 | 0,230 | 0,230 | −0,001 |
| MS1 & KG Var | 4,31 | 0,232 | 0,227 | −0,02 |
| Ev 2,5 Üst | 4,45 | 0,225 | 0,218 | −0,03 |
| MS X | 3,31 | 0,302 | 0,248 | −0,18 |
| KG Var | 1,35 | 0,741 | 0,546 | −0,26 |
(Tam liste: `output/bulten_20261126_235932/fiyat_karsilastirma_3331002.json`, 34 seçenek.)
- **Eşdeğer seçenekler:** 1-0 için "MS1 & 1,5 Alt" 12,95 > "Maç Skoru 1:0" 10,95; 1-1 için "2,5 Alt & KG Var" 7,03 >
  "Maç Skoru 1:1" 6,06; 0-0 için en yüksek "MSX & KG Yok" 16,25 (eşdeğerlik "İlk Gol Olmaz" 16,75 için kontrol gerekli).
  20 eşdeğer grup; alt küme fiyat tutarsızlığı 0. Ana marketlerde 1/oran toplamı ≈ 1,188.
- **Uyarı:** Pozitif EV satırları bir öneri değildir. Bunlar tam da modelin piyasadan en çok ayrıştığı düşük skorlu ev
  galibiyeti senaryosudur (madde 7.2); model kalibrasyonu havuzda kabul edilebilir olsa da tek maçta belirsizlik büyüktür ve
  piyasa modelin görmediği bilgiyi (kadro, form, ilk 11 beklentisi) içerebilir. "Yüksek güven" verilmez.

## 10. Veri eksikliği ve belirsizlikler
- İlk 11 açıklanmadı; Lankshear durumu çelişkili; Jander/Scienza dönüşü doğrulanmadı.
- Puan silme (−4) doğrulanmadı; sonuçlardan hesaplanan tablo cezaları içermez.
- Teesside Live (gazettelive.co.uk) robots.txt yapay zekâ ajanlarını engelliyor → yalnızca arama özeti; mfc.co.uk kimliği
  iki işaretle doğrulanamadı → okunmadı; dailyecho.co.uk getirme aracı tarafından reddedildi.
- xG, şut, korner, kart, hakem profili verisi yok.
- T−6s (17:00 TR) ve T−90dk (21:30 TR) turları **yapılmadı**; komutlar `output/arastirma/genis_pilot/sou_mid_20261127_v2/TURLAR.md`.

## 11. Son araştırma ve kaynaklar
Son araştırma 26.11.2026 ~21:10 UTC (T−24s). Kayıt: `output/arastirma/genis_pilot/sou_mid_20261127_v3/` (37 iddia,
21 host, 14 bağımsız zincir; SHA-256 `d845fb89…`). Donmuş tahmin: `output/tahminler/nesine_3331002_20261126T181800Z.json`.
Başlıca kaynaklar: southamptonfc.com maç paketi (okundu), football-data.org (veri), Teesside Live, Hayters, Sky Sports,
Yahoo Sports, FA (thefa.com), ITV, Sports Mole, The Hard Tackle, Squawka, Sportskeeda, Statz, the72, Forebet, Racing Post
(arama özetleri). Football data provided by the Football-Data.org API.
