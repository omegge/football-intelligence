# Pilot kulüplerinin resmî alan adı doğrulaması (25.11.2026)

**Yöntem:** İki bağımsız işaret aranır.
- (W) English Wikipedia kulüp maddesinde bilgi kutusunun `website` alanı ya da `{{Official website}}` şablonu.
- (S) Sitenin kendi ana sayfası. Sayfa başlığı kulübü resmî site olarak adlandırmalı. Kontrol dürüst bir User-Agent'la yapıldı, istekler yavaş gönderildi, bağlantı ve zaman aşımı hataları kaydedildi.
- Wikipedia adresi tek başına güvenilir kabul edilmedi.
- `{{Official URL}}` adresi Wikidata'dan çekiyor. Wikidata izin listesinde olmadığı için bu adres çözülemedi; o kulüpler için (W) "yok" sayıldı.

**Durum sınıfları:** "doğrulandı" = W ve S tutarlı. "tek işaret" = yalnızca W ya da yalnızca S var. "doğrulanamadı" = ikisi de yok ya da biri çelişiyor.

| Kulüp | Alan adı | W (Wikipedia) | S (ana sayfa başlığı) | Alan adı durumu | Kullanım / erişim |
|---|---|---|---|---|---|
| Sheffield United | www.sufc.co.uk | sufc.co.uk | başlık yok (yalnızca JavaScript) | tek işaret (W) | İçerik okunamıyor → kullanılmadı |
| Brentford | www.brentfordfc.com | brentfordfc.com | "Brentford FC \| Official Website" | **doğrulandı** | Kullanıldı |
| Tottenham Hotspur | www.tottenhamhotspur.com | tottenhamhotspur.com | "Home \| Tottenham Hotspur" | doğrulandı | Koşullar bot ve scraping'i yasaklıyor → kullanılmadı |
| Brighton & Hove Albion | www.brightonandhovealbion.com | yalnızca ad, adres yok | "Brighton & Hove Albion" | tek işaret (S) | Koşullar okunamadı → kullanılmadı |
| Nottingham Forest | www.nottinghamforest.co.uk | Wikidata (çözülmedi) | başlık yok (JavaScript) | **doğrulanamadı** | Kullanılmadı |
| Manchester United | www.manutd.com | manutd.com | "Official Manchester United Website" | doğrulandı | Koşullar sayfası 403 → kullanılmadı |
| TSG Hoffenheim | www.tsg-hoffenheim.de | tsg-hoffenheim.de | 403 | tek işaret (W) | Erişim engeli → kullanılmadı |
| FC St. Pauli | www.fcstpauli.com | fcstpauli.com | "FC St. Pauli \| Home" | doğrulandı | `robots.txt` Claude/Anthropic'i engelliyor → kullanılmadı |
| Eintracht Frankfurt | en.eintracht.de / www.eintracht.de | en.eintracht.de | "Eintracht Frankfurt – Offizielle Website" | **doğrulandı** | Kullanıldı |
| FC Augsburg | www.fcaugsburg.de | Wikidata (çözülmedi) | "Die offizielle Website des FC Augsburg" | tek işaret (S) | Okunabilir; pilotta ilgili haber bulunamadı |
| SC Freiburg | www.scfreiburg.com | scfreiburg.com | "SC Freiburg \| Die offizielle Website" | **doğrulandı** | Kullanıldı |
| SV Darmstadt 98 | www.sv98.de | sv98.de | "SV Darmstadt 1898 e.V." | **doğrulandı** | Kullanıldı |
| Bayer 04 Leverkusen | www.bayer04.de | bayer04.de | "Bayer 04 Leverkusen Fußball GmbH" | **doğrulandı** | Kullanıldı |
| VfL Wolfsburg | www.vfl-wolfsburg.de | vfl-wolfsburg.de | "… \| VfL Wolfsburg" | **doğrulandı** | Okunabilir; pilotta kullanılmadı |
| FC Barcelona | www.fcbarcelona.com (.es) | fcbarcelona.com | "Official FC Barcelona Website" / "Web Oficial del FC Barcelona" | **doğrulandı** (.com); .es tek işaret (S) | Kullanıldı (.com) |
| CD Leganés | www.cdleganes.com | cdleganes.com | "C.D. Leganés \| Web Oficial" | doğrulandı | Koşullar otomatik betik ve scraping'i yasaklıyor → kullanılmadı |
| Real Madrid | www.realmadrid.com | realmadrid.com | "Real Madrid CF \| Web Oficial" | doğrulandı | Koşullar otomatik betik ve scraping'i yasaklıyor → kullanılmadı |
| Real Valladolid | www.realvalladolid.es | realvalladolid.es | "Real Valladolid CF \| Web Oficial" | **doğrulandı** | Okundu; sayfalarda yayın tarihi yok → kanıt üretilemedi |
| Athletic Club | www.athletic-club.eus | athletic-club.eus | 403 | tek işaret (W) | Erişim engeli → kullanılmadı |
| CA Osasuna | www.osasuna.es (osasuna.es) | osasuna.es | "Web Oficial - Osasuna" | **doğrulandı** | Kullanıldı |
| SS Lazio | www.sslazio.it | Wikidata (çözülmedi) | "Home \| S.S. Lazio" | tek işaret (S) | `robots.txt` Claude/Anthropic'i engelliyor → kullanılmadı |
| US Salernitana 1919 | www.ussalernitana1919.it | ussalernitana1919.it | yanıt yok (bağlantı hatası) | tek işaret (W) | Erişilemedi |
| AS Roma | www.asroma.com | Wikidata; şablonda store.asroma.com | "AS Roma - the official website" | tek işaret (S) + aynı alan adının mağaza alt alanı | Okunabilir; pilotta haber Corriere'den alındı |
| AC Monza | www.acmonza.com | acmonza.com | "Associazione Calcio Monza S.p.A." | doğrulandı | Koşullar sayfası bulunamadı → kullanılmadı |
| Juventus | www.juventus.com | juventus.com | "Juventus Football Club - Sito Ufficiale" | doğrulandı | Koşullar JavaScript ile oluşuyor, okunamadı → kullanılmadı |
| SSC Napoli | www.sscnapoli.it | Wikidata (çözülmedi) | "SSC Napoli \| Sito ufficiale" | tek işaret (S) | Koşullar otomatik erişimi yasaklıyor → kullanılmadı |
| US Sassuolo | www.sassuolocalcio.it | Wikidata (çözülmedi) | "Home - U.S. Sassuolo Calcio" (bot doğrulaması işareti) | tek işaret (S) | Bot engeli → kullanılmadı |

