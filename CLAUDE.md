# Football Intelligence

Kişisel futbol araştırma ve bağımsız olasılık analizi sistemi. Yalnızca futbol.

## Çalışma biçimi

**Asıl soru (her analizde):** "Bu bahis sonucunun gerçekleşmesini destekleyen somut kanıtlar nelerdir, karşıt kanıtlar nelerdir ve bu ihtimal neden araştırmaya değerdir?" Amaç yüksek oranı haklı çıkarmak değil; iki yönü de araştırıp en güçlü gerekçeli seçenekleri bulmaktır. Nesine oranları şirket marjı içerir ve gerçek olasılık değildir. Oranlar yalnızca marketleri keşfetmek, piyasa görüşünü anlamak ve (geçerli model varsa) fiyat karşılaştırmak için kullanılır. EV ya da fiyat avantajı ZORUNLU değildir: yalnızca kalibre bir bağımsız olasılık varsa ve belirsizliğiyle birlikte gösterilir.

Football Intelligence ayrı bir uygulama değildir. Kullanıcı Claude Code'da Türkçe konuşur. Claude şunları birleştirerek sonucu doğrudan sohbette sunar:
- proje Skill'leri (`.claude/skills/`);
- Python komutları (`PYTHONPATH=lib python3 -m uygulama.sohbet …`);
- kendi web araştırması (WebSearch; izinli hostlarda sayfa okuma).

Nesine bülteni ana maç havuzudur. Web arayüzü (`uygulama/sunucu.py`) ve Render hazırlığı korunur ama kullanılmaz.

| Kullanıcı der ki | Yapılacak |
|---|---|
| "Bülteni çek", "Bugünün bültenini yenile", "Nesine maçlarını getir", "… tarihli bülteni çek" | `football-bulletin-fetch`: `sohbet bulten [--gun]` → sayılar + maç listesi sohbette |
| "Bütün maçları tara", "yüksek oranlı gerekçeli ihtimalleri bul", "favorilerin zorlanabileceği maçlar", "yüksek fiyatlı özel marketler" | `bulten-tara`: `sohbet tara` → önceliklendirme → kısa web eleme → aday raporu |
| "Şu maçı araştır / derinlemesine incele", "X–Y analiz" | `mac-analizi`: `mac` → `dondur` (model varsa) → haber → uzman notları → konsey → `karsilastir` → `marketler` |
| "Haberleri araştır", "diğer siteler/analistler ne diyor", "sakatlık durumu" | `haber-arastir` (+ `sohbet haber-kaydet`) |
| "En ilginç sürpriz sinyali", "favori zorlanır mı" | `surpriz-analizi` (`sohbet surpriz`) |
| "Bu maçın marketlerini incele", "200'den fazla marketi incele", "eşdeğer marketlerde en yüksek fiyat" | `market-incele` (`sohbet karsilastir`, `sohbet marketler`) |
| "Tahmin performansı", "arşiv" | `tahmin-performansi` (`sohbet performans`) |
| "Araştırma hafızası", "önceki araştırmalar" | `sohbet hafiza [--guncelle]` (çıkarım, sonuç, manifest; silme yok) |
| "Eski bültenleri temizle" | `sohbet temizle` (yalnızca plan); `--uygula` YALNIZCA kullanıcı açıkça isterse |
| "Hafızayı kaydet / geri getir" | `sohbet hafiza-dali hazirla` (yerel özel dal; push kullanıcı onayıyla) / `hafiza-dali geri` |
| "Arayüzü aç" (yalnızca açıkça istenirse) | `PYTHONPATH=lib python3 -m uygulama` (yerel, `docs/V1_ARAYUZ.md`) |

Oran tarafsızlığı:
- Oran bir eleme ölçütü değildir.
- Yüksek oran otomatik riskli, düşük oran otomatik güvenli sayılmaz.
- Favori ve sürpriz seçenekleri aynı titizlikle incelenir.
- Olayın olasılığı (yalnızca bağımsız model) ile fiyatın cazibesi ayrı değerlendirilir.
- Gerekçesi güçlü ama olasılığı hesaplanamayan seçenekler "hesaplanamaz" etiketiyle araştırma adayı olarak kalır.

## Araştırma görevi düzeni (kullanıcı kuralı, 27.11; varsayılan)
Kullanıcı bir araştırma görevi verdiğinde süreç baştan sona Claude tarafından yönetilir:
- **Sorulmayanlar:** bülten özeti, aday listesi, seçim sorusu ya da ara onay yok.
- **Onay istenen tek durum:** zorunlu erişim izni, ücretli işlem ya da önemli sistem değişikliği.

