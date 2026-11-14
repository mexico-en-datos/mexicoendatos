/* Infórmate: which theme to draw, decided before the page paints. Light on wide screens and dark
   on phones, unless the person chose one here (kept in this browser) or the address says
   ?tema=claro or ?tema=oscuro. */
(() => {
  let choice = null;
  try {
    const url = new URL(location.href);
    const asked = url.searchParams.get("tema");
    if (asked === "claro" || asked === "oscuro") {
      choice = asked;
      localStorage.setItem("tema", asked);
      url.searchParams.delete("tema");
      history.replaceState(null, "", url.pathname + url.search + url.hash);
    } else {
      choice = localStorage.getItem("tema");
    }
  } catch (error) {
    choice = null;
  }
  const dark = choice ? choice === "oscuro" : matchMedia("(max-width: 700px)").matches;
  document.documentElement.dataset.theme = dark ? "dark" : "light";
})();
