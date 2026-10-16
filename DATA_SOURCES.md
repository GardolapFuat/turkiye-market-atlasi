# Veri kaynakları ve kapsam

Harita **tam şube envanteri değildir**. Bir yerde pin görünmemesi, o yerde mağaza olmadığı anlamına gelmez. Özellikle A101 ve BİM için OpenStreetMap kapsamı bölgeden bölgeye değişir. İndirme tarihini, kaynak türünü ve kaynak bağlantısını her mağaza kartından inceleyin.

| Kaynak | Kullanım | Atıf / koşullar |
|---|---|---|
| [A101 resmî mağaza bulucu](https://www.a101.com.tr/en-yakin-magazalar) | Kısmi örneklemde ad, adres ve yayımlanmış koordinat | 451 kaynak kaydı; ilk HTTP 403 sonrasında duruldu. Ulusal envanter tamamlanmış değildir. Kaynak kendi koşullarına tabidir. |
| [ŞOK resmî mağaza bulucu](https://kurumsal.sokmarket.com.tr/tr/magazalar) | Ad, adres ve yayımlanmış koordinat | Kaynak kendi koşullarına tabidir; proje bu verilere MIT lisansı vermemektedir. |
| [Migros resmî mağaza bulucu](https://www.migros.com.tr/en-yakin-migros) | Migros/MJet ad, adres ve koordinat | Kaynak kendi koşullarına tabidir; proje bu verilere MIT lisansı vermemektedir. |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | A101/BİM mağazaları, köy/kasaba/mezra etiketli yerleşim noktaları | © OpenStreetMap contributors, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) |
| [Türkiye il poligonları](https://github.com/theaiagent/turkiye_iller_geojson) | Koordinatı il ve bölgeye atama | OSM kökenli; cihadturhan/tr-geojson ve theaiagent/turkiye_iller_geojson, ODbL |
| [GeoNames](https://www.geonames.org/) | Yakın yerleşim adı, arama desteği | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), GeoNames |
| Tekil kontrol kayıtları | Kaynakla incelenmiş az sayıdaki eksik kayıt | `data/verified-corrections.json` içindeki her kaydın kaynak bağlantısı ve kontrol tarihi geçerlidir; tüm haritanın Google Maps ile doğrulandığı iddia edilmez. |

Farklı kaynaklara ait kayıtlar kaynak kimliklerini ve atıflarını korur. Kod lisansı, veri kaynaklarının lisanslarını değiştirmez. OSM kaynaklı veri/uyarlamalar yeniden kullanılırken ODbL koşullarına uyulmalıdır. Diğer kaynaklar için açık yeniden kullanım lisansı varmış gibi bir izin verilmez.

## Koordinat ve filtre kuralları

- Adresten tahminî mağaza koordinatı üretilmez; yerleşim merkezine mağaza pini yerleştirilmez.
- `official`: resmî bulucunun yayımladığı koordinat. Fiziksel olarak bağımsız kontrol edildiği anlamına gelmez.
- `node`: OSM konum noktası. `area_center`: OSM mağaza alanının sınır kutusu merkezi; kapı konumu değildir.
- `source_record`: tekil olarak incelenmiş başka bir kamuya açık işletme kaydı.
- Kaynakta kapalı/terk edilmiş etiketli ve marka adı belirsiz OSM kayıtları çıkarılır. Aynı markanın 12 metre içindeki olası OSM kopyaları tekilleştirilir.
- Resmî A101 kaydının 25 metre çevresindeki aynı markalı OSM kaydı olası mükerrer kabul edilerek resmî kayıt tercih edilir; OSM kaynak bağlantısı `additional_sources` içinde korunur.
- İl poligonlarıyla eşleşmeyen ve açıkça hatalı/eksik koordinatlı kayıtlar tahminle düzeltilmez; derleme raporuna yazılır.
- Köy/kasaba filtresi, OSM `village`, `town`, `hamlet` merkezlerinin 2 km çevresidir. Bu etiketler bugünkü resmî idari statüyü, nüfusu veya kırsallığı kanıtlamaz; kentleşmiş eski köyler ve ilçe merkezleri de bulunabilir.
- Nüfusu eksik GeoNames kaydı sıfır veya küçük nüfus kabul edilmez.
- Yedi bölge, illerin tamamı üzerinden yaklaşık sınıflandırmadır.

Bu proje yerleşim keşfine yardımcı olur. Mağaza varlığı gelişim, imar veya gayrimenkul fiyat artışı tahmini olarak değerlendirilmemelidir.
