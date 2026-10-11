const form = document.getElementById("analyze-form");
if (form) {
  const msg = document.getElementById("msg");
  const list = document.getElementById("history");
  const esc = (s) => Object.assign(document.createElement("i"), { textContent: s ?? "" }).innerHTML;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = form.querySelector("button");
    btn.disabled = true; btn.textContent = "Analiz olunur…"; msg.hidden = true;
    try {
      const res = await fetch("/analyze", { method: "POST", body: new FormData(form) });
      const d = await res.json();
      if (!res.ok) throw new Error(d.error || "Xəta baş verdi");
      list.insertAdjacentHTML("afterbegin", `
        <article class="card item">
          ${d.image ? `<img src="${esc(d.image)}" alt="" referrerpolicy="no-referrer">` : ""}
          <h3>${esc(d.title)}</h3>
          <p class="price">${d.price.toFixed(2)} AZN <small>(bazar: ${d.market} AZN)</small></p>
          <span class="badge ${d.verdict}">${d.verdict}</span>
        </article>`);
      form.reset();
    } catch (err) {
      msg.textContent = err.message; msg.hidden = false;
    } finally {
      btn.disabled = false; btn.textContent = "Analiz et";
    }
  });
}
