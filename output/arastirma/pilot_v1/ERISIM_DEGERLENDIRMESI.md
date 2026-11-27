# Haber katmanı pilotu — 1. adım: kaynak erişimi ve kanıt kalitesi (24.11.2026)

> Sonuçları bilinen maçlar → **bağımsız kör test değildir.** Bu adımda haberden olasılık üretilmedi; modele hiçbir şey eklenmedi.

## Seçim (araştırmadan önce donduruldu)
- **Kayıt:** `pilot_secimi.json`, SHA-256 `d791de85…`.
- **Kural:**
  - Kaynak: 60 maçlık set (`set_v1`, SHA-256 `954a7487…`).
  - Her lig için A grubundan (favori kaybetti) ve B grubundan (berabere) birer sürpriz seçildi; her birine eşleştirilmiş kontrolü eklendi.
  - Rastgelelik tohumu set dosyasının SHA-256'sından türetildi, yani seçimi yapan kişiden bağımsız.
- **Maçlar:** 16; her ligden 2 sürpriz + 2 kontrol. Favorilerin 15'i ev sahibi, 1'i deplasmanda: en.1-A çiftinde (sürpriz ve kontrol) favori deplasmanda, diğer 14 maçta ev sahibi.

## Eşit derinlikte arama (adım 1)
- **Yöntem:** Maç başına 1 arama, 16 maçın hepsinde aynı şablon. Sorgu yerel dilde: favori + rakip + basın toplantısı veya eksikler + ay ve yıl. Kayıt: `arama_gunlugu.json`.
- **Sayfa okuma:** Hiç yapılmadı. Haber sitelerinin hiçbiri ortamın izin listesinde değil.
- **Sonuç:** **Doğrulanmış haber kanıtı = 0.** Arama özetleri kural gereği kanıt sayılmadı.

| Ölçüt | Sürpriz (8) | Kontrol (8) |
|---|---|---|
| Maça ait, tarihli resmî kulüp sayfası bulundu (aday) | 4 | 5 |
| Eksik/sakatlık bilgisi içeren aday bulundu | 6 | 4 |
| Bu maça ait aday hiç bulunamadı | 2 (de.1-A-S, it.1-A-S) | 2 (de.1-B-K, it.1-A-K) |
| Özet başka bir sezonun maçıyla karıştı | 6 | 6 |
| Özet maç sonucunu ya da maç sonrası bilgiyi içerdi | 3 | 3 |

**Kanıt kalitesi bulguları:**
- **Özetler güvenilmez.**
  - Juventus–Salernitana (Mayıs 2024) özetindeki eksik listesinde Bonucci ve Paredes vardı; ikisi o tarihte kulüpte değildi. Bu liste büyük olasılıkla eski bir maçtan karıştı.
  - Lazio–Salernitana özeti maçın oynandığı stat konusunda kendisiyle çelişti.
  - Özetlerin 12'si başka sezonların maçlarını karıştırdı.
