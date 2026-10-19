const menuToggle = document.querySelector(".menu-toggle");
const navLinks = document.querySelector(".nav-links");
const icon = menuToggle.querySelector("i");

menuToggle.addEventListener("click", () => {
    navLinks.classList.toggle("active");

    if(navLinks.classList.contains("active")){
        icon.classList.remove("fa-bars");
        icon.classList.add("fa-xmark");
    }else{
        icon.classList.remove("fa-xmark");
        icon.classList.add("fa-bars");
    }
});

const contactForm = document.querySelector("#contact-form");
const contactStatus = document.querySelector("#contact-status");
const contactSubmitButton = contactForm.querySelector('button[type="submit"]');

contactForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  contactStatus.textContent = "Mengirim pesan...";
  contactSubmitButton.disabled = true;

  const formData = new FormData(contactForm);
  const data = Object.fromEntries(formData.entries());

  try {
    const response = await fetch(contactForm.dataset.apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(result.error || "Pesan gagal dikirim.");
    }

    contactStatus.textContent = "Pesan berhasil dikirim.";
    contactForm.reset();
  } catch (error) {
    contactStatus.textContent =
      error instanceof TypeError
        ? "Tidak dapat terhubung ke server. Pastikan backend Flask sedang berjalan."
        : error.message;
  } finally {
    contactSubmitButton.disabled = false;
  }
});