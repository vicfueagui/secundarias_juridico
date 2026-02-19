(function () {
  "use strict";

  function elementMatches(el, selector) {
    if (!el || el.nodeType !== 1) {
      return false;
    }
    var proto = Element.prototype;
    var matchFn =
      el.matches ||
      proto.matches ||
      proto.webkitMatchesSelector ||
      proto.msMatchesSelector;
    if (!matchFn) {
      return false;
    }
    return matchFn.call(el, selector);
  }

  function closestMatch(el, selector) {
    var current = el;
    while (current && current.nodeType === 1) {
      if (elementMatches(current, selector)) {
        return current;
      }
      current = current.parentElement;
    }
    return null;
  }

  function initTramiteModalFallback() {
    var modal = document.getElementById("tramite-caso-modal");
    if (!modal) {
      return;
    }
    document.addEventListener("click", function (event) {
      var openTrigger = closestMatch(event.target, "[data-tramite-caso-modal-open]");
      if (openTrigger) {
        event.preventDefault();
        modal.hidden = false;
        var firstInput = modal.querySelector("input, select, textarea, button");
        if (firstInput && typeof firstInput.focus === "function") {
          firstInput.focus();
        }
        return;
      }
      var closeTrigger = closestMatch(event.target, "#tramite-caso-modal [data-modal-close]");
      if (closeTrigger) {
        event.preventDefault();
        modal.hidden = true;
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTramiteModalFallback);
  } else {
    initTramiteModalFallback();
  }
})();
