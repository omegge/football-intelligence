# Haber katmanı pilotu — 16 maç raporu (25.11.2026)

> **Bağımsız kör test DEĞİLDİR.**
> - Bütün sonuçlar önceden biliniyordu. Seçim (`pilot_secimi.json`, SHA-256 `d791de85…`) araştırmadan önce dondurulmuştu.
> - Kanıtlar `kanitlar.jsonl` dosyasında; SHA-256 `2f79d688…` (2026-11-25T17:30Z). Bu özet yalnızca kaydın sonradan değişmediğini gösterir.
> - Haberden olasılık üretilmedi. Modele hiçbir şey eklenmedi. MK-1: Nesine ya da bahis kaynağı kullanılmadı; 17 kanıt `kanit.py` denetiminden geçti.

## 1. Yöntem
- **Bütçe:** Maç başına en fazla 2 arama + 4 sayfa; sürpriz ve kontrol maçlarında aynı. Aramalar yalnızca o maç için kullanılabilir hostlarla sınırlandı.
- **İstatistik alanları:** Kendi verimiz (OpenFootball + Elo/Dixon–Coles) ve Wikipedia kulüp sezonu maddeleri (tüm kulvarlarda fikstür). Ayrıntı `istatistik_alanlari.json`'da.
- **Kanıt kuralları:**
  - Yayın tarihi sayfanın kendisinden doğrulandı: JSON-LD/meta ya da sayfada görünen tarih.
  - Aynı gün yayımlananlar maç saatiyle karşılaştırıldı.
  - Arama özetleri kanıt sayılmadı.
  - Kenar çubuğundaki "ilgili haberler" metinden çıkarıldı. İlk okumada 2026 tarihli bir yan haber kanıta karışmıştı; bu hata yakalanıp düzeltildi.

## 2. 16 maçlık karşılaştırma
Kısaltmalar: S = sürpriz, K = kontrol. DC = Dixon–Coles'un favori için kazanma olasılığı. Form = son 5 / son 10 maçta rakip gücüne göre düzeltilmiş performans (Elo beklentisine göre sonuç − beklenti toplamı). Dinlenme: tüm kulvarlar.

