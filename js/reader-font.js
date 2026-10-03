// Reader font-size buttons for the static chapter pages (translated/, fire-to-future/).
// The chosen size is kept in localStorage ("reader-font-scale") so it carries over
// between chapters. It is written only when the reader clicks a button, holds just
// that number, never leaves the device, and is removed again at the default size
// (see privacy.html: strictly necessary storage, Law 506/2004 art. 4(6)(b)).
(function(){
  var KEY = "reader-font-scale";
  var scale = 1;
  try {
    var saved = parseFloat(localStorage.getItem(KEY));
    if (saved >= 0.6 && saved <= 2.0) { scale = saved; }
  } catch (e) { /* storage blocked: in-memory only */ }
  function apply(){ document.documentElement.style.setProperty("--reader-font-scale", scale); }
  function set(next){
    scale = Math.round(Math.min(2.0, Math.max(0.6, next)) * 10) / 10;
    apply();
    try {
      if (scale === 1) { localStorage.removeItem(KEY); } else { localStorage.setItem(KEY, String(scale)); }
    } catch (e) { /* storage blocked: in-memory only */ }
  }
  apply();
  document.getElementById("fontDown").addEventListener("click", function(){ set(scale - 0.1); });
  document.getElementById("fontUp").addEventListener("click", function(){ set(scale + 0.1); });
})();
