# Uçtan uca güncel maç pilotu — SC Freiburg – FC Twente (26.11.2026)

> **Güncel mod.** Araştırma maç başlamadan ~20 saat önce yapıldı. Kesim: 2026-11-25 23:4x UTC. Maç 2026-11-26 20:00 UTC.
> **Dondurma sırası (MK-1):**
> 1. Bağımsız istatistik/tahmin kaydı: `istatistik.json`, SHA-256 `f00a01ee…`, 23:44:04Z.
> 2. Haber kanıtları: `../freiburg_twente_20261126_haber/`, kanıt SHA-256 `08ef67f1…`, 23:45:20Z.
> 3. Ancak bundan sonra Nesine market listesi açıldı.
>
> Oranlardan hiçbir olasılık türetilmedi. Kupon yok.

## 1. Maç seçimi
- **Bülten:** Nesine maç öncesi bülteni 26.11.2026 TR günü için çekildi (tek istek, HTTP 200). 97 futbol etkinliği var.
- **200+ market:** **Bültende 200'den fazla marketi olan maç yok.** En yüksek market sayısı 110 (Beşiktaş – HB Sheva).
- **Dört ligimizde iç lig maçı yok:** Bugün Premier League, Bundesliga, La Liga ve Serie A'da maç oynanmıyor. Bu dört lig modellerin test edildiği liglerdir. Bültenin çoğu Avrupa Ligi ve Konferans Ligi maçlarından oluşuyor.
- **Seçim gerekçesi:** En çok marketi olan maçlarda onaylı ve kullanılabilir hiçbir haber kaynağı yoktu. **Freiburg – Twente**'de favori tarafın resmî sitesi (scfreiburg.com) iki işaretle doğrulanmış ve "kullanılabilir"; takım adı da birebir eşleşti.
- **Seçimde oran kullanılmadı.** Yalnızca market sayısına ve kaynak erişimine bakıldı.

| Alan | Değer |
|---|---|
| Maç | Freiburg – Twente (Nesine kodu 3326598) |
| Lig | UEFA Konferans Ligi, lig aşaması (4. hafta) |
| Başlama (TR) | 26.11.2026 23:00 |
| Market sayısı | 80 (en yüksek 110) |

