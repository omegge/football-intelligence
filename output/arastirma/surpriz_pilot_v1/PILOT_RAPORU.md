# Tarihsel sürprizler — 10+10 pilot raporu (S aşaması)

- Ön kayıt `lib/fi/model/ON_KAYIT_S.md`, SHA-256 `ff064c09…` (seçimden önce donduruldu, değişmedi).
- Seçim: `fi.model.surpriz_pilot` (tohum = ön kayıt özeti). Kodlama: `pilot_kodlama.json`.
- **Oran kullanılmadı (MK-1):**
  - Favori ve olasılıklar yalnızca bağımsız modelden geliyor: E ayarlı yürüyen Poisson; veri yalnızca maçtan önceki sonuçlar.
  - Piyasa sütunu ayrıdır ve modele girmez.
- Dondurulmuş SOU–MID tahmini ve önceki deneyler (set_v1, genis_pilot) değiştirilmedi.

## 0. Havuz ve model kalibrasyonu (seçimin zemini)
Havuz:
- **Ligler:** en.1, es.1, de.1, it.1, fr.1.
- **Sezonlar:** 2022-23 … 2025-26.
- **Maç sayısı:** 7.264. Bunların 3.725'inde favorinin olasılığı ≥ 0,50.

| Kategori (A) | Maç | Ort. P(favori kazanır) | Gerçek kazanma (±%95) | Berabere | Favori kaybetti |
|---|---|---|---|---|---|
| 50–60 | 1.824 | 0,548 | 0,535 (±0,023) | 0,267 | 0,198 |
| 60–70 | 1.128 | 0,645 | 0,645 (±0,028) | 0,212 | 0,143 |
| 70–80 | 564 | 0,743 | 0,745 (±0,036) | 0,161 | 0,094 |
| 80+ | 209 | 0,843 | 0,833 (±0,051) | 0,120 | 0,048 |

Model kategori düzeyinde kalibre görünüyor. Örneğin 80+ grubunda sürpriz oranı yaklaşık %17. Bu oran, olasılıkların zaten söylediği orana çok yakın.

Bunun anlamı: **sürprizlerin çoğu "modelin kaçırdığı bir şey" değil, düşük olasılıklı olayların beklenen sıklıkta gerçekleşmesi olabilir.** Sinyal aramanın soracağı soru şu: aynı kategoride hangi maçlar ortalamadan daha riskliydi?

## 1. Maç tablosu
- **Seçim kuralları:**
  - Kota: 80+ → 2, 70–80 → 3, 60–70 → 3, 50–60 → 2.
  - Her favori en fazla bir kez seçilir.
  - Kontrol maçı: aynı yarışma, aynı sezon, aynı saha; favori kazanmış; P'si en yakın maç.
- **Ünlü maç seçimi yapılmadı.** UEFA ŞL 2024-25 havuzdaydı ama kurayla çıkmadı.
- **set_v1 ile çakışma:** sürprizlerde yok. Kontrollerde 1 maç var: Real Madrid–Valladolid (K1). İşaretlendi, değiştirilmedi.