**Özet (27 kulüp):**

| Alan adı durumu | Sayı |
|---|---|
| Doğrulandı (W + S) | 16 |
| Tek işaret | 10 |
| Doğrulanamadı (Nottingham Forest) | 1 |

Pilotta kanıt olarak kullanılan kulüp alan adları: Brentford, Eintracht, Freiburg, Darmstadt, Leverkusen, Barcelona (.com), Osasuna. Bunların hepsi **doğrulandı** sınıfında.

**Şüpheli ya da erişilemeyen alan adları:**
- Nottingham Forest: alan adı doğrulanamadı.
- Salernitana: bağlantı hatası.
- Hoffenheim ve Athletic: 403.
- Sheffield United: yalnızca JavaScript.
- Tek işaretli olanlar ikinci bir resmî kaynakla teyit edilmeden kanıt kaynağı yapılmayacak: Augsburg, Brighton, Lazio, Roma, Napoli, Sassuolo ve fcbarcelona.es. İkinci kaynak örneği: lig sitesindeki kulüp sayfası.

**Gerekli host izinleri:** Pilot için açılması gereken bütün hostlar onayınızla zaten açıldı (48 host). Yeni izin gerekmiyor.

**Kaldırılmasını önerdiğim hostlar** (kullanılamaz çıktılar; liste sizin onayınızla küçültülebilir):
- www.bundesliga.com
- www.tottenhamhotspur.com, www.realmadrid.com, www.cdleganes.com, www.sscnapoli.it ve sscnapoli.it
- www.fcstpauli.com, www.sslazio.it, www.hessenschau.de, www.kicker.de
- www.tsg-hoffenheim.de, www.athletic-club.eus, www.noticiasdenavarra.com, www.deia.eus, www.sassuolocalcio.it, www.ussalernitana1919.it, sport.sky.it
- www.sufc.co.uk, www.nottinghamforest.co.uk
