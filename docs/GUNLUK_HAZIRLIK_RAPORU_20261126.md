# Günlük analize hazırlık ve derin haber araştırması — 26.11.2026 (3. oturum)

Dal wip/model-prototip (temel a57e9e3; commit/push yok). Önceki çıktılar değiştirilmedi; yeni sürümler ayrı klasörlerde.

## 1. Çalışma ağacı
Denetim (215 test) ve geniş haber katmanı (+12 → 227) aynı dalda, birlikte çalışıyor. Bu oturumla 236 test, hepsi geçti.
Bekleyen: 4 değişmiş dosya + yeni dosyalar (git status). Gizli bilgi taraması temiz.

## 2. Lig eşlemeleri — fikstür hizalaması kanıtı (`veri/lig_esleme_kanitlari.json`)
Kanıt = Nesine yarışma kimliği + ülke + football-data.org yarışma kodu + 2026-27 sezonu + aynı UTC başlama dakikasında
iki takımın eşleşmesi. Takım benzerliği tek başına kanıt değildir.

| Nesine ligi [kimlik] | Ülke | Kaynak | Hizalama | Durum |
|---|---|---|---|---|
| İngiltere Championship [52] | ENG | ELC → en.2 | Southampton–Middlesbrough ↔ Southampton FC–Middlesbrough FC, 20:00 UTC, kesin/kesin | **kesin eşleme adayı** |
| İngiltere Premier Lig [43] | ENG | PL → en.1 | "Nottingham F." ad onayı | güçlü aday |
| Almanya Bundesliga [45] | DE | BL1 → de.1 | "M'gladbach" ad onayı | güçlü aday |
| İtalya Serie A [143] | IT | SA → it.1 | "Bologna" ad onayı | güçlü aday |
| İspanya La Liga [129] | ES | PD → es.1 | "Santander" ad onayı | güçlü aday |
| Fransa Ligue 1 [381] | FR | FL1 → fr.1 | "Brest", "Paris" = **Paris FC (PSG değil)** | güçlü aday |
| Hollanda Eredivisie [322] | NL | DED → nl.1 | "Willem II" ↔ "Willem II Tilburg" ad onayı | güçlü aday |
| Portekiz Premier Lig [566] | PT | PPL | iki ad da onay gerektiriyor | uyuşmuyor |
| Hollanda 1. Lig [681] | NL | DED | Eerste Divisie; ücretsiz planda yok | uyuşmuyor |
Hiçbiri onaylanmadı (`veri/lig_eslemeleri.json` boş).

## 3. Southampton – Middlesbrough (ilk gerçek pilot)
- Nesine 3331002, "İngiltere Championship" [52], 27.11 23:00 TR (26.11 20:57 TR bülteni) = football-data.org 561968,
  2026-11-27T20:00Z, SCHEDULED. Hakem henüz atanmadı (hakem etkisi uygulanmaz).
- Hazırlık kapısı: lig onayı DIŞINDA bütün kriterler veriyle sağlanıyor (veri kesimi 25.11, E2, 26 seçenek). Onay
  olmadığı için gerçek dondurulmuş tahmin OLUŞTURULMADI.

