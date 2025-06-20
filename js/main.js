document.addEventListener("DOMContentLoaded", () => {
  const observer = new MutationObserver(() => {
    const dialog = document.querySelector(".md-search__dialog");
    if (!dialog) return;

    // 対象のspanやテキストを明るく
    dialog.querySelectorAll("span, p, em, div, .md-search__meta").forEach(el => {
      el.style.color = "#e0e0e0";
    });
  });

  observer.observe(document.body, { childList: true, subtree: true });
});
