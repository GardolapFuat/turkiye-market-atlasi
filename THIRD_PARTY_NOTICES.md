# Üçüncü taraf kaynakları ve lisans bildirimleri

Projenin kökündeki MIT lisansı özgün uygulama ve veri toplama koduna uygulanır. Aşağıdaki kütüphaneler ve veri kaynakları kendi lisanslarını ve atıflarını korur.

## Harita kütüphaneleri

| Paket | Sürüm | Lisans | Korunan tam lisans metni |
| --- | --- | --- | --- |
| [Leaflet](https://leafletjs.com/) | 1.9.4 | BSD 2-Clause | [Leaflet lisansı](docs/vendor/Leaflet-1.9.4-LICENSE.txt) |
| [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster) | 1.5.3 | MIT | [MarkerCluster lisansı](docs/vendor/Leaflet.markercluster-1.5.3-LICENSE.txt) |

Leaflet: Copyright (c) 2010–2023, Volodymyr Agafonkin; Copyright (c) 2010–2011, CloudMade. Leaflet.markercluster: Copyright 2012 David Leaver.

Tam lisans dosyaları 17 Ekim 2026 tarihinde paket dağıtımından değiştirilmeden alındı. Dosya yolları sürüme sabitlenmiş paket metaverisinden belirlendi; indirilen içeriklerin SHA-256 bütünlük değerleri bu metaveriyle karşılaştırıldı.

- Leaflet [paket metaverisi](https://unpkg.com/leaflet@1.9.4/?meta) ve [dağıtılan LICENSE](https://unpkg.com/leaflet@1.9.4/LICENSE).
- Leaflet.markercluster [paket metaverisi](https://unpkg.com/leaflet.markercluster@1.5.3/?meta) ve [dağıtılan MIT-LICENCE.txt](https://unpkg.com/leaflet.markercluster@1.5.3/MIT-LICENCE.txt).

## Coğrafi veriler

**OpenStreetMap:** © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). OSM kaynaklı mağaza kayıtları, yerleşim referansları ve il sınırları [Open Database License 1.0 (ODbL)](https://opendatacommons.org/licenses/odbl/1-0/) koşullarına tabidir. İl sınırlarının dağıtım kaynağı [theaiagent/turkiye_iller_geojson](https://github.com/theaiagent/turkiye_iller_geojson), belirtilen geometri kaynağı OSM üzerinden [cihadturhan/tr-geojson](https://github.com/cihadturhan/tr-geojson) deposudur. İl özellikleri normalleştirilir ve yedi bölge il sınırları üzerinden yaklaşık eşlenir.

**GeoNames:** [GeoNames](https://www.geonames.org/) yerleşim verisi [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) lisanslıdır. Kaynak [Türkiye veri dökümüdür](https://download.geonames.org/export/dump/TR.zip). Proje aktif yerleşim kayıtlarını seçer, alan adlarını normalleştirir, kaynak nüfus değeri sıfır olan kayıtları `null` olarak gösterir ve il/bölge bilgisini poligon eşleşmesiyle ekler. Kaynak koordinatları korunur. Nüfus ve yerleşim türü resmî güncel köy/belde sınıflandırması olarak sunulmaz.

Resmî mağaza bulucularından ve diğer işletme kayıtlarından alınan içeriklerin kaynak bağlantıları ve koşulları [DATA_SOURCES.md](DATA_SOURCES.md) dosyasında açıklanır. Kod lisansı bu içeriklere ek yeniden kullanım izni vermez. Her veri kaydının kaynak kimliği ve atıf bilgileri korunmalıdır.
