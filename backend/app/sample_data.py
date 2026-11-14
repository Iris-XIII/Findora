"""ILLUSTRATIVE mock records only. Not observed retailer data."""
PRODUCTS = {
 "demo-headphones-a": {"product_id":"demo-headphones-a","title":"Demo Wireless Headphones","brand":"Example Audio","category":"Audio","image_url":None,"description":"Illustrative product for integration testing","data_status":"demo"},
 "demo-headphones-b": {"product_id":"demo-headphones-b","title":"Demo Studio Headphones","brand":"Example Audio","category":"Audio","image_url":None,"description":"Illustrative alternative","data_status":"demo"},
 "demo-headphones-c": {"product_id":"demo-headphones-c","title":"Demo Travel Headphones","brand":"Sample Sound","category":"Audio","image_url":None,"description":"Illustrative alternative","data_status":"demo"},
}
OFFERS = {"demo-headphones-a":[
 {"offer_id":"demo-offer-1","retailer":"Demo Store A","price":129.99,"currency":"USD","url":"https://example.com/a","observed_at":"2026-11-14T12:00:00Z","match_type":"exact","source_type":"demo"},
 {"offer_id":"demo-offer-2","retailer":"Demo Store B","price":119.99,"currency":"USD","url":"https://example.com/b","observed_at":"2026-11-14T12:00:00Z","match_type":"exact","source_type":"demo"}
]}
HISTORY = {"demo-headphones-a":[
 {"observed_at":"2026-11-01T12:00:00Z","price":149.99,"currency":"USD","retailer":"Demo Store A","source_type":"demo"},
 {"observed_at":"2026-11-07T12:00:00Z","price":139.99,"currency":"USD","retailer":"Demo Store A","source_type":"demo"},
 {"observed_at":"2026-11-14T12:00:00Z","price":129.99,"currency":"USD","retailer":"Demo Store A","source_type":"demo"}
]}
SIMILAR = {"demo-headphones-a":[
 {"product_id":"demo-headphones-b","title":"Demo Studio Headphones","brand":"Example Audio","price":109.99,"reason":"Same category and brand (demo)"},
 {"product_id":"demo-headphones-c","title":"Demo Travel Headphones","brand":"Sample Sound","price":99.99,"reason":"Same category (demo)"}
]}
