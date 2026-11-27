# Sonraki aşama — teknik plan (taslak, 25.11.2026)

Henüz kod yazılmadı. Commit, kupon ve main dalına birleştirme yok. Ana araştırma kuralları aynen geçerli: MK-1, rakip gücüne göre performans, ortak rakipler, sürpriz senaryoları, özel pazar kuralları ("hesaplanamaz").

## 0. Düzeltme: host sayısı 48 değil, 40
- Önceki raporlarda pilot için açılan host sayısını yanlışlıkla 48 yazdım. Doğrusu **40**: 16 + 16 + 8. Ortamın izin listesinde bunlardan önce gelen 12 host da var.
- Uyum taraması 38 hostta yapıldı. Taranmayan 2 host aynı sitenin ikinci adıdır:
  - www.osasuna.es → osasuna.es tarandı, okuma www.osasuna.es üzerinden çalıştı.
  - sscnapoli.it → www.sscnapoli.it tarandı; koşullar sayfası sscnapoli.it'te.

## 1. 40 hostun sınıflandırması (toplam denetimi: 14 + 3 + 15 + 8 = 40)
| Sınıf | Sayı | Hostlar | Ölçüt |
|---|---|---|---|
| **Kullanılabilir** | 14 | www.brentfordfc.com, www.bayer04.de, www.scfreiburg.com, www.eintracht.de, en.eintracht.de, www.sv98.de, www.vfl-wolfsburg.de, www.fcbarcelona.com, www.realvalladolid.es, osasuna.es, www.osasuna.es, www.thestar.co.uk, www.sussexexpress.co.uk, www.corrieredellosport.it | Erişilebilir; koşullar özel ve ticari olmayan okumaya izin veriyor; kulüp kimliği iki işaretle doğrulandı (basında ana sayfa kimliği) |
| **Doğrulanmamış** | 3 | www.fcaugsburg.de, www.fcbarcelona.es, www.asroma.com | Erişilebilir ve koşullar uygun, ama alan adının resmîliği yalnızca tek işarete dayanıyor |
| **Engellenmiş** | 15 | www.bundesliga.com, www.tottenhamhotspur.com, www.realmadrid.com, www.cdleganes.com, www.sscnapoli.it, sscnapoli.it, www.fcstpauli.com, www.sslazio.it, www.hessenschau.de, www.kicker.de, www.tsg-hoffenheim.de, www.athletic-club.eus, www.noticiasdenavarra.com, www.deia.eus, www.sassuolocalcio.it | Koşullar otomatik erişimi yasaklıyor, `robots.txt` Claude/Anthropic'i engelliyor ya da sunucu reddediyor (403/406/bot doğrulaması) |
| **Koşulları belirsiz / içerik erişilemez** | 8 | www.manutd.com, www.brightonandhovealbion.com, www.juventus.com, www.acmonza.com, www.sufc.co.uk, www.nottinghamforest.co.uk, www.ussalernitana1919.it, sport.sky.it | Koşullar okunamadı ya da bulunamadı; sayfa yalnızca JavaScript ile oluşuyor; yanıt yok; hata sayfası |

## 2. Kaldırma önerisi (henüz uygulanmadı; onayınızı bekliyor)
Yalnızca kullanılamaz olduğu **kesinleşen** 15 host önerildi:

| Gerekçe | Hostlar |
|---|---|
| Kullanım koşulları bot, scraping ya da otomatik erişimi açıkça yasaklıyor | www.bundesliga.com ("automated programmes, applets, bots … may not be used to access, analyse or download"), www.tottenhamhotspur.com (4.6.3), www.realmadrid.com, www.cdleganes.com ("secuencias de comandos automatizados o screen scraping"), www.sscnapoli.it ve sscnapoli.it (5.3 "accedere … mediante strumenti automatici") |
| `robots.txt` ClaudeBot/anthropic-ai için `Disallow: /` | www.fcstpauli.com, www.sslazio.it, www.hessenschau.de, www.kicker.de (kicker ayrıca 403) |
| Sunucu dürüst User-Agent'ı reddediyor | www.tsg-hoffenheim.de (403), www.athletic-club.eus (403), www.noticiasdenavarra.com (406), www.deia.eus (406), www.sassuolocalcio.it (bot doğrulaması). Aşmak yasak, tekrar denenmeyecek |

"Koşulları belirsiz" sınıfındaki 8 host kaldırılmaz. Önce yeniden kontrol önerilir:
- Man United, Brighton, Juventus: koşulların okunabilir bir sürümü aranır (ör. PDF).
- Salernitana ve sport.sky.it: tek bir yeniden deneme yapılır.