- **İngilizce aramalar en verimli dil oldu:** Kulüplerin resmî takım haberi ve basın toplantısı dökümü sayfaları doğrudan çıktı.
- **Almanca ve İtalyanca aramalarda tarih sorunu büyük:** Ligainsider, fantacalcio gibi derleme siteleri öne çıkıyor; tarihleri sonuçlarda çoğu zaman görünmüyor.
- **İspanyolca'da yerel basın güçlü:** Noticias de Navarra ve Deia, URL'de tarih taşıyan maç öncesi haberler veriyor.
- **Ön yorum (sayfalar okunmadan kanıt değil):** Sürprizlerde aday eksik bilgisi biraz daha sık (6'ya karşı 4). Bu fark ancak sayfalar okunup yayın zamanı doğrulandıktan sonra değerlendirilebilir.

## Şimdiki izinlerle yapılabilenler
| Alan | Durum |
|---|---|
| 1. Son 5–10 resmî maç, rakip gücü | Lig maçları için **var** (OpenFootball + Elo). Kupa ve Avrupa maçları Wikipedia sezon maddelerinden alınabilir. |
| 5–6. Fikstür yoğunluğu, dinlenme (bütün kulvarlar) | `en.wikipedia.org` izinli. 28 kulüp sezonu maddesinin 27'si var, yalnızca 2025-26 Hoffenheim maddesi yok. |
| 7. Motivasyon, puan ihtiyacı | Maç öncesi puan tablosu kendi verimizden **hesaplanabilir** (`hesaplandi`). |
| 9. Aynı rakiplere karşı performans | **Var** (bu sezon, maç öncesi). |
| 2, 3, 4, 8, 10 (kadro, sakatlık, ceza, açıklamalar, antrenman, taktik, karşı senaryo) | **Sayfa okuma izni gerekiyor.** |

## Gereken yeni host izinleri (onayınız olmadan açılmayacak)
Her host için önce `robots.txt` ve kullanım koşulları okunur. premierleague.com'da olduğu gibi koşullar veritabanı kurmayı veya yeniden kullanımı yasaklıyorsa o kaynaktan içerik saklanmaz, gerekirse kaynak hiç kullanılmaz.

**Öncelik 1 — resmî kulüp siteleri.** Yalnızca "aramada görüldü" olanlar; "doğrulanacak" olanlar ilk erişimde denetlenir.

| Lig | Aramada görüldü | Pilot için gerekli, alan adı doğrulanacak |
|---|---|---|
| PL | www.brentfordfc.com, www.tottenhamhotspur.com, www.brightonandhovealbion.com, www.manutd.com | Sheffield United, Nottingham Forest resmî siteleri |
| BL | www.tsg-hoffenheim.de, en.eintracht.de, www.scfreiburg.com, www.sv98.de, www.bayer04.de, fcsp-admin.fcstpauli.com (yönetim alt alanı; asıl site doğrulanacak) | FC Augsburg, VfL Wolfsburg |
| LL | www.fcbarcelona.es / www.fcbarcelona.com, www.realmadrid.com, osasuna.es | CD Leganés, Real Valladolid, Athletic Club |
| SA | www.juventus.com, www.asroma.com | SS Lazio, Salernitana, AC Monza, SSC Napoli, Sassuolo |

**Öncelik 2 — lig sitesi.** www.bundesliga.com (resmî kadro ve ilk 11 sayfaları aramada görüldü). LaLiga ve Serie A'nın resmî siteleri ayrıca değerlendirilir.

**Öncelik 3 — saygın yerel basın** (lig başına 2; yayın zamanı ve sürüm denetimi için):
- PL: www.thestar.co.uk / www.sheffieldtelegraph.co.uk, www.sussexexpress.co.uk
- BL: www.hessenschau.de, www.kicker.de
- LL: www.noticiasdenavarra.com, www.deia.eus
- SA: sport.sky.it, www.corrieredellosport.it

**Önerilmeyenler:**
- Derleme, fantezi ve bahis içerikli siteler kanıt kaynağı olarak önerilmiyor: sportsmole, ligainsider, fantacalcio, comuniate, futbolfantasy, goal.com. Goal sayfalarında bahis reklamı var; MK-1 gereği kaçınılır.
- Yahoo yeniden yayın sayfaları önerilmiyor; özgün yayıncı tercih edilir.

**Sosyal medya (X, Reddit):** Giriş duvarı nedeniyle doğrudan okunmaz. Yalnızca resmî kulüp sayfalarına gömülü içerik kullanılabilir.

## Önerilen sonraki adım
1. Siz hostları onaylayınca:
   - her host için kullanım koşullarını kaydederim;
   - 16 maçın hepsinde aynı kontrol listesi ve aynı bütçeyle sayfaları okurum (maç başına en fazla 8 arama ve 10 sayfa);
   - yayın zamanını sayfadan doğrularım;
   - kanıtları `Kanit` biçiminde JSONL'ye yazıp dondururum.
2. Kopyalanabilecek alanları (1, 5, 6, 7, 9) izin beklemeden kendi verimiz ve Wikipedia ile tamamlayabilirim.
3. Ayırt edicilik analizi: Kategori başına "sürprizde bulundu / kontrolde bulundu" oranları. n=8'e karşı 8 olduğu için yalnızca hipotez üretilir; yeni olasılık üretilmez.