| # | Tarih | Lig | Maç | Skor | Favori (saha) | P_fav | Kat. | Sonuç (A) |
|---|---|---|---|---|---|---|---|---|
| S1 | 2024-11-30 | es.1 | Barcelona – Las Palmas | 1-2 | Barcelona (ev) | 0,835 | 80+ | kaybetti |
| S2 | 2024-10-04 | fr.1 | Marseille – Angers | 1-1 | Marseille (ev) | 0,803 | 80+ | berabere |
| S3 | 2026-03-22 | fr.1 | Rennes – Metz | 0-0 | Rennes (ev) | 0,758 | 70–80 | berabere |
| S4 | 2025-04-12 | de.1 | Leverkusen – Union Berlin | 0-0 | Leverkusen (ev) | 0,732 | 70–80 | berabere |
| S5 | 2026-02-21 | en.1 | Chelsea – Burnley | 1-1 | Chelsea (ev) | 0,721 | 70–80 | berabere |
| S6 | 2024-02-18 | fr.1 | Monaco – Toulouse | 1-2 | Monaco (ev) | 0,621 | 60–70 | kaybetti |
| S7 | 2023-05-22 | it.1 | Roma – Salernitana | 2-2 | Roma (ev) | 0,608 | 60–70 | berabere |
| S8 | 2023-12-19 | es.1 | Atlético – Getafe | 3-3 | Atlético (ev) | 0,642 | 60–70 | berabere |
| S9 | 2025-11-08 | de.1 | Hoffenheim – Leipzig | 3-1 | Leipzig (dep) | 0,519 | 50–60 | kaybetti |
| S10 | 2024-03-17 | it.1 | Juventus – Genoa | 0-0 | Juventus (ev) | 0,592 | 50–60 | berabere |
| K1 | 2024-08-25 | es.1 | Real Madrid – Valladolid | 3-0 | Real (ev) | 0,836 | 80+ | kazandı · set_v1 tekrar |
| K2 | 2025-02-15 | fr.1 | Marseille – Saint-Étienne | 5-1 | Marseille (ev) | 0,801 | 80+ | kazandı |
| K3 | 2025-09-21 | fr.1 | Monaco – Metz | 5-2 | Monaco (ev) | 0,753 | 70–80 | kazandı |
| K4 | 2024-10-18 | de.1 | Dortmund – St. Pauli | 2-1 | Dortmund (ev) | 0,734 | 70–80 | kazandı |
| K5 | 2025-08-23 | en.1 | Arsenal – Leeds | 5-0 | Arsenal (ev) | 0,703 | 70–80 | kazandı |
| K6 | 2024-02-04 | fr.1 | Lille – Clermont | 4-0 | Lille (ev) | 0,618 | 60–70 | kazandı |
| K7 | 2023-05-20 | it.1 | Atalanta – Verona | 3-1 | Atalanta (ev) | 0,611 | 60–70 | kazandı |
| K8 | 2024-02-24 | es.1 | Barcelona – Getafe | 4-0 | Barcelona (ev) | 0,642 | 60–70 | kazandı |
| K9 | 2025-08-30 | de.1 | Hoffenheim – Frankfurt | 1-3 | Frankfurt (dep) | 0,520 | 50–60 | kazandı |
| K10 | 2024-04-27 | it.1 | Lazio – Verona | 1-0 | Lazio (ev) | 0,589 | 50–60 | kazandı |

Sürpriz dağılımı: 3 kayıp, 7 beraberlik. Bu dağılım havuzla uyumlu, çünkü havuzda her kategoride beraberlik kayıptan daha sık.

**Kullanıcı örnekleri** ayrı ekte tutuldu, pilota katılmadı:
- **Lille 1-0 Real Madrid** (ŞL, 2024-10-02): Real P≈0,571, 50–60 kategorisi, kaybetti.
- **Bournemouth 2-1 Man City** (2024-11-02): City 0,672, 60–70 kategorisi, kaybetti.
- **Sheriff (2021):** ŞL 2021-22 verisi yok.
- **Arjantin–Suudi Arabistan:** milli maç, kulüp modelinin dışında.

## 2. Sınıflandırma: A (bağımsız model) ve B (piyasa)
- **A:** Tablodaki kategori ve sonuç; 20 maçın hepsinde var.
- **B (marjı çıkarılmış kapanış 1X2):** 20 maçın **20'sinde "piyasa verisi eksik".**
  - İzinli bir kaynakta, bahis şirketi ve zaman damgasıyla kapanış oranı bulunamadı.
  - Basında geçen oran da kaydedilmedi.
  - Uydurulmadı. A ile B karşılaştırması bu pilotta yapılamıyor.

## 3. Gerçek açılış ve kapanış oranları
Bulunamadı. İncelenen kaynaklar:

| Kaynak | Kapsam | Karar |
|---|---|---|
| AnishKhetani/premier-league-data (GitHub) | football-data.co.uk türevi | reddedildi (türev, kaynak koşulları) |
| iredchuk (GitHub) | 2018-19'da bitiyor | dönem dışı |
| Beat the Bookie (akademik) | 2005–15, Kaggle hesabı gerekiyor | dönem dışı; hesap açılmadı |
| Odds-API.io örnek veri | CC BY 4.0, yalnızca 2025-26 kapanış | **erişim ve koşul denetimi yapılmadı → sıradaki adım** |
| football-charts | oran lisansı belirsiz | kullanılmadı |

Odds-API.io denetlenirse yalnızca 2025-26 maçlarını kapsar: S3, S5, S9, K3, K5, K9.

## 4. Maç öncesi bilinenler (A katmanı)
- Kaynak: web arama özetleri. Sayfalar okunmadı.
- Doğrulama seviyesi her biri için **dogrulanmadi**. Tarihsiz bilgiler kullanılmadı.