| Maç | Tür | Skor | DC | Favori formu 5/10 | Rakip formu 5/10 | Sıra (fav–rak) | Fav dinlenme (gün) | Sonraki fav maçı | Doğrulanmış haber |
|---|---|---|---|---|---|---|---|---|---|
| Sheffield U – **Brentford** | S kayıp | 1-0 | 0,71 | −0,46 / −0,77 | −0,32 / −1,63 | 11–20 | 3 | PL, 8 gün | 2 (rakipte TD değişimi; Mbeumo darbe) |
| Sheffield U – **Tottenham** | K | 0-3 | 0,71 | −1,26 / −1,98 | −1,52 / −1,31 | 5–20 | 5 | sezon sonu | 2 (rakip motivasyonu; rakip ilk 11) |
| **Brighton** – Forest | S ber. | 0-0 | 0,72 | −0,90 / +1,10 | −1,59 / −1,36 | 7–20 | 4 | PL, 4 gün | 2 (Mitoma, van Hecke, Colwill yok) |
| **Man United** – Forest | K | 3-0 | 0,72 | +0,72 / +1,83 | +1,67 / +0,08 | 5–19 | 6 | PL, 4 gün | **0** (erişilebilir kaynak yok) |
| **Hoffenheim** – St. Pauli | S kayıp | 0-1 | 0,62 | +0,81 / +2,83 | +0,98 / +1,13 | 3–16 | veri yok | veri yok | **0** (erişilebilir kaynak yok) |
| **Frankfurt** – Augsburg | K | 1-0 | 0,59 | −0,13 / −0,62 | +0,16 / −0,77 | 7–14 | 4 (ŞL sonrası) | BL, 7 gün | 1 (Larsson döndü) |
| **Freiburg** – Darmstadt | S ber. | 1-1 | 0,74 | −0,71 / −1,17 | −0,30 / −0,61 | 8–15 | 13 (milli ara) | **AL, 5 gün** | 3 (Röhl, Günter yok; rakipte Klarer cezalı) |
| **Leverkusen** – Wolfsburg | K | 2-0 | 0,74 | +1,37 / +2,35 | −0,69 / −0,69 | 1–13 | 3 (AL sonrası) | **AL, 4 gün** | 1 (rakipte ceza/sakatlık) |
| **Barcelona** – Leganés | S kayıp | 0-1 | 0,85 | −1,68 / −1,28 | −0,10 / +0,68 | 1–17 | 4 (ŞL sonrası) | LL, 6 gün | 2 (TD kenar cezalı; rotasyon ihtimali; rakipte 4 eksik) |
| **Real Madrid** – Valladolid | K | 3-0 | 0,83 | −0,53 / +0,71 | +0,97 / +0,06 | 13–6 (2. hafta) | 7 | LL, 4 gün | 0 (Valladolid sayfası tarihsiz) |
| **Athletic** – Osasuna | S ber. | 0-0 | 0,65 | −0,24 / +0,59 | −1,09 / −0,83 | 4–14 | 14 (milli ara) | LL, 7 gün | 1 (rakipte kaleci cezalı, 3 sakat) |
| **Osasuna** – Valladolid | K | 1-0 | 0,65 | +1,05 / +1,50 | −0,86 / −1,33 | 8–19 | 6 | **Kupa, 3 gün** | 0 (sayfa tarihsiz/404) |
| **Lazio** – Salernitana | S kayıp | 1-3 | 0,76 | +1,41 / +1,63 | −0,06 / +1,14 | 3–11 | **3 (AL sonrası)** | **AL, 4 gün** | 1 (Immobile yok) |
| **Roma** – Monza | K | 3-0 | 0,75 | +0,83 / +0,12 | veri yok (yeni takım) | 6–20 | 3 | SA, 5 gün | 1 (Wijnaldum, Zaniolo yok) |
| **Juventus** – Salernitana | S ber. | 1-1 | 0,75 | −0,03 / −1,37 | −1,02 / −2,29 | 4–20 | 7 | **Kupa finali, 3 gün** | 0 (eksik listesi okunamadı) |
| **Napoli** – Sassuolo | K | 2-0 | 0,76 | −0,33 / −0,69 | −1,93 / −1,94 | 5–16 | 8 | SA, 6 gün | 1 (Kvaratskhelia kadroya döndü) |

Kalın yazılan takım favoridir. Kısaltmalar: AL = Avrupa Ligi, ŞL = Şampiyonlar Ligi, PL = Premier League, BL = Bundesliga, LL = La Liga, SA = Serie A.

## 3. Doğrulanmış sakatlık, kadro ve teknik direktör haberleri (17 kanıt)
Hepsi maç başlamadan önce yayımlanmış ve maç öncesinde bilinebilir. "Aynı gün" işaretli olanlar maç gününe ait; bunlardan yayın saati doğrulanamayanlar ayrıca belirtildi.

