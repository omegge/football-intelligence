# Sonuç denetimi ve geliştirme — 26.11.2026 (2. oturum; dal wip/model-prototip, temel a57e9e3, commit yok)

Önceki çıktılar silinmedi ya da değiştirilmedi; düzeltmeler ayrı sürüm olarak üretildi. Ayrıntılı sayılar `output/`
(git dışı): `denetim/market_envanteri.json`, `model/denetim_20261126_170417/`, `model/e2_*`, `model/f2_*`,
`arastirma/kesif_j/`.

## 1. Mevcut geliştirmelerin denetimi

### 1.1 Market sayıları envanteri (`output/denetim/market_envanteri.json`)
| Sayı | Yöntem |
|---|---|
| 190 | sözlükteki bütün anahtarlar |
| 104 | şablon olmayan `KOD|çizgi` anahtarları (`Sozluk.kod_sayisi`; "104 marketlik" yazımı buradan) |
| 86 | benzersiz market kodu (her kodun bir `KOD|*` şablonu var; 78 kodun 1, 8 kodun 2–6 çizgili anahtarı) |
| 1.208 | ham bülten seçeneği (iki maç: 830 + 378) |
| 1.203 | arayüz referansı seçeneği (830 + 373) |
| 5 | fark = arayüzde görünmeyen iki MS=0 marketinin (457/0,5 ve 224) seçenekleri; birebir açıklanıyor |
1.208 ve 1.203 ayrı tutulur; biri diğerinin yerine kullanılmaz. 329 aday kaldı (1/2 bağımsız doğrulama).

### 1.2 Eşdeğerlik kapsamı (90 dk) ve değerlendirme kuralları
- **Doğrulanmadı.** Nesine'nin kendi kural metni bulunamadı (web araması: yalnızca başka şirketlerin genel kuralları —
  "normal süre + uzatma dakikaları, uzatma devresi/penaltı hariç"). Bunlar Nesine için kanıt sayılmaz.
- Eşdeğerlik çıktısındaki `kapsam_kaynagi` alanı bunu her grupta yazıyor; kural metni okunana kadar "kontrol gerekli".
- Kurala duyarlı seçenekler: 291 "Olmaz" (kendi kalesine gol/iptal), 777/779 "diğer", 329 aday → kontrol gerekli;
  "Uzt. Dahil", tam/çeyrek çizgi (iade), korner/kart/oyuncu → eşlenmez. Alt küme karşılaştırması yalnızca kesin ve
  oynanabilir seçenekler arasında; farklı kural kapsamındaki marketler (uzatma dahil) hiç karşılaştırılmaz.

### 1.3 Skor ızgarası sınırı (takım başına devre 7, maç 14)
- **Hata (düzeltildi):** `pazar_modelleri.gozlenen` golleri 10'a kırpıyordu (11-10 beraberlik sayılırdı). E verisinde bir
  maç etkilendi (nl.1 2020-21 VVV–Ajax 0-13: tek/çift yanlış); ölçüme etkisi < 1e-5 (yeniden çalıştırmada doğrulandı).
- **Hata (düzeltildi):** `f_asamasi.nokta` devre gollerini 7'ye kırpıyordu; artık ızgara dışı maç dışarıda bırakılıyor.
  F liglerinde böyle maç yok (etki 0).
- **Sınır koruması sıkılaştırıldı:** maç skoru ≤ 13, devre skoru ≤ 6, maç çizgisi ≤ 12,5, devre çizgisi ≤ 5,5.
- **Değişmezlik testi:** UST=7 ve UST=10 ile bütün bülten (102 maç): eşlenen 13.388 = 13.388, grup bölümlemesi farklı maç 0.

### 1.4 MK-1 yapısal doğrulama (`tests/test_mk1_akis.py`)
- İçe aktarma grafiği (AST, geçişli): olasılık/veri modülleri (`fi.model`, `fi.kaynaklar`, `fi.haber`, `fi.girdi`, …)
  fiyat modüllerine (`fi.pazar`, bülten betikleri) bağlı değil.
- **Bulgu (düzeltildi):** `f_asamasi` olay tanımları için fiyat paketi `fi.pazar.esdegerlik`'i içe aktarıyordu (oran
  okumuyordu ama bağımlılık vardı). Olay uzayı fiyat içermeyen `fi/olay_uzayi.py`'ye taşındı; çıktılar birebir aynı.
