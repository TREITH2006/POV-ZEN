// Single source of truth for the production API origin. This must load
// BEFORE api.js on every page (api.js reads window.POV_ZEN_API_BASE at
// script-evaluation time). If the backend's deployed URL ever changes,
// this is the only file that needs editing.
//
// Local development (localhost, 127.0.0.1, file://) is untouched: this
// file only sets the override for the specific production frontend
// hostname below. Everywhere else, window.POV_ZEN_API_BASE stays unset
// and api.js's own same-hostname derivation handles it, exactly as before.
(function () {
  const PRODUCTION_FRONTEND_HOSTNAME = "pov-zen-frontend.onrender.com";
  const PRODUCTION_API_BASE = "https://pov-zen.onrender.com";

  if (window.location.hostname === PRODUCTION_FRONTEND_HOSTNAME) {
    window.POV_ZEN_API_BASE = PRODUCTION_API_BASE;
  }
})();
