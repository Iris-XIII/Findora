// Keep demo mode enabled until the backend URL and its host permission are configured.
const USE_MOCK = true;
const API_URL = "https://YOUR-BACKEND-URL/api/analyze";
const FRONTEND_HOME_URL = "file:///Users/aubreyfeldman/Desktop/MadHack_2026/frontend/index.html?fromExtension=1";

const MOCK_RESPONSE = {
  product: {
    product_id: "northpeak-fp-hood-100",
    title: "NorthPeak Fleece Hoodie",
    brand: "NorthPeak",
    variant: "Charcoal / L"
  },
  data_status: "demo",
  decision: "INSUFFICIENT_DATA",
  analysis: "The synthetic sample moves from $59.99 to $49.99 across 3 dated fixture points. It is not a real price trend or buying recommendation.",
  observations: [
    { observed_at: "2026-11-01T12:00:00Z", price: 59.99, currency: "USD", source_type: "demo" },
    { observed_at: "2026-11-07T12:00:00Z", price: 54.99, currency: "USD", source_type: "demo" },
    { observed_at: "2026-11-14T12:00:00Z", price: 49.99, currency: "USD", source_type: "demo" }
  ]
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
const goBtn = document.getElementById("go");
const inspectScreenEl = document.getElementById("inspect-screen");
const analysisScreenEl = document.getElementById("analysis-screen");
const inspectNewFindBtn = document.getElementById("inspect-new-find");
const openHomepageBtn = document.getElementById("open-homepage");
const actionStatusEl = document.getElementById("action-status");
const analysisSummaryEl = document.getElementById("analysis-summary");
const productTitleEl = document.getElementById("product-title");
const productMetaEl = document.getElementById("product-meta");
const currentPriceEl = document.getElementById("current-price");
const decisionEl = document.getElementById("decision");
const observationCountEl = document.getElementById("observation-count");
const historyChartEl = document.getElementById("history-chart");

function formatPrice(price) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD"
  }).format(price);
}

function formatObservationDate(value) {
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC"
  });
}

function createSvgElement(name, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attributes).forEach(([attribute, value]) => {
    element.setAttribute(attribute, String(value));
  });
  return element;
}

function renderDemoAnalysis(data) {
  const { product, observations } = data;
  const latestObservation = observations[observations.length - 1];

  productTitleEl.textContent = product.title;
  productMetaEl.textContent = `${product.brand} · ${product.variant}`;
  currentPriceEl.textContent = formatPrice(latestObservation.price);
  decisionEl.textContent = data.decision;
  analysisSummaryEl.textContent = data.analysis;
  observationCountEl.textContent = `${observations.length} synthetic points`;

  const prices = observations.map(({ price }) => price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const points = observations.map((observation, index) => ({
    observation,
    x: observations.length === 1 ? 330 : 55 + (index * 550) / (observations.length - 1),
    y: maxPrice === minPrice ? 48 : 36 + ((maxPrice - observation.price) / (maxPrice - minPrice)) * 24
  }));
  const path = points
    .map(({ x, y }, index) => `${index === 0 ? "M" : "L"} ${x} ${y}`)
    .join(" ");
  const chartPoints = points.map(({ observation, x, y }) => {
    const label = createSvgElement("g", { class: "chart-point" });
    const labelY = y - 32;
    const date = createSvgElement("text", {
      class: "chart-date",
      x,
      y: labelY + 11,
      "text-anchor": "middle"
    });
    date.textContent = formatObservationDate(observation.observed_at);

    const price = createSvgElement("text", {
      class: "chart-price",
      x,
      y: labelY + 23,
      "text-anchor": "middle"
    });
    price.textContent = formatPrice(observation.price);

    label.append(
      createSvgElement("rect", {
        class: "chart-label",
        x: x - 52,
        y: labelY,
        width: 104,
        height: 28,
        rx: 7
      }),
      date,
      price,
      createSvgElement("circle", { class: "chart-dot", cx: x, cy: y, r: 4 })
    );
    return label;
  });

  historyChartEl.setAttribute(
    "aria-label",
    `Synthetic sample price history: ${observations
      .map(({ observed_at, price }) => `${formatObservationDate(observed_at)} ${formatPrice(price)}`)
      .join(", ")}`
  );
  historyChartEl.replaceChildren(
    createSvgElement("path", { class: "chart-line", d: path }),
    ...chartPoints
  );
}

renderDemoAnalysis(MOCK_RESPONSE);

getCurrentTab()
  .then((tab) => {
    pageEl.textContent = `${tab.title || "Untitled tab"}\n${tab.url}`;
  })
  .catch(() => {
    pageEl.textContent = "The active page is unavailable in this preview.";
  });

goBtn.addEventListener("click", async () => {
  statusEl.textContent = "Loading the synthetic clothing analysis…";
  goBtn.disabled = true;

  try {
    const pageUrl = USE_MOCK ? "" : (await getCurrentTab()).url;
    const data = await getData(pageUrl);
    renderDemoAnalysis(data);
    statusEl.textContent = "This synthetic fixture is not matched to the active page.";
    inspectScreenEl.hidden = true;
    analysisScreenEl.hidden = false;
  } catch (error) {
    statusEl.textContent = `Could not analyze this page: ${
      error instanceof Error ? error.message : String(error)
    }`;
  } finally {
    goBtn.disabled = false;
  }
});

inspectNewFindBtn.addEventListener("click", () => {
  actionStatusEl.textContent = "";
  analysisScreenEl.hidden = true;
  inspectScreenEl.hidden = false;
  goBtn.focus();
});

openHomepageBtn.addEventListener("click", async () => {
  actionStatusEl.textContent = "";
  try {
    const url = window.location.protocol === "file:"
      ? new URL("../frontend/index.html?fromExtension=1", window.location.href).href
      : FRONTEND_HOME_URL;
    await chrome.tabs.create({ url });
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    actionStatusEl.textContent = `Could not open the local frontend: ${detail}. If Chrome blocks the file URL, enable “Allow access to file URLs” in the extension details.`;
  }
});