| # | Maç öncesi haber / yorum |
|---|---|
| S1 | Casadó cezalı; Yamal ve Ferran dönüyor; genç oyuncular kadroda |
| S2 | Bir hafta önce Strasbourg yenilgisi; kadro haberi tarihsiz (kullanılmadı) |
| S3 | **Tarihli önizleme bulunamadı** |
| S4 | Bayern'in 6 puan gerisinde; Wirtz sakatlık sonrası yedekte; Union 13. |
| S5 | Cucurella yok (teknik direktörün basın toplantısı); önceki maç Leeds 2-2; Burnley düşme favorisi; SI tahmini 4-1 |
| S6 | Toulouse 3 gün önce Avrupa Ligi'nde Benfica ile oynadı; önizleme tahmini 2-0 Monaco |
| S7 | Roma Avrupa Ligi finaline yeni yükseldi; rotasyon doğrulanmadı |
| S8 | **Önizleme bulunamadı** |
| S9 | Leipzig, Bayern'in 5 puan gerisinde; kadro haberi yok |
| S10 | Allegri: "yeniden yola girmek" (kulüp, 16.03, kötü form); Alcaraz ve De Sciglio yok; Rabiot dönüyor; tahminler 1-0 / 1-1 / 2-1 |
| K1 | Mallorca'da beraberlik; Mendy cezalı; Bellingham sakatlık haberi |
| K2 | Mbemba, Blanco ve Moumbagna yok; Rongier ve Harit şüpheli; Saint-Étienne şubatta 2 yenilgi |
| K3 | Zorlu ŞL açılışı sonrası; Hradecky, Golovin ve Zakaria darbe aldı; Metz son sırada |
| K4 | Yalnızca tahmin (2-0, anket %88) |
| K5 | Havertz diz sakatlığı (Leeds'te Nørgaard yok) |
| K6 | 19 maçta 8 beraberlik; sonraki maç PSG; Bouaddi cezalı; Clermont son sırada |
| K7 | 2 yenilgi üst üste, 7.'liğe geriledi; uzun sakat listesi |
| K8 | Xavi ayrılacağını açıkladı; 5 maçtır yenilmiyor; Getafe'de Martín ve Arambarri yok |
| K9 | Yalnızca tahmin (1-3) |
| K10 | Kupada Juventus'a elendi; Provedel, Gila ve Lazzari yok; Zaccagni yedek |

Tahmin sitelerinin skor tahminleri ve anket yüzdeleri yalnızca bilgi olarak yazıldı; model girdisi değildir.

## 5. Maç içi (B) ve maç sonrası (C) açıklamalar — ayrı tutuldu
- **B (maç içi: kırmızı kart, penaltı, erken gol, sakatlık):** bu pilotta araştırılmadı → 20 maçta "veri yok".
- **C (maç sonrası):** yalnızca bir kayıt var. S1'deki Olmo sakatlığı daha sonraki bir önizlemeden geliyor. C olarak işaretlendi ve sinyale sayılmadı.
- **"Önceden görülebilir miydi?"** Bu pilotta hiçbir sürprizde favoriye özgü, kontrollerde görülmeyen güçlü bir maç öncesi işaret yok.
  - S3 ve S8'de hiç haber bulunamadı.
  - 10 sürprizin 10'u da şimdilik **"düşük olasılıklı olay gerçekleşti; önceden belirgin sinyal kanıtı yok"** sınıfında.
  - Bu bir kanıt yokluğudur; sinyalin yokluğunun kanıtı değildir.

## 6. Sinyal sıklıkları ve ilk hipotezler
- Kodlama sonuç bilinerek ve geriye dönük yapıldı (kör değil).
- Her grupta n = 10. Parantez içinde Wilson %95 güven aralığı var.

| Sinyal (maç öncesi) | Sürpriz | Kontrol (yanlış alarm) |
|---|---|---|
| Favoride kilit eksik / ceza / sakatlık dönüşü | 3/10 (0,11–0,60) | **7/10** (0,40–0,89) |
| Favori kötü formda | 3/10 | 3/10 |
| Favoride yoğun takvim / Avrupa maçı | 1/10 | 1/10 |
| Favoride şampiyonluk baskısı | 2/10 (0,06–0,51) | 0/10 (0–0,28) |
| Rakip düşme mücadelesinde | 1/10 | 2/10 |
| Favoride teknik direktör belirsizliği | 1/10 | 1/10 |
| Rakipte yoğun takvim | 1/10 | 0/10 |
| Haber bulunamadı | 2/10 | 2/10 |

**Okuma:**
- **Hiçbir sinyal iki grubu ayırmıyor.** Bütün güven aralıkları örtüşüyor.
- **"Favoride kilit eksik" bu pilotta ters yönde:**
  - Kontrollerde daha sık (7/10 ve 3/10).
  - Önceki 8+8 keşifteki "5/8'e 1/8" bulgusu bu sette tekrarlanmadı.
  - Muhtemel nedenler:
    - büyük takımlar her hafta eksikle oynuyor ve kadro derinliği bunu karşılıyor;
    - "kilit" tanımı gevşek.
- **"Şampiyonluk baskısı":**
  - İki sürpriz maçta var (S4 Leverkusen, S9 Leipzig): favori, takip ettiği takımın birkaç puan gerisinde.
  - Kontrollerde hiç yok.
  - Ancak bu sinyal kontrollerde sistematik aranmadı. Real ve Barça gibi takımlar da her zaman şampiyonluk yarışında. Bu kodlama yanlılığı olabilir.

**İleriye dönük test için hipotezler** (ön kayıt gerekir, şimdi uygulanmaz):
- **H-S1 (şampiyonluk takibi):**
  - Tanım: favori, lider olmayan ve liderin ≤ 6 puan gerisindeki bir takım; rakip ilk 10'un dışında.
  - Bu durumda beraberlik oranı, aynı P kategorisinin havuz ortalamasından yüksek mi?
  - Puan durumu sonuçlardan hesaplanabilir. Bu yüzden haber gerektirmez ve havuzun tamamında (3.725 maç) test edilebilir.
- **H-S2 (rakipte yoğun takvim):**
  - Tanım: rakip, maçtan ≤ 3 gün önce Avrupa maçı oynamış.
  - Beklenti: favori kazanma oranı havuz ortalamasından düşük değil, hatta yüksek.
  - S6 bunun tersi. Yön belirsiz; iki yönlü test edilmeli.
- **H-S3 (kilit eksik):**
  - Tanım: yalnızca "son 5 maçta ilk 11'de en az 4 kez oynamış oyuncunun resmi olarak yok olması".
  - Gevşek tanım yanlış alarm üretiyor.
- **H-S4 (sıfır hipotezi):**
  - Kalibre bir modelde sürprizler, P kategorisinin öngördüğü sıklıkta ve rastgele dağılır.
  - Yukarıdaki sinyallerin hiçbiri bunu reddedemezse önerilecek bir "sürpriz filtresi" yoktur.

## 7. Veri boşlukları ve güvenilirlik
1. **Piyasa:** 20 maçın 20'sinde eksik. B sınıflandırması yapılamadı.
2. **Haber:**
   - Bütün kayıtlar arama özeti. Doğrulama seviyesi yok.
   - 4 maçta kadro haberi hiç yok.
   - Tarihsiz bilgiler dışarıda bırakıldı.
3. **Kör olmama:** Sonucu bilerek araştırdım. Aramalar, sonucu açıklayan maç sonrası metinleri de getiriyor. Yalnızca maç öncesi tarihli bilgiyi aldım, ama seçici dikkat yanlılığı dışlanamaz.
4. **Kodlama tanımları** gevşek ve tek kodlayıcı yaptı. Kodlayıcılar arası tutarlılık ölçülmedi.
5. **Model:**
   - E ayarlı Poisson; Dixon-Coles yok; maçlar aynı sezondan.
   - Tahminler geriye dönük ama zaman açısından dürüst (yürüyen test).
   - ŞL'de M1 Elo var, fakat pilota ŞL maçı çıkmadı.
6. **n = 10 + 10:** Yalnızca yöntemi denemeye yeter. Hiçbir sıklık farkı istatistiksel kanıt değildir.

## 8. 30+30 ve 100+100'e genişletilebilir mi?
- **Seçim ve model tarafı: evet, hemen.**
  - Havuzda 3.725 favorili maç var. Sürprizler ve kontroller her kategoride yeterli (80+ grubunda bile 35 sürpriz).
  - `sec()` kotaları parametreyle büyütülebilir.
- **Haber tarafı: darboğaz.**
  - Maç başına 2–4 arama gerekiyor: 200 maç için yaklaşık 600 arama.
  - Bu pilotta maçların ~%20'sinde haber bulunamadı.
  - Ayrıca kör olmayan kodlama sorunu var. Öneri:
    - 30+30'da maçları sonuçlar gizlenmiş, karışık sırada araştırmak;
    - sinyalleri H-S3 gibi önceden yazılmış dar tanımlarla kodlamak;
    - araması sonuç sızdıran maçları işaretlemek.
- **Veriden hesaplanabilen sinyaller (H-S1, takvim yoğunluğu, form): 100+100 hatta havuzun tamamı mümkün.** Haber gerekmez. En güçlü sonraki adım bu.
- **Piyasa tarafı: şimdilik hayır.**
  - Önce Odds-API.io örneğinin erişim ve lisans denetimi gerekiyor.
  - Bu yalnızca 2025-26 sezonunu kapsar.
  - Eski sezonlar için izinli bir kapanış oranı kaynağı yok.

**Önerilen sıra:**
1. H-S1 ve takvim yoğunluğu için ön kayıt, ardından tüm havuzda test.
2. Odds-API.io denetimi.
3. Kör protokolle 30+30 haber araştırması.

---

## Ek (v2): maç içi gelişmeler, lig bazında kalibrasyon, Avrupa kupaları
Kodlamanın v1 sürümü (`pilot_kodlama.json`) değiştirilmedi. Bu ek `pilot_kodlama_v2.json` dosyasına dayanıyor.

### E1. Lig bazında model güvenilirliği (A sütunu yüzdeleri için ön koşul)
| Lig | Favorili maç | Ort. P | Gerçek kazanma (±%95) | Kategori ECE | Karar |
|---|---|---|---|---|---|
| en.1 | 809 | 0,628 | 0,622 (±0,033) | 0,014 | kalibre |
| es.1 | 700 | 0,624 | 0,637 (±0,036) | 0,022 | kalibre |
| it.1 | 781 | 0,614 | 0,618 (±0,034) | 0,010 | kalibre |
| fr.1 | 648 | 0,613 | 0,594 (±0,038) | 0,023 | kalibre |
| **de.1** | 679 | 0,636 | 0,599 (±0,037) | **0,039** | **sınırda**: favorilere fazla güveniyor |
| uefa.cl | 108 | 0,646 | 0,676 (±0,088) | 0,031 | n küçük |

Bundesliga'dan seçilen 4 maçın yüzdeleri "kalibrasyonu sınırda" uyarısıyla okunmalı: S4 Leverkusen, S9 Leipzig, K4 ve K9. Kategoriler korunuyor, ancak bu maçlarda yüzdeler kesin değer olarak sunulmaz.

### E2. Maç içi (B) ve maç sonrası (C) — 10 sürpriz
Kaynaklar maç sonrası haber ve istatistik sayfalarının arama özetleri. B ve C sinyal olarak sayılmaz.

| # | B: maç içinde sonucu değiştiren gelişmeler | C: maç sonrası açıklama | "Önceden tahmin edilebilir miydi?" |
|---|---|---|---|
| S1 | Las Palmas'ın iki golü kontra ve hızlı geçişlerden; kırmızı kart yok | Flick: "gol atamayınca zorlanıyoruz" | Düşük olasılıklı olay; maç öncesi kanıt zayıf (Casadó cezası) |
| S2 | 26' Angers ve 30' Maupay kırmızı kart → 10'a 10 | — | Maç içi olay belirleyici; maç öncesi sinyal: önceki hafta Strasbourg yenilgisi |
| S3 | Rennes golü VAR ile iptal; uzatmada kaçan kafa | — | Düşük olasılıklı olay; maç öncesi haber bulunamadı |
| S4 | Topa sahip olma üstünlüğü ama net pozisyon az; Rønnow'un kurtarışları | — | Kısmen: şampiyonluk takibi ve Wirtz'in dönüşü maç öncesi bilgiydi; belirleyici değil |
| S5 | 4' gol, ardından **Fofana kırmızı kart**, geç beraberlik golü | — | Maç içi olay belirleyici; maç öncesi Cucurella eksik |
| S6 | Kırmızı kart yok; Toulouse etkili bitiricilik | — | Düşük olasılıklı olay; rakibin Avrupa yorgunluğu beklentisi tersine döndü |
| S7 | Salernitana iki kez öne geçti; 83' beraberlik; uzatmada arbede | "Avrupa başarısından sonra gerçeğe dönüş" çerçevesi (C) | Kısmen: Roma 6 lig maçıdır galibiyetsizdi ve Avrupa Ligi finali yaklaşıyordu (maç öncesi, veriyle doğrulanabilir) |
| S8 | **Savić erken kırmızı**; Getafe 87' ve uzatmada penaltı | — | Maç içi olay belirleyici |
| S9 | Leipzig 9' öne geçti; bir Leipzig golü VAR ile iptal; **xG Leipzig 2,17 – Hoffenheim 1,87** | — | Düşük olasılıklı olay: favori daha çok pozisyon üretti. Maç öncesi: Hoffenheim 3 maçlık galibiyet serisiyle geldi |
| S10 | 17'ye 5 şut; Kean 90' direk; Vlahović uzatmada kırmızı (sonuca etkisi yok) | — | Kısmen: Juve 8 maçta 1 galibiyet (maç öncesi form verisi) |

**Okuma:**
- 10 sürprizin 3'ünde favorinin sonucu değiştiren bir kırmızı kartı var (S5 ve S8 kesin; S2'de iki taraf da 10 kişi kaldı). 2 maçta VAR ile gol iptali var.
- Bunlar maç öncesinde bilinemez. Bu maçlar için "tahmin edilebilir sürpriz" iddiası yapılamaz.
- Kontrol maçlarının B alanı araştırılmadı. Bu yüzden kırmızı kartın sürprizlerde daha sık olup olmadığı henüz ölçülemiyor; bu, 30+30'da yapılacak.

