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
      (e.key === "Enter" || (e.key === "Tab" && !e.shiftKey)) &&
      input &&
      input.tagName === "INPUT" &&
      input.closest("tr.o_data_row")
    ) {
      const row = input.closest("tr.o_data_row");
      const parentCell = input.closest("[name]");
      const currentFieldName = parentCell?.getAttribute("name") || input.getAttribute("name");

      if (!currentFieldName) return;

      const SERIAL_FIELDS = ["lot_name", "lot_id", "imei", "imei2"];

      // If Enter or Tab is pressed inside a serial/lot/IMEI input:
      if (SERIAL_FIELDS.includes(currentFieldName)) {
        // Collect all visible serial inputs in current row (excluding made_in_country_id, quantity, etc.)
        const serialInputs = Array.from(
          row.querySelectorAll("input:not([readonly]):not([disabled])")
        ).filter((el) => {
          const cell = el.closest("[name]");
          const name = cell?.getAttribute("name") || el.getAttribute("name");
          return SERIAL_FIELDS.includes(name) && el.offsetParent !== null;
        });

        const currentIndex = serialInputs.indexOf(input);
        if (currentIndex !== -1) {
          e.preventDefault();
          e.stopPropagation();

          if (currentIndex < serialInputs.length - 1) {
            // Move to next serial field in the SAME row (e.g. lot_name -> imei -> imei2)
            const nextInput = serialInputs[currentIndex + 1];
            nextInput.focus();
            nextInput.select?.();
          } else {
            // Last serial field in row reached: jump to NEXT row's lot_name field
            const tbody = row.parentElement;
            const allRows = Array.from(tbody.querySelectorAll("tr.o_data_row"));
            const currentRowIndex = allRows.indexOf(row);
            const nextRow = allRows[currentRowIndex + 1];

            const focusLotOnRow = (targetRow) => {
              const targetInput = targetRow.querySelector(
                "[name='lot_name'] input, [name='lot_id'] input, input[name='lot_name'], input[name='lot_id']"
              );
              if (targetInput) {
                targetInput.focus();
                targetInput.select?.();
                return true;
              }
              const targetCell = targetRow.querySelector("[name='lot_name'], [name='lot_id']");
              if (targetCell) {
                targetCell.click();
                setTimeout(() => {
                  const inp = targetRow.querySelector(
                    "[name='lot_name'] input, [name='lot_id'] input, input[name='lot_name'], input[name='lot_id']"
                  );
                  if (inp) {
                    inp.focus();
                    inp.select?.();
                  }
                }, 50);
                return true;
              }
              return false;
            };

            if (nextRow && focusLotOnRow(nextRow)) {
              return;
            }

            // On the last row: click 'Add a line' button to create new row and focus lot_name
            const listContainer = row.closest("table, .o_list_renderer, .o_field_widget") || document;
            const addLineBtn = listContainer.querySelector(
              ".o_field_x2many_list_row_add a, .o_field_x2many_list_row_add button, tr.o_field_x2many_list_row_add a, .o_list_button_add, a.o_field_x2many_list_row_add"
            );
            if (addLineBtn) {
              addLineBtn.click();
              setTimeout(() => {
                const updatedRows = Array.from(tbody.querySelectorAll("tr.o_data_row"));
                const newRow = updatedRows[updatedRows.length - 1];
                if (newRow) {
                  focusLotOnRow(newRow);
                }
              }, 150);
            }
          }
        }
      }
    }
  },
  true
);

