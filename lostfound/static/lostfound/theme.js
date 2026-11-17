/* ==========================================================================
   CAMPUS LOST & FOUND - THEME & NAVIGATION CONTROLLER
   Unified theme management (Dark Mode / Bright Mode) and responsive menu
   ========================================================================== */

/**
 * Apply the selected theme to the root element, persist in localStorage,
 * and update all relevant UI elements.
 * @param {string} theme - 'dark' or 'light'
 */
function applyTheme(theme) {
    const targetTheme = theme === "light" ? "light" : "dark";

    // Set theme attribute on root element
    document.documentElement.setAttribute("data-theme", targetTheme);

    // Save to both storage keys for 100% cross-page compatibility
    try {
        localStorage.setItem("theme", targetTheme);
        localStorage.setItem("campusTheme", targetTheme);
    } catch (e) {
        console.warn("localStorage not accessible:", e);
    }

    // Refresh UI components (label, icon, aria attributes)
    updateThemeUI(targetTheme);
}

/**
 * Update the header theme toggle switch, label, and icon to reflect the current theme.
 * @param {string} [currentTheme] - optional theme override ('dark' | 'light')
 */
function updateThemeUI(currentTheme) {
    const theme =
        currentTheme ||
        document.documentElement.getAttribute("data-theme") ||
        "dark";

    const isLight = theme === "light";

    // Update label text ("Bright Mode" vs "Dark Mode")
    const themeLabel = document.getElementById("themeLabel");
    if (themeLabel) {
        themeLabel.textContent = isLight ? "Bright Mode" : "Dark Mode";
    }

    // Update switch icon inside the toggle knob
    const switchIcon = document.getElementById("switchIcon");
    if (switchIcon) {
        switchIcon.textContent = isLight ? "☀" : "☾";
    }

    // Update accessibility attributes on the button
    const themeToggle = document.getElementById("themeToggle");
    if (themeToggle) {
        themeToggle.setAttribute("aria-pressed", isLight ? "true" : "false");
        themeToggle.setAttribute(
            "title",
            isLight ? "Switch to Dark Mode" : "Switch to Bright Mode"
        );
    }
}

/**
 * Backward compatibility alias for templates using updateThemeLabel()
 */
function updateThemeLabel() {
    updateThemeUI();
}

/**
 * Backward compatibility alias for templates using updateThemeButton(theme)
 */
function updateThemeButton(theme) {
    updateThemeUI(theme);
}

/**
 * Toggle between Dark Mode and Bright Mode.
 */
function changeTheme() {
    const currentTheme =
        document.documentElement.getAttribute("data-theme") || "dark";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    applyTheme(newTheme);
}

/**
 * Toggle the mobile navigation drawer.
 */
function toggleMobileMenu() {
    const nav = document.getElementById("mainNavigation");
    const btn = document.getElementById("mobileMenuBtn");

    if (!nav || !btn) return;

    const isOpen = nav.classList.toggle("nav-open");
    btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
}

/**
 * Close the mobile navigation drawer.
 */
function closeMobileMenu() {
    const nav = document.getElementById("mainNavigation");
    const btn = document.getElementById("mobileMenuBtn");

    if (nav && nav.classList.contains("nav-open")) {
        nav.classList.remove("nav-open");
        if (btn) {
            btn.setAttribute("aria-expanded", "false");
        }
    }
}

/* ==========================================================================
   INITIALIZATION & EVENT LISTENERS
   ========================================================================== */

// Immediately apply saved theme to avoid FOUC (Flash of Unstyled Content)
(function () {
    try {
        const savedTheme =
            localStorage.getItem("theme") ||
            localStorage.getItem("campusTheme") ||
            "dark";

        document.documentElement.setAttribute("data-theme", savedTheme);
    } catch (e) {
        document.documentElement.setAttribute("data-theme", "dark");
    }
})();

// Once DOM is loaded, synchronize the UI controls and register interactions
document.addEventListener("DOMContentLoaded", function () {
    const currentTheme =
        document.documentElement.getAttribute("data-theme") || "dark";
    updateThemeUI(currentTheme);

    // Close mobile menu when clicking outside of header / navigation
    document.addEventListener("click", function (event) {
        const nav = document.getElementById("mainNavigation");
        const btn = document.getElementById("mobileMenuBtn");

        if (nav && btn && nav.classList.contains("nav-open")) {
            if (!nav.contains(event.target) && !btn.contains(event.target)) {
                closeMobileMenu();
            }
        }
    });

    // Close mobile menu on Escape key press
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMobileMenu();
        }
    });

    // Reset mobile navigation when resizing up to desktop
    window.addEventListener("resize", function () {
        if (window.innerWidth > 1024) {
            closeMobileMenu();
        }
    });
});
