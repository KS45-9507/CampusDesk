document.addEventListener("DOMContentLoaded", () => {
  const menuButton = document.querySelector(".mobile-menu-toggle");
  const menuBackdrop = document.querySelector(".nav-backdrop");
  const closeMobileMenu = () => {
    document.body.classList.remove("mobile-nav-open");
    menuButton?.setAttribute("aria-expanded", "false");
    menuButton?.setAttribute("aria-label", "Open navigation menu");
  };
  if (menuButton && menuBackdrop) {
    menuButton.addEventListener("click", () => {
      const open = document.body.classList.toggle("mobile-nav-open");
      menuButton.setAttribute("aria-expanded", open ? "true" : "false");
      menuButton.setAttribute("aria-label", open ? "Close navigation menu" : "Open navigation menu");
    });
    menuBackdrop.addEventListener("click", closeMobileMenu);
    document.querySelectorAll(".sidebar .nav-link").forEach((link) => link.addEventListener("click", closeMobileMenu));
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeMobileMenu(); });
  }
  const themeToggle = document.querySelector(".theme-toggle");
  const savedTheme = window.localStorage.getItem("campusdesk-theme");
  if (savedTheme === "dark") document.body.classList.add("dark-mode");
  if (themeToggle) {
    themeToggle.setAttribute("aria-pressed", document.body.classList.contains("dark-mode") ? "true" : "false");
    const syncThemeButton = () => {
      const dark = document.body.classList.contains("dark-mode");
      themeToggle.setAttribute("aria-pressed", dark ? "true" : "false");
      themeToggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
      themeToggle.setAttribute("title", dark ? "Switch to light theme" : "Switch to dark theme");
    };
    syncThemeButton();
    themeToggle.addEventListener("click", () => {
      const enabled = document.body.classList.toggle("dark-mode");
      window.localStorage.setItem("campusdesk-theme", enabled ? "dark" : "light");
      syncThemeButton();
    });
  }
  const paymentDialog = document.querySelector(".payment-dialog");
  if (paymentDialog) {
    document.querySelector("[data-payment-open]")?.addEventListener("click", () => paymentDialog.showModal());
    paymentDialog.querySelectorAll("[data-payment-close], .payment-close").forEach((button) => button.addEventListener("click", () => paymentDialog.close()));
    paymentDialog.querySelector("[data-payment-confirm]")?.addEventListener("click", () => {
      const method = paymentDialog.querySelector('input[name="payment-method"]:checked')?.value || "selected method";
      const success = paymentDialog.querySelector(".payment-success");
      success.textContent = `Demo checkout complete using ${method}. No money was charged.`;
      success.hidden = false;
    });
    paymentDialog.addEventListener("click", (event) => { if (event.target === paymentDialog) paymentDialog.close(); });
  }
  const passwordToggle = document.querySelector(".password-toggle");
  const passwordInput = document.querySelector("#login-password");
  if (passwordToggle && passwordInput) {
    passwordToggle.addEventListener("click", () => {
      const visible = passwordInput.type === "password";
      passwordInput.type = visible ? "text" : "password";
      passwordToggle.textContent = visible ? "Hide" : "Show";
      passwordToggle.setAttribute("aria-label", visible ? "Hide password" : "Show password");
      passwordToggle.setAttribute("aria-pressed", visible ? "true" : "false");
    });
  }
  const filePicker = document.querySelector("#csv-file");
  const csvData = document.querySelector("#csv-data");
  if (filePicker && csvData) {
    filePicker.addEventListener("change", async () => {
      const [file] = filePicker.files || [];
      if (!file) return;
      csvData.value = await file.text();
      csvData.dispatchEvent(new Event("input", { bubbles: true }));
      filePicker.closest(".file-drop").querySelector("strong").textContent = file.name;
    });
  }

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
});
