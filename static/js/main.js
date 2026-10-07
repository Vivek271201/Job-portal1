// Vanilla JavaScript helpers for JobPortal
document.addEventListener('DOMContentLoaded', () => {
  // Mobile menu
  const btn = document.getElementById('menu-btn'), menu = document.getElementById('mobile-menu');
  if (btn && menu) btn.addEventListener('click', () => menu.classList.toggle('hidden'));

  // Dismissible alerts (auto-hide after 6s)
  document.querySelectorAll('[data-alert]').forEach(el => {
    const close = el.querySelector('[data-alert-close]');
    if (close) close.addEventListener('click', () => el.remove());
    setTimeout(() => el.remove(), 6000);
  });

  // Show / hide password
  document.querySelectorAll('[data-toggle-password]').forEach(b => {
    b.addEventListener('click', () => {
      const input = document.getElementById(b.dataset.togglePassword);
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      b.innerHTML = show ? '<i class="fa-regular fa-eye-slash"></i>' : '<i class="fa-regular fa-eye"></i>';
    });
  });

  // Confirm dialogs + loading state on submit
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', e => {
      if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) { e.preventDefault(); return; }
      const submit = form.querySelector('button[type=submit][data-loading]');
      if (submit && form.checkValidity()) {
        setTimeout(() => { submit.disabled = true; submit.classList.add('is-loading');
          submit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ' + (submit.dataset.loading || 'Please wait...'); }, 0);
      }
    });
  });

  // Image preview for file inputs
  document.querySelectorAll('input[type=file][data-preview]').forEach(input => {
    input.addEventListener('change', () => {
      const target = document.getElementById(input.dataset.preview);
      const f = input.files[0];
      if (f && target) { target.src = URL.createObjectURL(f); target.classList.remove('hidden'); }
    });
  });

  // Client-side file size hint
  document.querySelectorAll('input[type=file][data-max-mb]').forEach(input => {
    input.addEventListener('change', () => {
      const f = input.files[0];
      if (f && f.size > parseFloat(input.dataset.maxMb) * 1024 * 1024) {
        alert('File is too large. Maximum size is ' + input.dataset.maxMb + ' MB.');
        input.value = '';
      }
    });
  });
});
