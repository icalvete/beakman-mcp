// Cuenta, sin saber quién, cuánto se usa un «Ponte a prueba»: suma 1 cuando se empieza una sección (la primera vez que
// se toca algo en ella, en cada visita) y cuando se marcan las 12 preguntas. No manda respuestas, notas ni nada más.
// El servidor solo acepta secciones que existen (ver mcp/beakman_mcp/metricas.py). Ni cookies ni nada guardado.
(() => {
  const ruta = location.pathname.replace(/index\.html$/, "");
  const enviado = new Set();
  const avisa = (k) => {
    if (enviado.has(k)) return;
    enviado.add(k);
    const url = "/_cuenta?p=" + encodeURIComponent(ruta) + "&k=" + encodeURIComponent(k);
    try { if (!navigator.sendBeacon || !navigator.sendBeacon(url)) fetch(url, { method: "POST", keepalive: true }); }
    catch (e) { /* contar nunca puede romper la página */ }
  };
  const alTocar = (ev) => {
    const sec = ev.target.closest && ev.target.closest("section.block[id]");
    if (sec && ev.target.closest("button, input, select, textarea, summary, label, a")) avisa(sec.id);
  };
  document.addEventListener("click", alTocar, true);
  document.addEventListener("change", alTocar, true);
  // Las 12 preguntas: cuenta al marcar la última en esta visita, no al abrir la página con todo marcado de antes.
  const marcador = document.getElementById("qscore");
  if (marcador) {
    const completas = () => /sin marcar 0\b/.test(marcador.textContent);
    let antes = completas();
    new MutationObserver(() => {
      const ahora = completas();
      if (ahora && !antes) avisa("completa");
      antes = ahora;
    }).observe(marcador, { childList: true, subtree: true, characterData: true });
  }
})();
