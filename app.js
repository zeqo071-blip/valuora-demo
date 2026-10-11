const form = document.getElementById("analyze-form");
const msg = document.getElementById("msg");
const list = document.getElementById("history");
const KEY = "valuora_history";
const esc = (s) => Object.assign(document.createElement("i"), { textContent: s ?? "" }).innerHTML;
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch { return []; } };

const card = (d) => `
  <article class="card item">
    ${d.image ? `<img src="${esc(d.image)}" alt="" referrerpolicy="no-referrer">` : ""}
    <h3>${esc(d.title)}</h3>
    <p class="price">${Number(d.price).toFixed(2)} AZN <small>(bazar: ${d.market} AZN)</small></p>
    <span class="badge ${d.verdict}">${d.verdict}</span>
  </article>`;

const render = () => { list.innerHTML = load().map(card).join("") || "<p>Hələ analiz yoxdur.</p>"; };

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = form.querySelector("button");
  btn.disabled = true; btn.textContent = "Analiz olunur…"; msg.hidden = true;
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: form.url.value.trim() }),
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || "Xəta baş verdi");
    localStorage.setItem(KEY, JSON.stringify([d, ...load()].slice(0, 30)));
    render(); form.reset();
  } catch (err) {
    msg.textContent = err.message; msg.hidden = false;
  } finally {
    btn.disabled = false; btn.textContent = "Analiz et";
  }
});

document.getElementById("clear").addEventListener("click", () => { localStorage.removeItem(KEY); render(); });
render();