**Akış:**
1. Nesine bültenini çek (`sohbet bulten`) ve bütün maçları Python ile içeride ön tara: market derinliği, bağımsız model/veri kapsamı, özel marketler.
2. **Türkiye ligleri varsayılan olarak hariç tutulur** (kullanıcı kuralı, 27.11 son). Kullanıcı bir görevde isterse ayrı bölümde incelenir. Çekilen maç sayısı ile taranan sayı farklıysa nedeni tek satırda yazılır (Türkiye hariç, başlamış maç, özel/haftalık kayıt vb.).
3. Türkiye dışından en dikkat çekici **10 maça kadar** seç ve derinlemesine araştır:
   - haber, sakatlık ve ceza;
   - güncel durum ve taktik;
   - ülke dilinde yerel basın;
   - analistler ve tahmin siteleri;
   - diğer bahis sitelerinin oranları (yalnızca piyasa görüşü);
   - istatistik;
   - model varsa: önce dondur, sonra karşılaştır.
4. Hem sürprizler hem beklenen ama yüksek fiyatlı özel marketler değerlendirilir. Oran tarafsızlığı geçerlidir.
5. Güçlü gerekçesi olmayan aday elenir. Sayıyı doldurmak için zayıf aday eklenmez; daha az aday varsa bu açıkça söylenir.
6. **Çıktı yalnızca nihai sonuç:** market, seçenek, oran (çekim saatiyle), lehte ve aleyhte kanıt, kaynaklar, belirsizlikler, varsa bağımsız olasılık. Çalışmayan veri kaynakları tek satırda belirtilir. Kupon yok.
7. **Verimlilik:** büyük veri Python'da işlenir, sohbete yalnızca özet gelir. Yeni kod ya da test yalnızca kullanıcı isterse.

**Yeni oturum başında (bir kez, kısa):** hafızanın SessionStart ile geri yüklendiğini doğrula (`sohbet hafiza`); daha önce açılamayan 2–3 resmî kulüp/istatistik sayfasıyla `web-fetch` erişimini dene. Çalışıyorsa kaynakları tam sayfadan oku; çalışmıyorsa arama ve alternatif güvenilir kaynaklarla devam et. Yeni kaynak ekleme çalışması yapılmaz (47 host yeterli).

**Araştırma yöntemi (varsayılan, 27.11):**
- Keşif yapan araştırmacı gibi çalış: hipotez kur, kanıt ara, karşıt kanıtı özellikle ara; daha güçlü market ya da maç çıkarsa yön değiştir. Yalnızca model kapsamındaki maçlarla sınırlanma.
- Güncel içerik için WebSearch `mode: "extended"` + resmî/yerel `allowed_domains` + ülke dili. Engelli bir alan bütün sorguyu 400 ile düşürür; onu çıkarıp yeniden dene.
- **Bulma ve okuma ayrıdır:** WebSearch sayfayı bulur ve özetler; tam sayfa `web-fetch` ajanıyla okunur. Her bilgi **[tam sayfa]** ya da **[özet]** etiketiyle verilir; yalnızca özetten gelen bilgi kesin doğrulanmış sayılmaz ve belirsizlik kesinleştirilmez.
- Tam sayfa açılamazsa aynı bilgi başka resmî ya da güvenilir kaynakta aranır (lig sitesi, ulusal yayıncı, ikinci kaynak).
- **Hata türleri ayrılır:** `ENOTFOUND` / proxy reddi = ortamın ağ izni (host izin listesinde yok; izin kullanıcı onayıyla eklenir). WebSearch 400 "not accessible to our user agent" ya da 403 = sitenin bot engeli (aşılmaz, izin listesine de eklenmez).
- **Ağ izinleri:** temel lig, haber, istatistik ve analiz hostları ortamın izin listesinde kalıcıdır. Araştırma başında, incelenecek maçların listede olmayan resmî kulüp hostları tek toplu istekle eklenir (çağrı başına ≤20 host; joker karakter yok). Her maç için ayrı izin istenmez. Yeni eklenen hostları `web-fetch` aracı ancak yeni oturumda görür. 429 = sitenin hız sınırı ya da bot koruması; yeniden denenmez.
- Diğer bahis şirketlerinin oranları ve analist görüşleri: yalnızca erişilebilir kaynaktan, site adı ve tarihiyle; doğrulanamayan oran ya da görüş yazılmaz.
- İstatistik–market uyumu: bir istatistik, marketin gerçekleşme koşulunu doğrudan ölçüyor mu? (ör. yüksek toplam gol ≠ iki yarıda KG; normal KG ≠ iki yarıda KG; ortalama ≠ yarıya özgü dağılım.)
- Kadro haberi bulunamazsa kulübün dilinde yeniden ara ve resmî kulüp sitesini (duyurular, basın toplantısı) mutlaka kontrol et; teknik direktör değişikliğini de doğrula.
- **Olay tarihi ≠ yayın tarihi:** bir maçın ana bulgusu olarak sunulan haberde olayın tarihi (ör. hoca atanması) ile haberin yayın tarihi ayrı yazılır; olay tarihi birincil kaynaktan (resmî duyuru) doğrulanır. Model etkisi hakkında, model girdisini (veri kesimi, pencere) kontrol etmeden varsayım yapılmaz.
- İstatistiği markete olay sayısıyla bağla: ortalama yerine "kaç maçta gerçekleşti" (ör. 2. yarıda daha çok gol attığı maç sayısı / toplam maç).
- İlginç bir bulguda alternatif açıklamaları da ara (rakip kalitesi, şans/xG sapması, hoca değişikliği, kadro değişimi, küçük örneklem).
- Başka sitelerin olasılıkları yalnızca karşılaştırmalı kaynak görüşüdür; bağımsız modelimiz gibi sunulmaz.
- Rapor kalite ölçütleri: kaynak türü sayısı; ilk bakışta görünmeyen bulgular; karşıt kanıtla değişen hipotezler; keşfedilen yeni maç/market; nihai gerekçeler; doğrulanamayanlar.