## 3. Mevcut 17 kanıtın güveni ve olası yanlılık
- **Düzeyler:** 8 resmî (kulüp sitesi), 9 tek kaynak (yerel ya da ulusal basın veya rakip kulüp). **Çok kaynak: 0.** Hiçbir kanıta yüksek güven verilmez.
- **Saat doğrulanamayanlar:** 2 kanıt maç günü yayımlanmış ama saati doğrulanamadı (Barcelona önizlemesi, Osasuna kadrosu). Bunlar düşük güvenle tutuluyor.
- **Brentford/Mbeumo:** Sayfada yalnızca "darbe" yazıyor. Oynamayacağı doğrulanmadı.
- **Yanlılık kaynakları:**
  1. **Erişim asimetrisi.** Favorinin kendi sitesi sürprizlerin 3/8'inde, kontrollerin 4/8'inde kullanılabildi. Basın kapsamı lige göre çok farklı: Serie A'da yalnızca Corriere, Bundesliga'da yalnızca kulüp siteleri vardı. "Favori eksiği 4'e karşı 1" bulgusu bu dengesizlikten etkilenebilir.
  2. **Sonucu bilen araştırmacı.** Sorgu şablonları sabitti, ama hangi sayfanın açılacağına araştırmacı karar verdi.
  3. **Anahtar kelime çıkarımı.** Bazı eksik listeleri kaçırıldı; örneğin Juventus ve Napoli tabloları sayfanın düz metninde yoktu.
  4. **Küçük örneklem.** n = 8'e karşı 8; istatistik testi yapılamaz.
  5. **Hayatta kalan sayfalar.** Arşivde kalan ya da güncellenmiş sayfalar; güncelleme saati maç öncesinde olsa bile sürüm farkı olabilir.

## 4. Zaten çalışan parçalar
| Parça | Yer | Durum |
|---|---|---|
| Kanıt kaydı + MK-1 denetimleri (bahis alan adı ve oran alanı yasağı, tarih tutarlılığı) | `lib/fi/kanit.py` | Depoda, testli |
| OpenFootball okuyucu: tarih düzeltmeleri, skor tamamlama, tarih denetimi | `lib/fi/kaynaklar/openfootball.py` | Depoda, testli |
| Takım adı eşleştirme | `lib/fi/takim_adlari.py` | Depoda, testli |
| Nesine bülten çekici (lig ve takım listesi kaynağı) | `.claude/skills/football-bulletin-fetch` | Depoda, testli |
| Erişim ve uyum taraması: robots, AI ajan kuralları, bot engeli, koşul maddeleri | scratchpad `uyum_tarama.py` | Pilotta çalıştı; depoya alınmadı |
| Sayfa okuyucu: yayın zamanı (JSON-LD, meta, `<time>`, görünür tarih), kenar çubuğu kesme, sayfa SHA-256, host beyaz listesi | scratchpad `sayfa_oku.py` | Pilotta çalıştı; 1 hata (kenar çubuğu) bulunup düzeltildi |
| Kulüp alan adı iki işaret doğrulaması (Wikipedia + ana sayfa başlığı) | scratchpad | Pilotta çalıştı |
| Wikipedia tüm kulvar fikstürü (dinlenme, kupa veya Avrupa maçı, milli ara) | scratchpad `pilot_istatistik.py` | 27/28 madde çalıştı |
| Form (rakip gücüne göre), ortak rakipler, maç öncesi puan tablosu | scratchpad | Çalıştı |
| Seçimi dondurma (tohum ve SHA-256), eşit bütçe | `pilot_secimi.json` | Çalıştı |

## 5. Yeniden kullanılabilir haber katmanı — modüller (`lib/fi/haber/`, plan)
1. **`kaynak_kaydi`:** Host kaydı. Her host için tutulur:
   - lig ve kulüp, kaynak türü;
   - kimlik işaretleri ve sınıf (yukarıdaki 4 sınıf);
   - koşulların ve robots kurallarının okunma tarihi ve özeti;
   - yeniden kontrol tarihi.

   Veri `veri/haber_kaynaklari.json` dosyasında durur. İzin listesine ekleme ve çıkarma **her zaman kullanıcı onayıyla** yapılır.
2. **`kesif`:** Herhangi bir lig için kaynak keşfi (alt ligler dahil). Akış:
   Nesine bülteni lig ve takım adı → `TakimEslestirici` → Wikipedia kulüp maddesi → resmî site adayı → iki işaret kimlik doğrulaması → uyum taraması → sınıf.
   - Yerel basın adayları web aramasıyla bulunur ve aynı uyum taramasından geçer.
   - Wikipedia maddesi olmayan alt lig kulüplerinde kimlik ancak ikinci bir resmî kaynakla doğrulanır (lig ya da federasyon sitesindeki kulüp sayfası). Doğrulanamazsa kaynak "doğrulanmamış" kalır ve kullanılmaz.
3. **`okuyucu`:** `sayfa_oku`'nun genelleştirilmiş hali:
   - host başına hız sınırı; `Retry-After`'a uyulur;
   - zaman aşımı ve bağlantı hatası kaydı; tek yeniden deneme;
   - boyut sınırı; JavaScript çalıştırılmaz; içerik saklanmaz, yalnızca özet tutulur.
