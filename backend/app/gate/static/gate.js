// Optional extras for the gate, which works without them: sends the visitor's
// timezone with each guess, and counts down a pause, reopening the gate at zero.
const tz = document.getElementById("tz");
try {
  if (tz) tz.value = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
} catch {
  // An unknown timezone is shown in UTC.
}

const countdown = document.querySelector("[data-countdown]");
if (countdown) {
  const end = Date.now() + Number(countdown.dataset.countdown) * 1000;
  const tick = () => {
    const left = Math.max(0, Math.ceil((end - Date.now()) / 1000));
    countdown.textContent = `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`;
    if (left === 0) {
      // A fresh GET, never a resubmitted guess.
      window.location.replace(window.location.pathname);
      return;
    }
    window.setTimeout(tick, 250);
  };
  tick();
}
