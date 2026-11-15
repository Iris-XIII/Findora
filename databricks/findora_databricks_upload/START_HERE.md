# Start here: direct Databricks upload

No Git repository or API key is needed for this import. The package contains the
Python pipeline, your collected responses, product targets, and the companion App source.
The private local `.env` file is deliberately excluded.

1. Open your chosen Databricks **Workspace** folder.
2. Open the folder's **⋮** menu → **Import** and choose `findora_databricks_upload.zip`.
   Databricks extracts ZIP imports into files and notebooks. Expand the resulting
   folder(s) until you see `Findora_B/01_ingest`.
3. Open `01_ingest`. Select **Serverless** notebook compute. This is separate from
   the SQL warehouse used by the SQL Editor and App.
4. Keep `catalog` set to `workspace`; leave `project_root` blank.
5. Click **Run All**. If automatic folder detection fails, copy the workspace path
   of the `Findora_B` folder into `project_root`, including the `/Workspace/` prefix,
   then run again.

The notebook creates `workspace.bronze`, `workspace.silver`, and `workspace.gold`,
copies included responses into `/Volumes/workspace/bronze/serpapi_raw/responses`,
and builds tables/views. Repeated runs preserve identical raw files and do not
add duplicate observations. A conflicting file is rejected rather than overwritten.

For this initial package, compare the printed counts to `PACKAGE_MANIFEST.json`:
11 saved responses, 130 unique Bronze candidates, 3 canonical products, and 0
approved exact offers. Zero approved offers is expected until variant review;
it does not mean ingestion failed. The notebook displays a candidate review table
and saves `review_queue.generated.json` in the Volume for inspection.

After the first successful run, send the printed counts or the full error text
(without credentials). Next we will verify retailer/variant evidence, fill
`config/approvals.json`, rerun the notebook, and deploy the App from `app/`.
Reviewers must confirm model, color, size/fit, USD price, condition, and availability.
Google redirect destinations must be recorded; a search result title is insufficient.

The pipeline is tested locally. Databricks execution and permissions still require
this first actual workspace run. Nothing has been deployed by importing the ZIP alone.

## Local private key file (only for future collection)

Put your replacement SerpAPI key on this line in `databricks/.env` on your local machine:

```dotenv
SERPAPI_API_KEY=your_key_here
```

The collector reads it automatically; an existing environment variable takes precedence.
Do not upload `.env`, put the key in a notebook, or paste it into chat. The supplied
upload notebook does not call SerpAPI. Once you need a new collection, run from `databricks/`:

```bash
python3 -m findora_data.collect --max-requests 9
```

Rebuild an upload ZIP after local code/data changes with:

```bash
python3 -m findora_data.package_upload
```

Official import instructions:
[Databricks workspace files](https://docs.databricks.com/aws/en/files/workspace-basics).