- Çalışma anı: `bagimsiz_tahmin` sırasında açılan dosyalar izlendi; bülten dosyası açılmıyor.
- Dondurulmuş kayıt fiyat karşılaştırmasından sonra bayt bayt aynı; olasılık değişmiyor.

## 2. Önceki model sonuçlarının denetimi (`fi/model/denetim.py`)
| Konu | Bulgu |
|---|---|
| Zaman ayrımı / sızıntı | E, F: yürüyen test, `egitim_kesimi < tarih` her maçta doğrulandı; taban yalnızca tarih öncesi maçlardan. D: sıralı lojistik yalnızca geçmiş sezonlardan. H: tarih öncesi maçlar. Sızıntı bulunmadı. |
| Tekrarlanabilirlik | E (10.158 maç) ve F-v2 (5.877) yeniden çalıştırıldı: bütün marketlerde fark < 1e-5. |
| Bağımlılık ve GA | v1 tarih kümeli. Hafta ve lig-sezon kümeli (E 35, F 15 küme) GA ile E ve F'de hiçbir karar değişmedi. **D'de değişti:** M1−B1 −0,013; tarih kümeli [−0,025; −0,001], takım kümeli [−0,026; −0,001], **sezon kümeli [−0,021; +0,001] (0'ı içeriyor)**; M1 8 sezonun 6'sında iyi. "Anlamlı iyileşme" ifadesi sezonlar arası sağlam değil. |
| Taban | Genişleyen pencere lig frekansı (2010'dan beri; durağan değil). Sonuç marketlerinde model farkı büyük; toplam gol marketlerinde model zaten tabanı geçemiyor. Daha güçlü taban (365 gün) kararları ancak daha da olumsuz yapabilir. |
| Eksik ilk yarı | F-v1 seçilim yanlılığı (0-0 maçlarda İY yazılmıyor) v2'de mantıksal tamamlamayla giderildi; F2'de aynı kural. |
| Lig bazında kalibrasyon | Havuz ECE'si lig sorunlarını gizliyor: MS 1 havuz 0,016 ama es.2 0,044; MS 2 es.2 0,052; AÜ 2,5 de.2 0,078; 1Y KG it.2 0,041. |
| Sezon genellemesi | E: MS 1'de model 35 lig-sezonun 32'sinde, AÜ 2,5'te yalnızca 15'inde, KG'de 10'unda tabandan iyi. |

## 3. Güncel veri
- **football-data.org ücretsiz plan (mevcut onaylı anahtar, ortam proxy'si):** 2026-27 sezonu `season=2026` ile
  9 kulüp yarışmasında ilk yarı skorlarıyla geliyor (PL 110, ELC 204, BL1 90, SA 120, PD 129, FL1 99, DED 117, PPL 98,
  CL 90 biten maç; son maçlar 22–25.11, PPL 08.11).
  **Bulgu:** uzun tarih aralıklı sorgu bu planda sessizce eksik dönüyor (ELC 80 vs 204); önceki `calistir.fdorg_ekle`
  (PL) tarih aralığı kullanıyordu → güvenilmez sayıldı; yeni `kaynaklar/guncel.py` yalnızca `season=` kullanır.
- **Çapraz doğrulama:** OpenFootball ile çakışan 513 maçta maç sonu ve ilk yarı skorları %100 aynı (uyuşmazlık 0).
  Eşlenemeyen tek takım: pt.1 "Vitória SC" (11 maç eklenmedi, aday listesinde).
- **OpenLigaDB:** ODbL; Almanya ligleri düzenli, UEFA kupaları topluluk girişi ve parçalı (`ucl2026` yer tutucu, `ucl` güncel).

### Kaynak tablosu
| Kaynak | İzin / lisans | Kapsam | Güncellik | Maliyet | Karar |
|---|---|---|---|---|---|
| OpenFootball | CC0 (LICENSE.md) | 47 lig dosyası, 2010–2027, İY skoru ~%93 | son 2026-09-20 | ücretsiz | kullanılıyor (geçmiş) |
| football-data.org (ücretsiz) | Koşullar 2018: anahtar gizli, atıf zorunlu | 12 yarışma (9 kulüp), İY, hakem adı | 22–25.11.2026 | ücretsiz | kullanılıyor (güncel, onaylı anahtar) |
| OpenLigaDB | ODbL 1.0, adil kullanım | Almanya 1–3, UEFA kupaları (parçalı) | 2026-11-25 (UCL) | ücretsiz | aday (adlar Almanca; onaylı eşleme gerekir) |
| martj42/international_results | CC0 | milli takımlar | 2026-11-17 | ücretsiz | kulüp için yok |
| TheSportsDB | resmî koşullar okunamadı (yalnızca ikincil kaynak/ayna) | genel | ? | ücretsiz anahtar "123" | kullanılmaz (koşul doğrulanmadı) |
| fixturedownload.com | koşul metni bulunamadı | fikstür | ? | ? | kullanılmaz |
| football-data.co.uk, ClubElo, StatsBomb, FBref, Understat, Sofascore, FotMob, Transfermarkt | AI/bot yasağı ya da kullanıcı kararı | — | — | — | kullanılmaz |
| football-data.org ücretli, API-Football | ücretli / hesap gerekir | — | — | ücretli | kullanılmaz |
Korner, kart (çok sezonlu), oyuncu istatistiği, beklenen 11: izinli kaynak yok (veri bekliyor).

## 4. Lig ve takım eşleme adayları
- `veri/lig_esleme_adaylari.json` (otomatik; HİÇBİRİ ONAYLI DEĞİL). Kanıt: Nesine takımlarının kaynak lig kadrosuyla
  "kesin" eşleşmesi + benzerlik önerisi (yalnızca lig adayı için). Güçlü aday: "İngiltere Championship" (52) → en.2,
  "İtalya Serie B" (1774) → it.2, "İskoçya Premiership" (149) → sco.1. "İngiltere 1. Lig" (24) → en.3 yalnızca zayıf
  aday (10 takımdan 3 kesin). Tuzak örneği: "İtalya Serie A" (Monza, Fiorentina) en çok it.2'ye benziyor (Monza
  2025-26'da Serie B) → kadro sezonu eski olabilir; otomatik onay yok.
- `veri/openligadb_takim_adaylari.json`: aynı UTC dakikasında başlayan maç + birebir ortak rakip adı kanıtıyla 20 aday
  (ör. "Ferencváros Budapest" → "Ferencvaros", rakip "NK Celje" birebir). Olympiakos–Milan, Escaldes–Kopenhag: aynı
  dakikada başka maçlar var ve birebir ortak ad yok → aday üretilmedi.
- `veri/lig_eslemeleri.json` boş kaldı (onay bekliyor).

## 5. Gol modeli iyileştirmesi (E2; ön kayıt `ON_KAYIT_E2.md`, SHA-256 cf90aefd…)
- Geliştirme (fr.1, nl.1, pt.1, de.2, es.2; 10.158 maç): ceza 16 seçildi (gol ölçütü 0,5233 → 0,5179, 1X2 ≤ +0,001);
  M3 hiyerarşik büzülme w = 0,65, b = 0 → 0,5169; negatif binom (r 5–40) daha iyi değil (≥ 0,5171).
- **Sınama (en.2 + football-data.org 2026-27, at.1, be.1, sco.1, tr.1, gr.1; 7.861 maç; tek çalıştırma; tutarlılık ihlali 0):**

| Market | M0 − taban | Aday − taban (GA üst) | Aday − M0 (GA üst) | ECE M0 → aday | Günlük kapsam |
|---|---|---|---|---|---|
| AÜ 2,5 | +0,0077 | −0,0033 (−0,0010) | −0,0110 (−0,0087) | 0,048 → 0,018 | hayır (bir lig ECE 0,046) |
| AÜ 1,5 | +0,0049 | −0,0026 (−0,0006) | −0,0076 (−0,0052) | 0,036 → 0,011 | hayır (sapmalı kutu) |
| AÜ 3,5 | +0,0075 | −0,0038 (−0,0015) | −0,0113 (−0,0095) | 0,048 → 0,009 | hayır (sapmalı kutu) |
| AÜ 4,5 | +0,0041 | −0,0034 (−0,0011) | −0,0075 (−0,0051) | 0,029 → 0,009 | **evet** |
| KG var | +0,0055 | −0,0025 (−0,0001) | −0,0080 (−0,0057) | 0,045 → 0,014 | **evet** |
| MS 1 | −0,0435 | −0,0428 | +0,0007 (+0,0040) | 0,025 → 0,025 | hayır (lig ECE 0,066) |
| MS X | −0,0037 | −0,0041 | −0,0004 (+0,0008) | 0,015 → 0,013 | evet |

  Sonuç: toplam gol ve KG marketlerinde **M0'a göre anlamlı ve tutarlı iyileşme** (bütün AÜ çizgileri, KG, gol aralığı);
  E'deki "tabanı geçemiyor" sorunu bu liglerde giderildi. 1X2'de iyileşme yok. Günlük kapsam: 26 seçenek
  (`veri/model_kapsami.json`, yalnızca bu 6 ligde). Dixon–Coles M0'a göre her markette ≈ 0 fark.

## 6. İlk yarı / ikinci yarı (F2; ön kayıt `ON_KAYIT_F2.md`)
- Geliştirmede (it.2, fr.2, en.3, en.4; 5.069 maç) durum etkisi: 1Y önde olan takımın 2Y hız çarpanı 0,993, geride
  olanınki 1,076.
- Sınamada (6 lig, 6.968 maç): F1 − F0 farkı ≤ 0,001 log loss; 62 seçenekten 6'sında anlamlı. 1Y KG–2Y KG olasılık
  oranı gözlenen **1,00** (geliştirmede 1,20), F0 1,11, F1 1,10 → bağımlılık ligden lige değişiyor; model yakalamıyor.
- Marjinal 1Y marketleri (209, 14, 15, 452, 455) tabanı geçmiyor; 1Y 0,5 üst gerçekleşen − tahmin +0,023 (model 1Y
  gollerini düşük veriyor). 7, 9: yalnızca bazı seçenekler taban üstü, kalibrasyon sınırda.
- Kuralları geçen 3 seçenek (İY/MS X/2, 587 "2.", 779 "0:1") çoklu karşılaştırma riski nedeniyle kapsam dışı.
  **Devre marketleri hesaplanamaz.**

## 7. Haber ve sürpriz (J)
- Keşif (`output/arastirma/kesif_j/`): sayısal maç öncesi özelliklerin hiçbiri sürpriz/kontrol ayrımında anlamlı değil.
  Favori aleyhine doğrulanmış haber: sürpriz 5/8, kontrol 1/8 (Fisher p = 0,119; araştırma sonuç bilinerek yapıldı).
- İleriye dönük test ön kaydı: `ON_KAYIT_J.md` (kör araştırma, ≥ 150 işaretli maç, haber olasılığa eklenmez).
- Bağımsız tahmine katkı: **kanıtlanmadı.**

## 8. Günlük hazırlık kapısı
`is_akisi.bagimsiz_tahmin` her maç için kriterleri kanıtıyla yazar: lig eşlemesi onaylı · model bu ligde ileriye dönük
değerlendirildi · lig verisi var · veri ≤ 14 gün · iki takım kesin/onaylı · test edilmiş ve kalibre market var · veri
kesimi kaydedildi · olasılık oranlardan önce dondurulacak. Biri sağlanmazsa "hesaplanamaz". Kapsam
`veri/model_kapsami.json`'dan (SHA-256 her tahminde kaydedilir).
- 26.11 bülteni (94 maç): hepsi "lig_eslemesi_onayli" kriterinde kalıyor; 92'si izinli verisi olmayan liglerde
  (UEFA kupaları vb.), 2'si zayıf aday. Onay verilse bile bugün hiçbir maç model liglerinde değil.
- Simülasyon (onaysız lig eşlemesi varsayımıyla, dondurulmadı): Southampton – Middlesbrough (ELC, 27.11 23:00 TR) bütün
  kriterleri geçiyor (veri kesimi 25.11, E2 modeli, 26 market).

## Çalıştırılan testler
`PYTHONPATH=lib python3 -m unittest discover -s tests` → 215 test, hepsi geçti (önceki 195 + 20 yeni).
