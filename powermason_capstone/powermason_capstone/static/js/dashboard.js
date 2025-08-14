console.log("Sidebar JS loaded!");
document.addEventListener("DOMContentLoaded", () => {
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebarClose = document.getElementById('sidebarClose');
  const sidebar = document.getElementById('sidebar');

  // Open sidebar (mobile)
  sidebarToggle?.addEventListener('click', () => {
    sidebar.classList.add('open');
  });

  // Close sidebar (mobile)
  sidebarClose?.addEventListener('click', () => {
    sidebar.classList.remove('open');
  });

  // Highlight active link on click
  document.querySelectorAll('.sidebar-menu-item > a').forEach(link => {
    link.addEventListener('click', () => {
      // Remove active from all
      document.querySelectorAll('.sidebar-menu-item').forEach(item => item.classList.remove('active', 'bg-blue-100'));
      // Add active to parent <li>
      link.parentElement.classList.add('active', 'bg-blue-100');
    });
  });

  // Toggle submenu buttons
  document.querySelectorAll('[data-submenu-toggle]').forEach(button => {
    button.addEventListener('click', () => {
      const submenu = button.nextElementSibling; // <ul> submenu
      const arrow = button.querySelector('svg.ml-auto');

      // Toggle submenu visibility
      submenu.classList.toggle('hidden');

      // Rotate arrow
      arrow.classList.toggle('rotate-180');

      // Optional: toggle active styling for button
      button.parentElement.classList.toggle('bg-blue-50');
    });
  });
  // ====== Fade out Django messages ======
  const container = document.getElementById('message-container');
  if (container) {
    setTimeout(() => {
      container.style.transition = "opacity 0.5s ease";
      container.style.opacity = 0;
      setTimeout(() => container.remove(), 500);
    }, 3000); // 3 seconds
  }
});