| Maç | Bilgi | Kaynak (sınıf) | Yayın | Olası etki |
|---|---|---|---|---|
| Sheffield–Brentford (S) | Rakip Sheffield aynı hafta teknik direktörü görevden aldı | brentfordfc.com (resmî) | 07.12.2023 15:00Z | 1X2 belirsizliği (yeni TD) — nicel etki hesaplanamaz |
| Sheffield–Brentford (S) | Favoride Mbeumo darbe aldı (oynamayacağı sayfada kesin değil) | brentfordfc.com (resmî) | 07.12.2023 | Favori hücumu |
| Sheffield–Tottenham (K) | Küme düşmüş rakip teknik direktörü "sezonu iyi bitirmek" istiyor | thestar.co.uk (tek kaynak) | 18.05.2024 | Nitel |
| Sheffield–Tottenham (K) | Rakip ilk 11'inde 3 değişiklik; cezalı ve sakat oyuncular döndü | thestar.co.uk (tek kaynak) | 19.05.2024 14:00Z (maç 15:00Z) | Rakip kadrosu |
| Brighton–Forest (S) | Favoride Mitoma, van Hecke ve Colwill yok (teknik direktör alıntısı) | sussexexpress (tek kaynak) | 17.10.2022 | Favori hücum ve savunma |
| Brighton–Forest (S) | Kesin ilk 11: Mitoma ayak bileği sakatlığı nedeniyle yok | sussexexpress (tek kaynak, aynı yayıncı) | 18.10.2022 17:49Z (maç 18:30Z) | Favori hücumu |
| Frankfurt–Augsburg (K) | Favoride Larsson sakatlıktan döndü | en.eintracht.de (resmî) | 12.12.2025 | Favori lehine |
| Freiburg–Darmstadt (S) | Favoride Röhl büyük olasılıkla yok; kırmızı kart cezalıları döndü | scfreiburg.com (resmî) | 23.11.2023 | Favori orta sahası |
| Freiburg–Darmstadt (S) | Favoride kaptan Günter yok (önkol enfeksiyonu) | sv98.de (rakip kulüp, tek kaynak) | 23.11.2023 | Favori savunması |
| Freiburg–Darmstadt (S) | Rakipte Klarer cezalı | sv98.de (resmî) | 23.11.2023 | Favori lehine |
| Leverkusen–Wolfsburg (K) | Rakipte bir sol bek cezalı, Rogerio şüpheli | bayer04.de (rakip kulüp, tek kaynak) | 09.03.2024 | Favori lehine |
| Barcelona–Leganés (S) | Favorinin teknik direktörü Flick kenarda olmayacak (ceza) | fcbarcelona.com (resmî) | 14.12.2024 | Nitel; nicel etki hesaplanamaz |
| Barcelona–Leganés (S) | Flick "rotasyon olabilir"; Araujo dönüyor; rakipte 3 sakat, 1 cezalı | fcbarcelona.com (resmî) | 15.12.2024 (aynı gün, saat yok) | Karşı senaryo: rotasyon |
| Athletic–Osasuna (S) | Rakipte kaleci Herrera cezalı, 3 oyuncu sakat | osasuna.es (resmî) | 30.03.2025 (aynı gün, saat yok) | Favori lehine |
| Lazio–Salernitana (S) | Favoride Immobile yok | corrieredellosport (tek kaynak) | 29.10.2022 (güncelleme 30.10 12:50, maç 18:00) | Favori hücumu |
| Roma–Monza (K) | Favoride Wijnaldum ve Zaniolo yok; rakipte 3 eksik | corrieredellosport (tek kaynak) | 30.08.2022 10:08 | Favori orta saha/hücum |
| Napoli–Sassuolo (K) | Favoride Kvaratskhelia kadroya döndü | corrieredellosport (tek kaynak) | 27.08.2023 17:25 (maç 20:45) | Favori lehine |

Hiçbir bilgi "çok kaynak" düzeyine çıkmadı: ikinci, bağımsız bir yayıncı bulunamadı ya da erişilemedi. Bu yüzden hiçbir kanıta yüksek güven verilmedi.

