---
name: mac-analizi
description: Tek bir futbol maçını Nesine bülteninden eşleştirip derinlemesine araştırır ve sohbette raporlar. Kullanım: son 5–10 maç, rakip gücü, sakatlık/ceza, ilk 11, taktik, motivasyon, yerel basın, muhabirler, teknik direktör, Reddit/taraftar, diğer tahmin sitelerinin gerekçeleri, Footy-Skills uzman notları ve 7 savunuculu konsey, bağımsız modelle dondurma, ardından Nesine fiyat karşılaştırması ve özel marketler. Kullanıcı "şu maçı araştır", "bu maçı derinlemesine incele", "X–Y maçını analiz et", "bu maçın bütün marketlerine bak" dediğinde kullan.
---

# Maç analizi (Football Intelligence + Footy-Skills protokolü)

**Asıl soru (her analizde):** "Bu bahis sonucunun gerçekleşmesini destekleyen somut kanıtlar nelerdir, karşıt kanıtlar nelerdir ve bu ihtimal neden araştırmaya değerdir?" Amaç yüksek oranı haklı çıkarmak değil; iki yönü de araştırıp en güçlü gerekçeli seçenekleri bulmaktır. Nesine oranları şirket marjı içerir ve gerçek olasılık değildir. Oranlar yalnızca marketleri keşfetmek, piyasa görüşünü anlamak ve (geçerli model varsa) fiyat karşılaştırmak için kullanılır. EV ya da fiyat avantajı ZORUNLU değildir: yalnızca kalibre bir bağımsız olasılık varsa ve belirsizliğiyle birlikte gösterilir.

Komutlar proje kökünden çalıştırılır: `PYTHONPATH=lib python3 -m uygulama.sohbet …`. Çıktıyı sohbete özetle; dosya gönderme zorunlu değil.

## Değişmez kurallar (CLAUDE.md ile aynı)
- **MK-1:**
  - Nesine oranları ve diğer sitelerin yüzdeleri bağımsız olasılığa GİRMEZ.
  - Olasılık yalnızca `dondur` komutundaki önceden kayıtlı modelden gelir.
  - Oranlar ancak dondurmadan SONRA `karsilastir` ile açılır.
- Kalibre olmayan markette yüzde, EV ya da "avantaj" yoktur: **hesaplanamaz**.
- Haber, yorum ve savunucu görüşleri olasılığı DEĞİŞTİRMEZ (kanıtlanmış haber modeli yok).
- Her bilgi için kaynak, yayın zamanı ve doğrulama seviyesi verilir. Bulunamayan bilgi "veri yok" olarak yazılır.
- Araştırılmamış bir şey araştırılmış gibi sunulmaz. Araştırma kapsamı (arama sayısı, kaynak türleri, bulunamayanlar) raporda yer alır.
- Bot korumasını aşma. Ücretli API kullanma. Alt ajan runner'ı başlatma (`claude -p`, opencode, codex).
- Kullanıcı istemeden kupon kurma.
- **Oran tarafsızlığı:**
  - Oran eleme ölçütü değildir.
  - Yüksek oran otomatik riskli, düşük oran otomatik güvenli sayılmaz.
  - Favori ve sürpriz seçenekleri aynı titizlikle incelenir.
  - Olasılık (model) ile fiyat cazibesi ayrı değerlendirilir.

## Adımlar
0. **Hafıza:** `sohbet hafiza` ve aynı takımlar için `output/arastirma/genis_pilot/` altındaki önceki araştırmalar. Eski bulgular tarihleriyle "geçmiş" olarak ayrılır.
1. **Maçı eşleştir:** `mac KOD` ya da `mac "takım adı"`. Bültende yoksa önce `bulten --gun YYYY-AA-GG` çalıştır (football-bulletin-fetch).
   - Maç başladıysa maç öncesi analiz yapılmaz. Canlı skor, dakika ve kırmızı kart web aramasıyla doğrulanır.
2. **Bağımsız model durumu:** `mac` çıktısında hazırlanabilir / takım onayı gerekli / hesaplanamaz bilgisi var.
   - "Hazırlanabilir" ise, araştırmadan ÖNCE `dondur KOD` çalıştır. Olasılık haberden etkilenmez; erken dondurmak MK-1 sırasını korur.
   - "Takım onayı gerekli" ise kullanıcıya hangi adın onay beklediğini söyle. Benzer ada göre kendin eşleme.
3. **Haber araştırması:** `haber-arastir` becerisinin protokolü (WebSearch; T−24s / T−6s / T−90dk turu).
   - Kapsam: kulüp ve federasyon, yerel ve ulusal basın, muhabir, teknik direktör basın toplantısı, beklenen ve kesin ilk 11, Reddit ve taraftar, tahmin sitelerinin gerekçeleri.
   - Bulunanları `haber-kaydet` ile kaydet.
4. **Uzman notları:** `protokol/uzmanlar.md`. 5 not: kadro haberleri, taktik, alttaki istatistikler, bağlam ve motivasyon, medya.
5. **Konsey:** `protokol/konsey.md`. 7 savunucu: ev, deplasman, beraberlik, gol, zayıf taraf, oyun akışı, kaos. Her biri bağımsız, iki geçişli.
6. **Sürpriz bağlamı:** `surpriz KOD`. Bağımsız favori (yalnızca modelden), tarihsel taban oranları, pilot bulguları. Bu bulgular kanıtlanmış tahmin gücü değildir.
7. **Fiyat ve özel marketler** (isteğe bağlı ek bilgi; yalnızca dondurmadan sonra):
   - `karsilastir KOD`: dondurmadan sonra çekilmiş bülten yoksa çeker.
   - `marketler KOD`: bütün marketler, oranlarıyla.
   - Kapsamdaki marketlerde p, başabaş ve EV verilir. Diğer marketlerde yalnızca nitel gerekçe, "hesaplanamaz".
   - Pozitif EV avantaj değildir: "model–piyasa ayrışması · doğrulama gerekli".
8. **Rapor:** `protokol/rapor.md` B biçimi, sohbette. Sonunda en önemli sürpriz sinyali, belirsizlikler ve araştırma kapsamı yer alır.

## Model kapsamı (özet; güncel liste `mac` çıktısında)
- **E3:** en.1, de.1, it.1, es.1, en.3, en.4, fr.2, it.2. 38 market; MS 1/2, ÇŞ, 2,5 Alt/Üst dahil (ON_KAYIT_E3, 15.994 maçlık tek sınama).
- **E2:** en.2, at.1, be.1, sco.1, tr.1, gr.1. 26 market; MS 1/2 ve 2,5 Alt/Üst hariç.
- **Poisson E:** fr.1, nl.1, pt.1, de.2, es.2. 10 market.
- **Lig onayı:** Kullanımda yalnızca `veri/lig_eslemeleri.json`'daki onaylı ligler geçerli. 27.11 itibarıyla 7 lig onaylı: Championship → en.2, Premier Lig → en.1, Bundesliga → de.1, Serie A → it.1, La Liga → es.1, Ligue 1 → fr.1, Eredivisie → nl.1. Kanıt: `veri/lig_esleme_kanitlari_20261127.json`. Portekiz onaysız.
- **Model yoksa** araştırma DURMAZ: haber, istatistik, taktik ve yerel basınla nitel analiz yapılır; yüzde verilmez.
- **Kapsam dışı:** Diğer ligler, Avrupa kupaları, millî maçlar, korner, kart, oyuncu ve devre marketleri. Bunlar **hesaplanamaz**.
