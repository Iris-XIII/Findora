# Focused demo: one unisex product

The current matching target is a **Gildan 18000 Heavy Blend adult/unisex crewneck
sweatshirt, Black, size M, new, blank/unprinted, one garment**. Aim for two verified
retailers for this same variant before expanding to more products.

Style references (not evidence of a current price or stock):
- [Manufacturer's 18000 product](https://retail.gildan.com/18000-adult-crewneck-sweatshirt-en_us/)
- [S&S unisex 18000 specification](https://www.ssactivewear.com/ShopNow/ItemSpecSheet.aspx?ColorID=33297&ID=372&LanguageCode=en)

The previous three canonical products and their raw history remain intact. The full
manifest now has four products. `config/focus_products.json` contains only the new
collection target, so the next collection does not repeat the old searches.

From the local `databricks/` directory, with your private `.env` configured:

```bash
python3 -m findora_data.collect --products config/focus_products.json --max-requests 3 --dry-run
python3 -m findora_data.collect --products config/focus_products.json --max-requests 3
python3 -m findora_data.review --output data/review_unisex.json
```

This makes at most one Shopping search and two detail calls. It does not guarantee
matching offers; inspect returned variants before approval. Upload the newly created
JSON response files into the existing Volume responses directory, preserving the old
files. Pull the feature branch in Databricks **before** rerunning the notebook so the
full manifest recognizes the new product ID.

For matching, verify adult/unisex size M, Black, style 18000, single unit, blank/new
condition, USD, and the actual price for quantity one. Reject youth models, hoodies,
printed/customized garments, multipacks, and bulk-only price tiers. Retailer style
aliases require manufacturer evidence; title similarity is not sufficient.

No prices or availability are prefilled. Existing approvals remain empty until review.
The small initial scope verifies exact-item comparison. Similar alternatives and a
larger women's/unisex collection follow after this one-product workflow succeeds.
