document.addEventListener("DOMContentLoaded", function () {

  // Password show/hide toggles
  document.querySelectorAll(".password-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var targetId = btn.getAttribute("data-target");
      var input = document.getElementById(targetId);
      if (!input) return;

      var revealed = input.type === "text";
      input.type = revealed ? "password" : "text";
      btn.classList.toggle("is-revealed", !revealed);
      btn.setAttribute("aria-label", revealed ? "Show password" : "Hide password");
    });
  });

  // Live "passwords match" hint on the registration page
  var password = document.getElementById("password");
  var confirm = document.getElementById("confirm_password");
  var hint = document.getElementById("password-hint");

  if (password && confirm && hint) {
    var checkMatch = function () {
      if (!confirm.value) {
        hint.textContent = "";
        hint.classList.remove("is-error");
        return;
      }
      if (password.value === confirm.value) {
        hint.textContent = "Passwords match.";
        hint.classList.remove("is-error");
      } else {
        hint.textContent = "Passwords don't match yet.";
        hint.classList.add("is-error");
      }
    };
    password.addEventListener("input", checkMatch);
    confirm.addEventListener("input", checkMatch);
  }

  // ---- Dashboard: hamburger toggles sidebar on small screens ----
  // dashboard.css hides .sidebar under 860px and only shows it again
  // when it has an .open class — but nothing was ever adding that
  // class. This wires up .hamburger to toggle .sidebar + a dimming
  // .overlay (both classes already styled in dashboard.css).
  var hamburger = document.querySelector(".hamburger");
  var sidebar = document.querySelector(".sidebar");
  var overlay = document.querySelector(".overlay");

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("open");
  }

  function openSidebar() {
    if (sidebar) sidebar.classList.add("open");
    if (overlay) overlay.classList.add("open");
  }

  if (hamburger && sidebar) {
    hamburger.addEventListener("click", function () {
      var isOpen = sidebar.classList.contains("open");
      if (isOpen) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  if (overlay) {
    overlay.addEventListener("click", closeSidebar);
  }

  // Close sidebar if window is resized back up past the breakpoint
  window.addEventListener("resize", function () {
    if (window.innerWidth > 860) {
      closeSidebar();
    }
  });

  // ---- Dashboard: profile dropdown toggle ----
  // dashboard.css defines .profile-dropdown.open but nothing toggles
  // it either. Wiring it up here so the avatar menu actually opens.
  var navProfile = document.querySelector(".nav-profile");
  var profileDropdown = document.querySelector(".profile-dropdown");

  if (navProfile && profileDropdown) {
    navProfile.addEventListener("click", function (e) {
      e.stopPropagation();
      profileDropdown.classList.toggle("open");
    });
    document.addEventListener("click", function (e) {
      if (!profileDropdown.contains(e.target)) {
        profileDropdown.classList.remove("open");
      }
    });
  }
});