## 4. E2 günlük kapsam (26/60) — `output/denetim/E2_KAPSAM_TABLOSU.md`
Kapsam dışı nedenleri (çakışabilir): n≥30 kutularda sapma > 0,05 → 24; bir ligde ECE > 0,04 → 13; tabanı geçmiyor → 8;
havuz ECE > 0,02 → 5. Kullanım yalnızca en.2, at.1, be.1, sco.1, tr.1, gr.1 (bugün güncel veri yalnızca en.2'de).
**Yöntem notu:** n = 30 kutuda örnekleme hatası ≈ ±0,09; "sapma > 0,05" kuralı gürültülü ve tutucudur. Geriye dönük
değiştirilmedi; sonraki ön kayıtta güven aralıklı kalibrasyon testi önerilir. Kalibrasyonu başarısız market açılmadı.

## 5. Güncel veri güncelleme yöntemi
`PYTHONPATH=lib python3 -m fi.kaynaklar.guncel guncelle` → 9 yarışma `season=2026`; her çekim
`output/guncel/<UTC>/` altında (SHA-256). Bütünlük: son tam haftadan önce kayıt eksikliği (ertelenen maç ayrı bilgi),
mükerrer eşleşme, skorsuz biten, önceki çekime göre kaybolan biten maç ve değişen skor. İlk iki çekim: 9/9 temiz
(PD'de ertelenen Rayo–Athletic doğru biçimde "bilgi" olarak ayrıldı).

## 6. İlk yarı / ikinci yarı başarısızlık analizi
1Y KG–2Y KG olasılık oranı lig bazında 0,73 (be.1) – 1,65 (fr.2); olay sıklığı ~%5 → lig başına ~50 olay, log OR
standart hatası ≈ 0,18. Lig farkının büyük kısmı örnekleme gürültüsü olabilir: bağımlılığı güvenilir öğrenmek için veri
yetmiyor. 1Y gol payı 0,43–0,46 (istikrarlı); 1Y marjinallerindeki sapma büyük olasılıkla E'deki aşırı yayılmanın devre
düzeyine yansıması. Öneri (yeni ön kayıt, ileriye dönük 2026-27 verisiyle): E2 büzülmesini devre hızlarına taşıyan F3.
Aynı sınama liglerinde yeniden ayar yapılmadı.

## 7. Derin haber araştırması
| | SOU–MID v2 | Groningen–Willem II |
|---|---|---|
| Sorgu | 10 (+v1'in 4'ü) | 3 |
| İddia / grup | 28 / 21 | 15 / 11 |
| Farklı host / bağımsız zincir | 17 / 13 | 6 / 6 |
| İki bağımsız (basın + maç verisi) | 2 | 1 |
| Çelişkili | 3 | 2 |
| Doğrulanmadı | 15 | 8 |
- **Gerçekten bulunanlar (SOU–MID):** iki takımın 24.11 sonuçları (veriyle doğrulandı); Southampton'da Jander/Scienza
  dönüş umudu ve Larin'in dönüşü (tek basın toplantısı zinciri, 3 kopya); Middlesbrough'da Lankshear hazır (Teesside
  Live) ↔ şüpheli (önizleme) çelişkisi; Alfie Jones, Barron, Pukstas yok; Stamenic cezası tek önizlemede; Eckert'in
  ertelenmiş cezası (FA, 7.10); iki takım da 7 günde 3. maçında (veri).
- **Veriyle çürütülen arama özetleri:** "Boro 21.11'de Derby'yi yendi" (Bristol City'yi yendi), "Boro West Ham'da
  3-2" (Southampton'ın maçı), "FA duruşması bu hafta" (24.09'du).
- **Kendi hatam (düzeltildi):** sonuçlardan hesaplanan puan durumu puan silmelerini içermiyor. "7 puan geride" iddiası
  bildirilen 4 puan silmeyle tutarlı; önceki "veriyle çelişiyor" değerlendirmem yanlıştı. Puan silme doğrulanmadı.
- **Neden çoğu "doğrulanmadı":** bütün haberler web arama özeti; kulüp/yerel basın sayfaları için okuma izni (robots +
  koşullar denetimi) yok. Onay listesi: southamptonfc.com, mfc.co.uk, gazettelive.co.uk, dailyecho.co.uk, thefa.com,
  fcgroningen.nl, willem-ii.nl.
- **Sportif çıkarımlar** raporların 11. bölümünde YORUM olarak ayrı; olasılıklara uygulanmadı.
- Turlar: T−24s yapıldı; T−6s (17:00 TR) ve T−90dk (21:30 TR) yapılmadı (`sou_mid_20261127_v2/TURLAR.md`).

## 8. Sürpriz haber türleri (keşif)
Yalnızca pilot 16 maç (8 sürpriz + 8 kontrol) araştırılmıştı; 30+30 setin kalan 44 maçında haber araştırması yapılmadı.
"Favori eksik/ceza": 5/8 sürpriz (doğru pozitif) vs 1/8 kontrol (yanlış alarm). Geriye dönük seçim ve sonuç bilinerek
araştırma → başarı kanıtı değildir. İleriye dönük protokol: `ON_KAYIT_J.md` + `ON_KAYIT_J_EK.md` (tür tanımları, kör
araştırma, tür başına ≥ 150 işaretli maç).

## 9. İleriye dönük değerlendirmeye hazırlık
| Bileşen | Durum | Eksik |
|---|---|---|
| E2 (gol) | hazır (dondurma + `ileri_puanla`) | lig/takım onayları; şimdilik yalnızca en.2'de güncel veri |
| E Poisson (fr.1, nl.1) | hazır | lig + takım adı onayları |
| F2 (devre) | hazır değil | kapsamda güvenilir seçenek yok; F3 ön kaydı yazılmadı |
| J (haber) | protokol hazır | sayfa okuma onayları; T−6s/T−90dk zamanlayıcısı; ≥150 işaretli maç |

## 10. Bugünkü maçların engelleri — `output/denetim/GUNLUK_ENGELLER.md` (maç bazında)
- 26.11 (94 maç): izinli veri kaynağı yok 92, lig zayıf aday 2.
- 27.11 (174 maç): izinli veri kaynağı yok 153, lig uyuşmuyor 8, lig zayıf aday 6, lig onayı bekliyor 7. Onay
  bekleyenlerden 3'ü onaylarla olasılık alabilir: Southampton–Middlesbrough (E2), Brest–Paris FC ve Groningen–Willem II
  (E Poisson, takım adı onayıyla); diğer 4'ünde model o ligde ileriye dönük değerlendirilmedi.
