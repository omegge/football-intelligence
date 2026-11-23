"""Football Intelligence ortak araştırma altyapısı (yalnızca Python standart kütüphanesi).

Modüller:
  kanit         : kanıt kaydı (iddia, kaynak URL, yayın tarihi, erişim zamanı, doğrulama seviyesi, ölçüm dönemi)
  takim_adlari  : Nesine takım adlarını diğer kaynakların adlarıyla eşleme (belirsiz eşleşme otomatik kabul edilmez)
  girdi         : oranlardan bağımsız maç araştırma girdisi (yalnızca kimlik, takımlar, tarih, lig)
  http          : izinli kaynak listesi, önbellek, hız sınırı, hata yönetimi, kaynak bilgisi
  kaynaklar     : ClubElo ve football-data.co.uk okuyucuları (oran sütunları atılır)

Bu paket Nesine oranlarını okumaz; bülten çekicisinden (football-bulletin-fetch) bağımsızdır.
"""

SURUM = "0.3.0"
USER_AGENT = f"FootballIntelligence/{SURUM} (kisisel arastirma; istek uzerine)"