## 2. Takım ve lig eşleştirmesi (mevcut `TakimEslestirici`)
- **"Freiburg":** OpenFootball de.1'deki "SC Freiburg" ile **kesin** eşleşme. football-data.org adıyla da kesin.
- **"Twente":** OpenFootball nl.1 ile eşleşme **belirsiz** çıktı, otomatik kabul edilmedi. Analizde nl.1'de "twente" içeren tek takım olan "FC Twente '65" kullanıldı.
- **Kalıcı Twente eşlemesi onayınızı bekliyor** (`veri/takim_eslemeleri.json`'a yazılmadı).

## 3. Bağımsız olasılıklar
**Elo, Poisson ve Dixon–Coles: HESAPLANAMAZ.**

Gerekçe:
- Modellerimiz lig içinde çalışıyor: Freiburg için Bundesliga, Twente için Eredivisie. İki ligin ölçekleri birbirine bağlı değil.
- Avrupa kupası, yani ligler arası maçlar için test edilmiş bir model yok.
- Kural: modelin kapsamı dışında güvenilir olmayan yüzde üretilmez.

Bu nedenle model favorisi de belirlenemedi. Favori oranlarla da belirlenmedi (MK-1).

## 4. Maç öncesi istatistikler (yalnızca 25.11.2026'ya kadar oynanan maçlar)
**Kaynaklar:**
- OpenFootball (CC0, 20.09.2026'ya kadar).
- football-data.org ücretsiz plan: Bundesliga ve Eredivisie 2026-27 bitmiş maçları, birer istek. "Football data provided by the Football-Data.org API".
- Wikipedia 2026-27 sezon maddeleri (tüm kulvarlar).

Elo ve form değerleri yalnızca kendi ligi içinde anlamlıdır; iki takım arasında doğrudan karşılaştırılamaz.

| | SC Freiburg (Bundesliga) | FC Twente (Eredivisie) |
|---|---|---|
| Lig içi göreli Elo / sıra | +40 / 18 takım içinde 6. | +118 / 18 takım içinde 4. |
| Bu sezon lig | 10 maçta 22 puan | 13 maçta 27 puan |
| Son 5 / son 10 rakip gücüne göre form (Σ sonuç − Elo beklentisi) | +0,68 / +2,07 | +0,28 / +1,07 |
| Son 10 rakibin ortalama Elo'su | −10,9 (ortalamanın altı) | −5,3 |
| Güçlü rakiplere karşı | Leverkusen 1-2 (deplasman), Bayern 1-3 (iç saha) kaybetti | PSV 3-2 kazandı, AZ 2-0 (deplasman) kazandı, Ajax 2-2, Utrecht 1-2 kaybetti |
| Son 5 lig maçı | G G M G G | B M G G B (+ Excelsior 9-0) |
| Dinlenme (tüm kulvarlar) | 5 gün (21.11 Elversberg 1-0) | 5 gün (21.11 Willem II 2-1) |
| Sonraki maç (maç öncesi bilinen fikstür) | **29.11 RB Leipzig** (3 gün sonra) | **28.11 NEC** (2 gün sonra), 02.12 kupa |
| Konferans Ligi (Wikipedia) | **veri yok** (Freiburg maddesinde Konferans Ligi bölümü yok) | Lig aşamasında 3/3 galibiyet: Thun 1-0, Lincoln 4-1, Pafos 3-1. Ön elemede Qarabağ'ı 0-1 ve 4-1 ile geçti |

**Ortak rakipler:** Ligde yok (farklı ligler). Konferans Ligi'nde Freiburg'un maçları bilinmediği için ortak rakip bulunamadı.

## 5. Haber kanıtları (maç öncesi doğrulanmış, 4 kanıt)
Kaynak: www.scfreiburg.com (kulübün resmî sitesi, "kullanılabilir"). Önizleme 25.11.2026'da, yani maçtan bir gün önce yayımlandı.

| Kategori | Bilgi | Seviye | Olası etki |
|---|---|---|---|
| Kadro | Freiburg'da bütün oyuncular hazır | resmî | ev sahibi lehine (nicel etki: hesaplanamaz) |
| Rotasyon | Schuster: "Rotasyon yapabiliriz, ama maç planına uymalı" | resmî | belirsiz; 3 gün sonra Leipzig maçı var |
| Taktik / rakip | Twente lig aşamasında yenilmedi; "çok oturmuş bir takım"; Schuster onları Elversberg'e benzetiyor | tek kaynak (rakip hakkında, Freiburg'un sitesinden) | ev sahibi aleyhine (nitel) |
| Motivasyon | Ginter: bir galibiyetle sıralamada Twente'yi puanca yakalayabiliriz | resmî | nitel |

**Kanıta alınmayanlar:**
- **Twente kadrosu, sakatlık, ceza, teknik direktör:** Kaynak yok. fctwente.nl ve Hollanda basını (ör. tubantia.nl, nos.nl) izin listesinde değil; www.uefa.com kayıtlı değil (uyum taraması yapılmadı). Arama özetlerinde Twente'ye ait güncel eksik bilgisi yoktu; çıkan tek haber Ekim'deki Thun maçına aitti.
- **Freiburg basın toplantısı:** Yalnızca video olarak yayımlanmış (25.11.2026); metni okunamadı, "doğrulanamadı" sayıldı.
- **Yanlış eşlenen sayfa:** Arama özeti "wollen-kraft-aus-der-atmosphaere-ziehen" sayfasını Twente önizlemesi olarak gösterdi. Sayfa aslında başka bir deplasman maçına (Türk rakip) ait ve tarihsiz. **Kanıt sayılmadı.** Bu, arama özetlerinin neden kanıt olmadığının yeni bir örneği.

## 6. Kazanamama senaryosu ve karşı kanıtlar
Model favorisi belirlenemedi. Aşağıdaki işaretler ev sahibi Freiburg açısından **nitel** olarak sıralandı; olasılığa çevrilmedi.

**Freiburg'un kazanamaması için işaretler:**
- Twente Konferans Ligi'nde 3/3 kazandı ve lig aşamasında yenilmedi (Wikipedia + Freiburg önizlemesi).
- Twente kendi liginde 4. sırada; PSV'yi yendi, AZ'yi deplasmanda yendi.
- Freiburg'un bu sezon güçlü rakiplere karşı iki maçı da kaybedildi (Leverkusen, Bayern). Son 10 rakibinin ortalaması lig ortalamasının altında, yani yüksek form kısmen kolay fikstürden geliyor.
- 3 gün sonra Leipzig maçı var; teknik direktör rotasyon ihtimalini açıkça söyledi.

**Karşı kanıtlar:**
- Freiburg'da bütün oyuncular hazır.
- Maç Freiburg'un iç sahasında; 32.400 seyirci bekleniyor.
- Freiburg son 10 maçta rakip gücüne göre +2,07 formda.
- Twente'nin de yoğun fikstürü var (2 gün sonra NEC, ardından kupa), rotasyon onlar için de olası.
- Twente'nin Konferans Ligi rakipleri (Thun, Lincoln, Pafos) görece zayıf; bunun ölçümü yapılamadı.

## 7. Fiyat karşılaştırması (dondurmadan sonra)
**Yapılmadı.** Karşılaştırılacak bağımsız olasılık yok. Nesine oranlarından olasılık türetilmedi; favori oranlarla belirlenmedi.

80 market olay ailelerine ayrıldı (`3_fiyat_karsilastirma.json`). Hepsi **hesaplanamaz**:

| Aile | Market sayısı | Neden hesaplanamaz |
|---|---|---|
| Maç sonucu ve gol | 23 | Ligler arası model yok |
| Devre golleri | 25 | Ligler arası model yok; ilk yarı/ikinci yarı modeli henüz kurulmadı |
| Birleşik | 9 | Doğrulanmış aile modeli ve bağımlılık modeli yok |
| Korner | 21 | Korner verisi ve modeli yok |
| Oyuncu | 2 | Oyuncu verisi ve modeli yok |

## 8. Çalışan kaynaklar, eksik kalanlar, elle bağlanan modüller
**Çalışanlar:**
- Nesine bülten çekici.
- `TakimEslestirici` (Freiburg için kesin eşleşme).
- OpenFootball ve football-data.org (Bundesliga ve Eredivisie; free planda Konferans Ligi yok).
- Wikipedia sezon maddeleri (Twente tam; Freiburg'da Konferans Ligi yok).
- `fi.haber`: `KaynakKaydi`, `GuvenliOkuyucu`; kayıtsız uefa.com'a istek atılmadı. `zaman`, `haber_kaniti`, `AramaOturumu` (güncel mod, dondurma).

**Eksik kalanlar:**
- Twente için hiçbir haber kaynağı yok.
- Freiburg'un Konferans Ligi maçları bilinmiyor.
- Basın toplantısı video olduğu için okunamadı.
- Ligler arası model yok.
- Korner, kart ve oyuncu verisi yok.
- Bültende 200+ market yok.

**Elle bağlanan adımlar:**
1. **Maç seçimi:** bülten → kaynak erişimi değerlendirmesi elle yapıldı.
2. **Twente eşleşmesi:** "belirsiz" sonucu elle "FC Twente '65" olarak kullanıldı; onayınız gerekiyor.
3. **İstatistik betiği:** Lig verisi birleştirme, Elo/form ve Wikipedia fikstür ayrıştırması scratchpad'de; depoya alınmadı.
4. **Arama:** Claude web araması, sorgular elle yazıldı.
5. **Yayın tarihi (modül eksiği):** `sayfa.gorunur_tarihler` yalnızca metnin ilk 3000 karakterine bakıyor. scfreiburg.com'da menü uzun olduğu için "25.11.2026" tarihi otomatik bulunamadı. Tarih elle doğrulandı ve kanıtta "elle" diye işaretlendi. Bu bir hatadır; düzeltilmesi önerilir.
6. **Kanıt cümleleri:** Elle ve kısa olarak yazıldı.
7. **Market ailesi sınıflandırması:** Geçici bir betikle yapıldı. İlk denemede "Alt/Üst" adları yanlışlıkla birleşik sayıldı, düzeltildi. 104 kodluk sözlük eşlemesi henüz yok.
8. **Durum kodlarının kötüye kullanımı:** Bazı durum kayıtlarında, kategori kapatmak için uygun kod olmadığından "aranıp bulunamadı" kodu kullanıldı. Bunlar fikstür (bilgi aslında istatistik dosyasında) ve karşı senaryo (bölüm 6'da) kayıtları. Ayrı bir "başka dosyada" durum kodu eklenmeli.