**Kaba sınıflama (tek kodlayıcı, sonuç bilinerek):**

| Sınıf | Maç sayısı | Maçlar |
|---|---|---|
| Maç içi olay belirleyici | 3 | S2, S5, S8 |
| Düşük olasılıklı olay, maç öncesi kanıt yok ya da zayıf | 4 | S1, S3, S6, S9 |
| Maç öncesinde kısmi risk görülebiliyordu (kanıt kesin değil) | 3 | S4, S7, S10 |

### E3. Veriden doğrulanabilen form sinyalleri
S7, S9 ve S10'da maç öncesi form bilgisi haber gerektirmeden sonuç verisinden hesaplanabilir:
- favorinin son N maçta galibiyetsizliği;
- rakibin galibiyet serisi.

Bu da önceki hipotezlere ekleniyor:
- **H-S5 (ön kayıtla, tüm havuzda test):** Favori son 6 lig maçında ≤ 1 galibiyet aldıysa, aynı P kategorisinde favorinin kazanma oranı havuz ortalamasından düşük mü? Rakibin ≥ 3 maçlık galibiyet serisi için de aynı soru.
- Not: Model zaten son sonuçları kullanıyor. Bu yüzden test, modelin bu bilgiyi yeterince hızlı yansıtıp yansıtmadığını ölçer (kalıntı kalibrasyon).

