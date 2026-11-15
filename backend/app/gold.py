"""Read-only Gold adapter. Values are bound parameters; identifiers are validated."""
import os
import re
from urllib.parse import urlsplit


class DataUnavailable(RuntimeError):
    pass


class Gold:
    def __init__(self, query=None):
        catalog = os.getenv('FINDORA_CATALOG', 'findora_hackathon')
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*', catalog):
            raise ValueError('Invalid FINDORA_CATALOG')
        self.ns = f'`{catalog}`.gold'
        self.query = query or self._query

    def _query(self, statement, parameters=None):
        try:
            from databricks import sql
            from databricks.sdk.core import Config
            cfg = Config()
            path = os.environ['DATABRICKS_HTTP_PATH']
            with sql.connect(server_hostname=urlsplit(cfg.host).hostname, http_path=path,
                             credentials_provider=lambda: cfg.authenticate) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(statement, parameters=parameters or {})
                    names = [c[0] for c in cursor.description]
                    return [dict(zip(names, row)) for row in cursor.fetchall()]
        except Exception:
            raise DataUnavailable('Databricks data is unavailable') from None

    def health(self):
        self.query(f'SELECT product_id FROM {self.ns}.product_catalog LIMIT 1')

    def products(self, query='', product_id=None):
        where = 'product_id = :id' if product_id is not None else 'contains(lower(concat(title, \' \', coalesce(brand, \'\'))), lower(:query))'
        rows = self.query(f'''SELECT product_id, title, brand, category, image_url,
            CAST(NULL AS STRING) AS description, data_status FROM {self.ns}.product_catalog
            WHERE {where} ORDER BY title LIMIT 50''', {'id': product_id} if product_id is not None else {'query': query})
        for row in rows:
            if row['data_status'] not in ('demo', 'observed'):
                row['data_status'] = 'insufficient'
        return rows

    def observations(self, product, current=False):
        # Filter at the API boundary too: Gold history deliberately retains revoked rows.
        table = 'current_offers' if current else 'product_offers'
        sources = "source_type = 'demo'" if product['data_status'] == 'demo' else "source_type IN ('snapshot', 'live')"
        fresh = 'AND observed_at >= current_timestamp() - INTERVAL 24 HOURS' if current else ''
        return self.query(f'''SELECT offer_id, retailer, price, currency, product_url AS url,
            observed_at, match_type, source_type FROM {self.ns}.{table}
            WHERE product_id = :id AND match_type = 'exact' AND {sources}
            AND price > 0 AND NOT isnan(price) AND price < CAST('Infinity' AS DOUBLE)
            AND currency = 'USD' AND observed_at <= current_timestamp() {fresh}
            ORDER BY {'price, retailer' if current else 'observed_at, offer_id'}''', {'id': product['product_id']})
