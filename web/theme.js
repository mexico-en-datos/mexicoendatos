/* Infórmate: which theme to draw, decided before the page paints. Light everywhere; dark only on
   wide screens and only when chosen, by the link at the end of the bar (kept in this browser) or
   by an address with ?tema=oscuro. Phones stay light for now. */
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
  const dark = choice === "oscuro" && !matchMedia("(max-width: 700px)").matches;
  document.documentElement.dataset.theme = dark ? "dark" : "light";
})();
