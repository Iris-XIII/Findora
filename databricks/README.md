# Databricks setup — owner B

1. Confirm workspace access, available catalog/schema privileges, SQL warehouse, and Apps availability.
2. Choose **documented real data sources**. Add provenance, original URLs, collection method, and observed times.
3. Load raw offers into Bronze; normalize into Silver; aggregate into Gold.
4. Run the validation queries in `sql/validation.sql` and save counts/results in `docs/progress/databricks.md`.
5. Coordinate with backend owner to connect Gold query results to FastAPI.
6. Deploy a **Databricks App** with a small product lookup using Gold data; record its accessible URL and redeploy/check Sunday morning before judging.

`sql/` files are templates: adapt catalog/schema names and source fields to the actual workspace. No fake historical observations should be presented as real.
