// Keep demo mode enabled until the backend URL and its host permission are configured.
const USE_MOCK = true;
const API_URL = "https://YOUR-BACKEND-URL/api/analyze";

const MOCK_RESPONSE = {
  data_status: "demo",
  message: "Synthetic extension test only; no live product analysis or verified price data."
};

async function getData(pageUrl) {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 400));
    return MOCK_RESPONSE;
  }

  const response = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: pageUrl })
  });
  if (!response.ok) throw new Error(`Server returned ${response.status}`);
  return response.json();
}

async function getCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) throw new Error("Could not read the active tab URL.");
  return tab;
}

const pageEl = document.getElementById("page");
const statusEl = document.getElementById("status");
const outEl = document.getElementById("out");
const goBtn = document.getElementById("go");

getCurrentTab()
  .then((tab) => {
    pageEl.textContent = `${tab.title || "Untitled tab"}\n${tab.url}`;
  })
  .catch(() => {
    pageEl.textContent = "Could not read this tab. Try a regular webpage.";
  });

goBtn.addEventListener("click", async () => {
  statusEl.textContent = "Analyzing…";
  outEl.textContent = "";
  goBtn.disabled = true;

  try {
    const tab = await getCurrentTab();
    const data = await getData(tab.url);
    statusEl.textContent = USE_MOCK ? "Demo response (synthetic)" : "Done";
    outEl.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    statusEl.textContent = `Could not analyze this page: ${
      error instanceof Error ? error.message : String(error)
    }`;
  } finally {
    goBtn.disabled = false;
  }
});