4. **`zaman`:** Yayın zamanı önceliği: JSON-LD → meta → `<time>` → görünür tarih. Ardından maç başlama saatiyle karşılaştırılır:
   - güncel maçlarda başlama saati Nesine bülteninden;
   - tarihsel maçlarda Wikipedia ya da football-data.org'dan.

   Aynı gün yayımlanmış ve saati olmayan içerik "saat doğrulanamadı" etiketi alır. Tarihi hiç bulunamayan içerik **kanıt olmaz**.
5. **`plan`:** Sabit kontrol listesi: kadro, sakatlık, ceza, teknik direktör, antrenman ve rotasyon, fikstür, motivasyon, taktik, karşı senaryo. Dile göre sorgu şablonları (İngilizce, Almanca, İspanyolca, İtalyanca, Türkçe ve diğerleri) ve **eşit bütçe** (sürpriz ve kontrol, ev ve deplasman için aynı).
6. **`kayit`:** `Kanit` genişletmesi. Eklenecek alanlar (`docs/HABER_KATMANI.md` §4):
   - `kesim_zamani`, `yayin_zamani_kaynagi`, `kaynak_turu`, `kategori`, `etki`, `teyit`, `sayfa_sha256`;
   - "çok kaynak" için iki farklı yayıncı zorunlu.
7. **İki ayrı mod:**
   - **Tarihsel:** Kesim = maç başlangıcı. Sonuç biliniyor; çıktı "kör değil" etiketi taşır ve `output/arastirma/tarihsel/` altına yazılır.
   - **Güncel:** Kesim = araştırma anı (maçtan önce). Model tahmini önce dondurulur, sonra haber araştırılır, haber kaydı da dondurulur. Nesine fiyatı ancak bundan sonra açılır. Çıktı `output/arastirma/guncel/` altına yazılır.
   - İki modun sonuçları ayrı değerlendirilir; tarihsel sonuçlar ileriye dönük sonuçlarla karıştırılmaz.
8. **Model etkisi kapısı:** Haber önce yalnızca nitel not olur. Bir haber türünün olasılığı değiştirebilmesi için sırayla şunlar gerekir:
   1. önceden kayıtlı hipotez;
   2. dokunulmamış dönem ya da lig üzerinde kronolojik backtest;
   3. ileriye dönük test;
   4. kullanıcı onayı.

   Bunlar olmadan raporda "haber etkisi: hesaplanamaz" yazar. Bilgi uydurulmaz: kaynak yoksa ya da doğrulanamıyorsa "veri yok" ya da "doğrulanamadı" yazılır.

**Önerilen testler:**
- Kesim sonrası yayın reddedilir.
- Tarihsiz sayfa kanıt olamaz.
- Kenar çubuğu içeriği alınmaz.
- Engelli ya da AI'yı engelleyen host okunmaz.
- Retry-After'a uyulur, zaman aşımı kaydedilir.
- Tarihsel ve güncel çıktılar karışmaz.
- Çok kaynak için iki farklı yayıncı gerekir.
- MK-1 (bahis alan adı yasağı) korunur.

## 6. Sonraki aşamalarda unutulmayacaklar
1. **İlk yarı / ikinci yarı gol istatistikleri** (öncelikli). OpenFootball'daki ilk yarı skorlarıyla gol ailesi modeline eklenir: İY/MS, devre Alt/Üst, "hangi yarı". Önce veri kapsamı denetlenir.
2. **Alt lig yeterlilik kartları:** Nesine bülten ligleri × kaynaklar. Kapsanan sezonlar, maç sayısı, ilk yarı oranı, korner/kart/oyuncu verisi, güncellik ve kaynak künyesi (lisans).
3. **104 Nesine pazar kodu** (`market_sozlugu_v3.json`): Her kod bir olay ailesine (gol, devre, korner, kart, oyuncu, zaman aralığı, birleşik) ve olay tanımına eşlenir. Eşlenmeyen kod "tanımsız" sayılır. Doğrulanmış aile modeli ve aileler arası bağımlılık modeli yoksa sonuç "hesaplanamaz" olur.
4. **Fikstür işaretleri:** Milli ara ve kupa/Avrupa maçı yakınlığı, dört ligin bütün favori maçlarında ölçülür. Ön kayıttaki F3/F4'ün tüm kulvarlara genişletilmiş hali.

## 7. Önerilen sıra
1. Host kaydı ve kaldırma kararı (sizin onayınızla).
2. Pilotta çalışan araçların (`uyum`, `okuyucu`, `zaman`, alan adı doğrulama) testleriyle depoya alınması.
3. Fikstür işaretlerinin 4 ligde ölçülmesi.
4. İlk yarı / ikinci yarı analizi.
5. Alt lig kaynak keşfi ve yeterlilik kartları.
6. Pazar kodu eşlemesi.
7. Güncel moddaki ilk ileriye dönük haber kayıtları.
