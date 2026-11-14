# Open B's code in Databricks using Git

Repository: `https://github.com/Iris-XIII/MadHack_2026.git`

Branch: `codex/databricks-serpapi`

The repository already exists. Create a Databricks Git folder pointing to it; no new
GitHub repository is needed. This branch contains B's code and tests. Raw responses,
ZIP files, and `.env` are excluded from Git.

1. In Databricks, open **Workspace** and your own folder.
2. Choose **Create → Git folder**. Enter the repository URL above and select GitHub.
   If prompted, connect the GitHub account that has access to this repository.
   Authenticate in the Databricks/GitHub UI; do not paste tokens into chat or notebooks.
3. After cloning, open the Git dialog and select branch **codex/databricks-serpapi**.
4. Open **databricks/notebooks/01_ingest** and select **Serverless** notebook compute.
5. Keep `catalog=workspace` and leave `project_root` blank. Run **only the first code cell**.
   It creates schemas, tables, and the raw-data Volume directory.
6. Open **Catalog → workspace → bronze → Volumes → serpapi_raw → responses**.
   Upload all 11 `.json` files from the local directory:

   ```text
   MadHack_2026/databricks/data/raw/
   ```

   Destination: `/Volumes/workspace/bronze/serpapi_raw/responses`.
   Upload the JSON files themselves, not the workspace ZIP, review queue, or `.env`.
7. Return to the notebook and click **Run All**.

Expected initial counts: 130 Bronze candidates, 3 canonical products, 0 approved
offers. Exact variants/prices still need review before offers enter Silver/Gold.
No SerpAPI key or new API calls are needed to ingest these existing files.

If folder discovery fails, set `project_root` to the workspace path ending in
`MadHack_2026/databricks`, then run again. After local changes are pushed, use **Pull**
in the Databricks Git dialog to update the cloud copy.

The notebook and App have not yet been run in your workspace. Send the resulting
counts or error text after the first run. App deployment and backend integration
follow ingestion verification.

[Official Databricks Git folder instructions](https://docs.databricks.com/aws/en/repos/git-operations-with-repos)
