// Countdown for the quiz page. The server enforces the limit too, so this is
// only for the student's convenience: it auto-submits the form at 0.
(function () {
  var el = document.getElementById("timer");
  var form = document.getElementById("quiz-form");
  if (!el || !form) return;

  var deadline = Date.now() + parseInt(el.dataset.seconds, 10) * 1000;
  var submitted = false;
  form.addEventListener("submit", function () { submitted = true; });

  function pad(n) { return (n < 10 ? "0" : "") + n; }

  function tick() {
    var left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
    el.textContent = pad(Math.floor(left / 60)) + ":" + pad(left % 60);
    el.classList.toggle("warn", left <= 30);
    if (left === 0) {
      if (!submitted) { submitted = true; form.submit(); }
      return;
    }
    setTimeout(tick, 250);
  }
  tick();
})();
