"""Read-only judge demo using the Databricks App service principal."""
import os
import re
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

st.set_page_config(page_title="Findora — Dig beneath the price", page_icon="🧥", layout="wide")
st.title("Findora")
st.write("Compare reviewed clothing offers and explore the prices we have actually observed.")
catalog = os.environ.get("FINDORA_CATALOG", "findora_hackathon")
if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", catalog):
    st.error("Invalid catalog configuration.")
    st.stop()
namespace = f"`{catalog}`.gold"


@st.cache_data(ttl=60)
def query(statement, parameters=None):
    cfg = Config()
    warehouse = os.environ["DATABRICKS_WAREHOUSE_ID"]
    with sql.connect(server_hostname=urlsplit(cfg.host).hostname,
                     http_path=f"/sql/1.0/warehouses/{warehouse}",
                     credentials_provider=lambda: cfg.authenticate) as conn:
        with conn.cursor() as cursor:
            cursor.execute(statement, parameters=parameters or {})
            return pd.DataFrame.from_records(cursor.fetchall(), columns=[c[0] for c in cursor.description])


try:
    products = query(f"SELECT product_id, title, category, data_status FROM {namespace}.product_catalog ORDER BY title")
    if products.empty:
        st.info("Product collection has not been loaded yet.")
        st.stop()
    category = st.selectbox("Category", ["All"] + sorted(products.category.unique().tolist()))
    choices = products if category == "All" else products[products.category == category]
    labels = dict(zip(choices.product_id, choices.title))
    selected = st.selectbox("Product", list(labels), format_func=labels.get)
    params = {"product_id": selected}
    offers = query(f"SELECT retailer, price, currency, product_url, observed_at FROM {namespace}.current_offers WHERE product_id = :product_id ORDER BY price", params)
    history = query(f"SELECT retailer, price, observed_at FROM {namespace}.product_offers WHERE product_id = :product_id ORDER BY observed_at", params)
    st.subheader("Reviewed retailer offers")
    st.caption("Observed snapshots from the last 24 hours. Listed prices in USD; shipping and tax may be additional. Recheck the selected variant at the store.")
    if offers.empty:
        st.info("No reviewed offers from the last 24 hours. Collect and review a new snapshot.")
    else:
        suggested = offers.iloc[0]
        st.subheader("An option to consider")
        st.write(f"{labels[selected]} — {suggested.retailer}, ${suggested.price:,.2f} USD.")
        st.write("Why: this listing was reviewed against the selected product's model, color, and size. "
                 "It has the lowest listed price among the fresh reviewed offers in this dataset.")
        st.caption(f"Based on {len(offers)} reviewed offer(s); this is not a market-wide comparison or a buy-now prediction. "
                   f"Observed at {suggested.observed_at}. Confirm the variant and checkout total at the store.")
        st.metric("Lowest observed listed price", f"${offers.price.min():,.2f}")
        st.dataframe(offers, hide_index=True, use_container_width=True,
                     column_config={"product_url": st.column_config.LinkColumn("Store listing")})
    st.subheader("Observed price history")
    if history.empty:
        st.info("No reviewed price observations yet.")
    else:
        history["observed_at"] = pd.to_datetime(history.observed_at, utc=True)
        st.scatter_chart(history, x="observed_at", y="price", color="retailer")
        st.caption("Each point is an observed retailer price, not a forecast. All timestamps are UTC.")
        dates = history.observed_at.dt.date.nunique()
        span = history.observed_at.max() - history.observed_at.min()
        # DEMO HARD RULE: labeled demo data never produces real buy/wait advice,
        # even when it satisfies the date/span thresholds.
        is_demo = str(products.loc[products.product_id == selected, "data_status"].iloc[0]) == "demo"
        if is_demo:
            st.info("DEMO dataset — labeled seed data never produces real buy/wait advice, regardless of its date coverage.")
        elif dates < 3 or span < pd.Timedelta(hours=48):
            st.info("INSUFFICIENT_DATA — not enough dated history for buy/wait advice.")
        else:
            st.info("Historical observations are available. Buy/wait rules are provided by the main application's backend.")
        with st.expander("View source observations"):
            st.dataframe(history, hide_index=True, use_container_width=True)
except Exception:
    # Credentials and connection strings should never reach a judge's browser.
    st.error("Data is unavailable. Check the app's warehouse resource, Gold table permissions, and completed ingestion run.")
