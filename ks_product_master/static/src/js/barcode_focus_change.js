/** @odoo-module **/

// console.log("✅ Smart row-navigation loaded (quantity skipped)");

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
        // console.log("⏭️ Reached last input before quantity — letting Odoo handle Enter");
        return; // Allow default behavior (Odoo saves and adds new row)
      }

      // Prevent default Enter & move to next input
      e.preventDefault();
      e.stopPropagation();

      const nextInput = inputs[currentIndex + 1];
      nextInput.focus();
      nextInput.select?.();
      // console.log(`➡️ Focus moved from ${currentFieldName} to next input`);
    }
  },
  true
);
