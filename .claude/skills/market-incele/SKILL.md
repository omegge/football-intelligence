---
name: market-incele
description: Bir maçın bütün Nesine marketlerini (200'den fazla seçenek dahil) market sözlüğü ve eşdeğerlik sistemiyle inceler; dondurmadan sonra bağımsız olasılıkla fiyat karşılaştırması, eşdeğer marketlerde en yüksek fiyat ve beklenen senaryoya uyan yüksek fiyatlı özel marketleri raporlar. Kullanıcı "bu maçın marketlerini incele", "özel marketlere bak", "200'den fazla marketi incele", "eşdeğer marketlerde en yüksek fiyat" dediğinde kullan.
---

# Market inceleme

**Asıl soru (her analizde):** "Bu bahis sonucunun gerçekleşmesini destekleyen somut kanıtlar nelerdir, karşıt kanıtlar nelerdir ve bu ihtimal neden araştırmaya değerdir?" Amaç yüksek oranı haklı çıkarmak değil; iki yönü de araştırıp en güçlü gerekçeli seçenekleri bulmaktır. Nesine oranları şirket marjı içerir ve gerçek olasılık değildir. Oranlar yalnızca marketleri keşfetmek, piyasa görüşünü anlamak ve (geçerli model varsa) fiyat karşılaştırmak için kullanılır. EV ya da fiyat avantajı ZORUNLU değildir: yalnızca kalibre bir bağımsız olasılık varsa ve belirsizliğiyle birlikte gösterilir.

1. **Dondurma durumu:** `PYTHONPATH=lib python3 -m uygulama.sohbet mac KOD`.
   - Model hazırlanabilir ve tahmin donmamışsa ÖNCE `dondur KOD` çalıştır.
   - Model hazırlanabilir ama tahmin donmamışsa `marketler KOD` oranları gizler (MK-1 sırası).
   - Bu maç için bağımsız model hiç yoksa oranlar KEŞİF amacıyla açılır: şirket marjı içerir, olasılık değildir. Her seçenek destekleyen ve karşıt sportif kanıtla değerlendirilir; yüzde ve EV verilmez.
2. `karsilastir KOD`: dondurmadan sonra güncel bülten (gerekirse çeker); kapsamdaki marketlerde p, başabaş ve EV; eşdeğer olay gruplarında en yüksek fiyat.
3. `marketler KOD`: bütün marketler ve seçenekler (oranlar dondurmadan sonra).
4. **Beklenen senaryoyla uyumlu yüksek fiyatlı özel market:**
   - Bağımsız modelin en olası senaryosundan yola çık (ör. "ev hafif favori, düşük skor").
   - O senaryoya mantıksal olarak uyan özel seçenekleri listele: İY/MS, skor aralığı, handikap, "her iki yarıyı da kazanır", kombine.
   - Kapsamdaki olaylar için p, eşdeğerlik grubundan verilir. Kapsam dışı olanlar (korner, kart, oyuncu, devre) için yalnızca nitel gerekçe yazılır, **hesaplanamaz**.
5. **Kurallar:**
   - Fiyat oranları (marj ayrıştırılmış olsa bile) olasılık olarak sunulmaz.
   - Pozitif EV "model–piyasa ayrışması · doğrulama gerekli" etiketini taşır.
   - `oynanabilirlik` değeri `oynanabilir` olmayan seçenekler (ör. `durumu_dogrulanmamis`) ayrıca işaretlenir.
   - Kullanıcı istemeden kupon kurulmaz.