## 4. Sürprizlerde ve kontrollerde görülen işaretler (keşif; n = 8'e karşı 8)
| İşaret (maç öncesi bilinebilir) | Sürpriz (8) | Kontrol (8) | Yorum |
|---|---|---|---|
| Doğrulanmış en az 1 haber | 6 | 5 | Erişim farkı var: kontrollerden 3'ünde kaynak yoktu ya da sayfa tarihsizdi |
| **Favori tarafında doğrulanmış eksik veya sakatlık** | **4 oyuncu eksiği** (Brighton, Freiburg, Lazio; Brentford'da Mbeumo yalnızca darbe, kesin değil) + Barcelona'da teknik direktör cezası | **1** (Roma) | En belirgin fark; ama küçük örneklem ve erişim yanlılığı |
| Favori teknik direktörü kenarda değil / rakipte TD değişimi | 2 (Barcelona; Sheffield'ın yeni TD'si) | 0 | Hipotez |
| Rakip tarafında eksik (favori lehine) | 3 (Darmstadt, Leganés, Osasuna) | 2 (Wolfsburg, Monza) | Ayırt etmiyor |
| ±4 gün içinde Avrupa/kupa maçı (favori) | 3 (Barcelona, Lazio, Juventus kupa finali) | 3 (Frankfurt, Leverkusen, Osasuna) | Ayırt etmiyor |
| Milli ara sonrası ilk maç | 2 (Freiburg, Athletic) | 0 | Hipotez; sürpriz maçların ikisi de berabere |
| Favori formu (son 5) < 0 | 6 | 4 | Zayıf fark (60'lık setle tutarlı) |
| Rakip formu (son 10) > 0 | 3 | 2 | Zayıf |
| Ortak rakiplere karşı favori − rakip (maç başı puan) | ort. +0,85 (n=8) | ort. +1,23 (n=5; 3 maçta sezon başı, ortak rakip yok) | Kontrollerde fark daha büyük — favori üstünlüğü sürprizlerde daha dar |

**Yanlılık uyarıları:**
- Sürpriz maçlarda kaynak bulma oranı daha yüksekti. Kontrol maçlarından ikisinde (Man United, Real Madrid) favorinin kendi sitesi kullanılamadı. Bu, "favori eksikleri" farkını kısmen açıklayabilir.
- Kanıtların çoğu tek kaynak düzeyinde.
- n=8'e karşı 8 olduğu için hiçbir fark istatistiksel olarak sınanamaz.

## 5. Erişilemeyen kaynaklar ve nedenleri
| Host | Neden | Karar |
|---|---|---|
| www.bundesliga.com | Koşullar: "otomatik programlar ve botlar içeriğe erişemez ve indiremez"; metin ve veri madenciliği hakkı saklı | Kullanılmadı |
| www.tottenhamhotspur.com | Koşullar: bot, crawler ya da scraper ile veri toplama yasak | Kullanılmadı |
| www.realmadrid.com, www.cdleganes.com | Koşullar: otomatik betik ve "screen scraping" yasak; sistematik veri toplama yasak | Kullanılmadı |
| www.sscnapoli.it | Koşullar: hizmetlere otomatik araçlarla erişim yasak | Kullanılmadı |
| www.fcstpauli.com, www.sslazio.it, www.hessenschau.de, www.kicker.de | `robots.txt` ClaudeBot ve anthropic-ai ajanlarını engelliyor (kicker ayrıca 403) | Kullanılmadı |
| www.tsg-hoffenheim.de, www.athletic-club.eus | HTTP 403 | Engel aşılmadı |
| www.noticiasdenavarra.com, www.deia.eus | HTTP 406 | Engel aşılmadı |
| www.sassuolocalcio.it | Bot doğrulaması işareti | Engel aşılmadı |
| www.ussalernitana1919.it | Yanıt yok | — |
| sport.sky.it | Ana sayfa "Error" döndü | — |
| www.sufc.co.uk, www.nottinghamforest.co.uk | İçerik yalnızca JavaScript ile oluşuyor (tarayıcı taklidi yasak) | Kullanılmadı |
| www.manutd.com | Kullanım koşulları sayfası 403 → koşullar doğrulanamadı | İhtiyatla kullanılmadı |
| www.brightonandhovealbion.com, www.juventus.com | Koşullar sayfası JavaScript ile oluşuyor → okunamadı | İhtiyatla kullanılmadı |
| www.acmonza.com | Koşullar sayfası bulunamadı | Kullanılmadı |

**Kullanılan hostlar** (koşullar özel ve ticari olmayan okumaya izin veriyor; içerik kopyalanmadı, yalnızca URL, tarih, kendi cümlemizle kısa iddia ve sayfa özeti tutuldu):
- PL: brentfordfc.com, thestar.co.uk, sussexexpress.co.uk
- BL: bayer04.de, scfreiburg.com, eintracht.de, en.eintracht.de, fcaugsburg.de, sv98.de, vfl-wolfsburg.de
- LL: fcbarcelona.es, fcbarcelona.com, realvalladolid.es, osasuna.es
- SA: asroma.com, corrieredellosport.it

## 6. Veri kalitesi ve eksiklikler
- **Kaynak hiç yok:** 2 maç (Man United–Forest, Hoffenheim–St. Pauli). Kullanılabilir hiçbir host yoktu.
- **Yayın tarihi yok:** realvalladolid.es sayfalarında tarih bulunmuyor. Bu yüzden 2 bilgi "doğrulanamadı" sayıldı (Real Madrid ve Osasuna maçları).
- **Kadro listesi okunamadı:** Corriere'nin Juventus ve Napoli sayfalarındaki "indisponibili" tabloları sayfanın düz metninde yok. Arama özetindeki liste kanıt sayılmadı.
- **Maç günü yayınlarında saat eksik:** 2 kanıtın (Barcelona önizlemesi, Osasuna kadrosu) yayın saati doğrulanamadı. İçerik türü maç öncesine ait.
- **Arama özetleri bir kez daha hatalı çıktı:**
  - Juventus eksik listesi eski bir sezondan karıştı.
  - Bir Darmstadt sayfasında 2026 tarihli yan haber asıl haberle karıştı.
  - Birçok özet maç sonucunu içeriyordu.
- **Fikstür:** Wikipedia 28 maddeden 27'sini sağladı; Hoffenheim 2025-26 maddesi yok. Takvim bilgisi resmî maç raporlarıyla karşılaştırılmadı.
- **Yapısal eksikler:**
  - Rotasyon ve kesin ilk 11 çoğu maçta yalnızca maç saatine yakın yayımlanıyor; tarihsel olarak arşiv sayfaları dağınık.
  - X ve Reddit giriş gerektirdiği için kullanılmadı.
  - Takım muhabirlerinin içeriği çoğunlukla engelli hostlarda.

## 7. Gelecek maçlarda araştırılmaya değer işaretler (hipotez — modele eklenmedi)
1. **Favori tarafında maç öncesi doğrulanmış eksik.** Kilit oyuncu (hücumcu, kaptan, kilit orta saha) yok mu? En belirgin farkı bu işaret gösterdi (oyuncu eksiği 4'e karşı 1), ama erişim yanlılığı var.
   - Önce ileriye dönük maçlarda, hem sürpriz hem kontrol için aynı kontrol listesiyle toplanmalı.
   - Oyuncu önemi ancak lisanslı ve yapılandırılmış dakika/ilk 11 verisi olursa ölçülebilir.
2. **Teknik direktör olayı.** Favori teknik direktörünün cezalı olması ya da rakibin yeni teknik direktörü (yeni hoca etkisi). Kolay ve tarafsız toplanabilir; resmî kaynakta açıkça yazıyor.
3. **Milli ara sonrası ilk maç** ve **büyük bir kupa veya Avrupa maçından önceki son lig maçı** (rotasyon riski; Juventus örneğinde kupa finali 3 gün sonraydı). Wikipedia fikstüründen tarafsız ve otomatik hesaplanabilir. 60 maçlık ve 4 ligin bütün favori maçlarında hemen test edilebilir.
4. **Favori formu (son 5).** Önceki çalışmalarda yalnızca beraberlikler için zayıf bir işaret gösterdi.

Ayırt etmeyen işaretler: rakip eksikleri ve sadece "Avrupa maçı var/yok".

## 8. Önerilen sonraki adımlar (onay gerekiyor)
- 3. maddedeki fikstür işaretlerini (milli ara, kupa veya Avrupa maçından önceki/sonraki gün sayısı) 4 ligin bütün favori maçlarında Wikipedia'dan hesaplayıp ölçmek. Ön kayıttaki F3/F4'ün tüm kulvarlara genişletilmiş hali olur.
- 1. ve 2. maddeleri 2026-27'de oynanacak maçlarda ileriye dönük olarak toplamak: tahmini dondur, sonra haberleri kaydet. Gerçek kör test ancak bu olur.
- Kullanılamayan hostların yerine, koşulları uygun alternatif yerel yayıncılar önerilebilir. Her biri için ayrı izin gerekir.