## Değişiklik raporlama (ChatGPT ile ortak değerlendirme, 27.11)
Temel sürüm: ChatGPT'ye verilen aktarım ZIP'i (27.11; kod `f40ec55` ile aynı). Her kod/Skill/CLAUDE.md güncellemesinde kısaca bildir: değişen dosyalar ve yolları, önceki → yeni commit kimliği, gerekçe, yeni araştırma hafızası kayıtları. Kullanıcı isterse yalnızca değişen dosyalardan küçük ZIP hazırla. Kod değişmediyse paket hazırlama; günlük rapor ve kaynaklar yeterli.

## Değişmez kurallar
1. Bot korumasını ya da erişim engelini aşma; tarayıcı taklidi, Playwright/Selenium, çerez kullanma. Engel varsa dur ve raporla.
2. Otomatik alt ajan runner'ı başlatma (`opencode`, `codex`, `claude -p`). Footy-Skills protokolü (uzmanlar, konsey, karar verici) aynı oturumda Claude tarafından adım adım uygulanır (`.claude/skills/mac-analizi/`).
3. Ücretli API kullanma; paket yükleme (mevcut kütüphaneler: requests, pandas, numpy, openpyxl, xlsxwriter).
4. **MK-1 Oran bağımsızlığı (değişmez modelleme kuralı; ayrıntı `docs/MODEL_KURALLARI.md`).**
   - Nesine oranları; favori belirleme, takım gücü değerlendirme, maç sonucu tahmini ve olasılık hesaplamada
     KESİNLİKLE kullanılmaz. Favori ve sürpriz adayları yalnızca bağımsız futbol verileriyle belirlenir.
   - Oranlardan ima edilen olasılıklarla bağımsız tahmin düzeltilmez, ağırlıklandırılmaz, kalibre edilmez.
   - Sıra: (1) geçmiş performans, rakip kalitesi, güncel haberler, kadro, taktik ve doğrulanmış istatistiklerden tahmin;
     (2) tahmini zaman damgası + SHA-256 ile dondur; (3) ANCAK SONRA Nesine oranlarını aç ve fiyat karşılaştırması yap.
   - Aynı olayın farklı Nesine pazarlarındaki fiyatları matematiksel olarak karşılaştırılabilir; ama bu fiyat oranları
     gerçek ya da bağımsız (koşullu) olasılık olarak SUNULMAZ.
   - Yeterli veri ya da doğrulanmış model olmayan (özel) pazarlarda olasılık uydurulmaz: "hesaplanamaz" denir.
5. Her veri için kaynak, veri tarihi ve doğrulama zamanı göster; veri yoksa sayı uydurma, "veri yok" de.
6. Kullanıcı açıkça istemeden kupon hazırlama ve bütün maçları ayrıntılı analiz etmeye başlama. Kupon istense bile
   `dogrulanmamis_eslesme` / `isim_celiskisi` işaretli maçları ve `oynanabilirlik` değeri `oynanabilir` olmayan
   oranları (ör. `durumu_dogrulanmamis`, market durumu MS≠1 ya da eksik) kupona alma; nedenini kullanıcıya söyle.
7. Hiçbir pazara doğrulanmamış "yüksek güven" verme.

## Çıktılar ve araştırma hafızası
`output/` git dışıdır.
- **Kalıcı araştırma hafızası:** `output/hafiza/`, `output/tahminler/`, `output/arastirma/`, `output/raporlar/`.
- **Bültenler geçicidir.** Son 3 gün tutulur; daha eski tam bültenler ancak hafızaya çıkarım ve SHA-256 doğrulamasından sonra, kullanıcı isterse silinir.
- **Oturumlar arası:** aynı özel depoda kod içermeyen `arastirma-hafizasi` dalı. Push kullanıcı onayıyla yapılır.
- **Hafıza dalına girmeyenler:** ham bülten, Excel, önbellek ve kaydedilmiş ham web sayfaları (gömülü üçüncü taraf anahtarları içerebilir).
