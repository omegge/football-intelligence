"""Katman 2 — haber araştırma altyapısı (yalnızca standart kütüphane). Tasarım: docs/HABER_KATMANI.md.

Modüller:
  kaynak       : host kaydı (sınıf, kimlik işaretleri, kullanım koşulları / robots özeti) ve uyum sınıflandırması
  kimlik       : resmî kulüp sitesi keşfi ve iki işaretle kimlik doğrulama (Wikipedia + sitenin kendi başlığı)
  sayfa        : HTML'den yayın zamanı adayları, gövde metni (kenar çubuğu kesilir), görünür tarihler — ağsız
  okuyucu      : güvenli sayfa okuyucu (yalnızca 'kullanilabilir' hostlar; hız sınırı, Retry-After, zaman aşımı)
  zaman        : yayın zamanı çözümleme ve maç başlangıcıyla karşılaştırma
  kanit_kaydi  : yapılandırılmış haber kanıtı (fi.kanit.Kanit) ve durum kayıtları (eksik / engel / doğrulanamadı)
  arastirma    : tarihsel ve güncel araştırma oturumları (ayrı klasör, etiket, dondurma)

Kurallar: arama özeti kanıt değildir; yayın zamanı maç başlangıcından önce DOĞRULANMAYAN içerik maç öncesi kanıt
olamaz; aynı yayıncı grubundaki tekrarlar bağımsız teyit sayılmaz; haberin nicel olasılık etkisi her zaman
"hesaplanamaz" (doğrulanmış etki modeli yok); Nesine / bahis kaynakları reddedilir (MK-1).
"""
