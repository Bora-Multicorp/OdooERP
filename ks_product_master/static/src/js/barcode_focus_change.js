/** @odoo-module **/

let lastLotInput = null;

// Track focus and user interaction on lot/serial number input fields
document.addEventListener(
  "focusin",
  function (e) {
    const input = e.target;
    if (input && input.tagName === "INPUT") {
      const parentDiv = input.closest("div[name]");
      const fieldName = parentDiv?.getAttribute("name") || input.getAttribute("name");
      if (fieldName === "lot_name" || fieldName === "lot_id") {
        lastLotInput = input;
      }
    }
  },
  true
);

// Function to refocus and select text on the lot/serial input
function focusBackToLotInput() {
  setTimeout(() => {
    let targetInput = null;
    if (
      lastLotInput &&
      document.body.contains(lastLotInput) &&
      lastLotInput.offsetParent !== null
    ) {
      targetInput = lastLotInput;
    } else {
      // Find active row or form view lot/serial input
      const activeRow =
        document.querySelector("tr.o_data_row.o_selected_row") ||
        document.querySelector("tr.o_data_row:focus-within") ||
        document.querySelector("tr.o_data_row");
      if (activeRow) {
        targetInput = activeRow.querySelector(
          "div[name='lot_name'] input, div[name='lot_id'] input, input[name='lot_name'], input[name='lot_id']"
        );
      }
      if (!targetInput) {
        targetInput = document.querySelector(
          ".o_form_view div[name='lot_name'] input, .o_form_view div[name='lot_id'] input, .o_form_view input[name='lot_name'], .o_form_view input[name='lot_id']"
        );
      }
    }

    if (targetInput) {
      targetInput.focus();
      if (typeof targetInput.select === "function") {
        targetInput.select();
      }
    }
  }, 100);
}

// Watch for Error/Warning modals popping up in the DOM
const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    // Check added nodes for error dialogs
    for (const node of mutation.addedNodes) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        const modalEl =
          node.classList?.contains("modal") || node.classList?.contains("o_dialog")
            ? node
            : node.querySelector?.(".modal, .o_dialog");

        if (modalEl) {
          const text = (modalEl.textContent || "").toLowerCase();
          if (
            text.includes("already used") ||
            text.includes("serial number") ||
            text.includes("lot_name") ||
            text.includes("lot/serial")
          ) {
            modalEl._isLotErrorModal = true;
            node._isLotErrorModal = true;
          }
        }
      }
    }

    // Check removed nodes (dialog closed)
    for (const node of mutation.removedNodes) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        if (node._isLotErrorModal || node.querySelector?.("[_isLotErrorModal]")) {
          focusBackToLotInput();
        }
      }
    }
  }
});

function startObserver() {
  const targetNode = document.body || document.documentElement;
  if (targetNode) {
    observer.observe(targetNode, { childList: true, subtree: true });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startObserver);
} else {
  startObserver();
}

document.addEventListener(
  "keydown",
  function (e) {
    const input = e.target;

    if (
      e.key === "Enter" &&
      input.tagName === "INPUT" &&
      input.closest("tr.o_data_row") &&
      input.classList.contains("o_input")
    ) {
      const row = input.closest("tr.o_data_row");
      const parentFieldDiv = input.closest("div[name]");
      const currentFieldName = parentFieldDiv?.getAttribute("name");

      if (!currentFieldName) return;

      // Collect all visible editable inputs BEFORE 'quantity'
      const inputs = Array.from(
        row.querySelectorAll("div[name] input.o_input:not([readonly]):not([disabled])")
      ).filter((el) => {
        const div = el.closest("div[name]");
        const name = div?.getAttribute("name");
        return name !== "quantity" && el.offsetParent !== null;
      });

      const currentIndex = inputs.indexOf(input);

      // If current field is the last one before quantity, let Odoo handle next row
      if (currentIndex === -1 || currentIndex === inputs.length - 1) {
        return; // Allow default behavior (Odoo saves and adds new row)
      }

      // Prevent default Enter & move to next input
      e.preventDefault();
      e.stopPropagation();

      const nextInput = inputs[currentIndex + 1];
      nextInput.focus();
      nextInput.select?.();
    }
  },
  true
);