### E4. Talimattaki öncelik sırasıyla uyum ve eksikler
- **Avrupa kupaları (öncelik 1):**
  - Havuzda yalnızca ŞL 2024-25 var: 108 favorili maç. Kurada hiç seçilmedi.
  - 30+30 için önerim: Avrupa kupaları için ayrı bir katman kotası (ör. 30'un 8'i).
  - Bunun için ŞL 2022-24 ve Avrupa Ligi / Konferans Ligi verisinin izinli bir kaynaktan okunması gerekiyor. openfootball'da bu sezonların okunabilirliği henüz denetlenmedi.
- **Diğer Avrupa ligleri (öncelik 4)** ve **millî maçlar (öncelik 5):** pilotta yok.
  - Millî maçlar için kulüp modeli kullanılamaz. Ayrı bir model ve kalibrasyon olmadan yüzde üretilmez.
- **Piyasa ayrıntıları:** Asya handikapı, Alt/Üst, KG fiyatları, fiyat hareket zamanları ve bahis şirketleri arası ayrışma için de izinli kaynak bulunamadı; bu alanlar "piyasa verisi eksik".
- **Tahmin sitelerinin gerekçeleri:** Yalnızca skor tahminleri toplandı (SI 4-1, Sports Mole 2-0 ve 1-3). Gerekçeler sayfa okunmadan alınamadı. Reddit ve taraftar toplulukları aranmadı.
