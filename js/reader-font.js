// Reader font-size buttons for the static chapter pages (translated/, fire-to-future/).
// In-memory only: no localStorage, so nothing is stored on the reader's device.
(function(){
  var scale = 1;
  function apply(){ document.documentElement.style.setProperty("--reader-font-scale", scale); }
  apply();
  document.getElementById("fontDown").addEventListener("click", function(){ scale = Math.max(0.6, scale - 0.1); apply(); });
  document.getElementById("fontUp").addEventListener("click", function(){ scale = Math.min(2.0, scale + 0.1); apply(); });
})();
