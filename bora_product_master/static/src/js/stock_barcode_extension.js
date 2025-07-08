odoo.define('bora_product_master.stock_barcode_extension', function (require) {
    "use strict";

    var core = require('web.core');
    var BarcodeParser = require('barcodes.BarcodeParser');
    var PickingBarcodeHandler = require('stock_barcode.PickingBarcodeHandler'); // Or the specific barcode handler you're using

    // Extend the existing barcode handler
    PickingBarcodeHandler.include({
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.barcode_parser = new BarcodeParser({'nomenclature_id': options.nomenclature_id});
            this.imei_field_name = 'imei_number'; // Your custom field name
        },

        // Override the _onBarcodeScanned method
        _onBarcodeScanned: function (barcode) {
            var self = this;
            return this._super.apply(this, arguments).then(function (result) {
                // Check if a product was successfully identified by the barcode
                // and if the current context is a stock.move.line form
                if (self.current_line && self.current_line.record_id && self.imei_field_name) {
                    var $imeiField = self.$("input[name='" + self.imei_field_name + "']");
                    if ($imeiField.length > 0) {
                        $imeiField.focus();
                        return $.Deferred().resolve(true); // Indicate success
                    }
                }
                return $.Deferred().resolve(result); // Continue with default behavior
            });
        },

        // Override the _processSerialNumber method or similar if you have specific serial handling
        // This part might need more specific logic depending on how you're using serials/lots
        _processSerialNumber: function (barcode) {
            var self = this;
            return this._super.apply(this, arguments).then(function (result) {
                if (result.success && self.current_line && self.imei_field_name) {
                    var $imeiField = self.$("input[name='" + self.imei_field_name + "']");
                    if ($imeiField.length > 0) {
                        $imeiField.focus();
                        return $.Deferred().resolve(true);
                    }
                }
                return $.Deferred().resolve(result);
            });
        },

        // You might also need to handle the 'change' event on your IMEI field
        // to move to the next serial line after IMEI is entered
        _bindActionEvents: function () {
            this._super.apply(this, arguments);
            var self = this;
            this.$el.on('change', "input[name='" + this.imei_field_name + "']", function () {
                // After IMEI is entered, try to move to the next serial line or commit the current line
                // This logic can be complex as it depends on how Odoo handles adding new lines
                // You might need to trigger a 'create_new_line' or 'add_quantity' action
                // or just simulate a 'Tab' key press.

                // A simple approach might be to simulate a Tab press
                $(this).trigger($.Event('keydown', { keyCode: 9, which: 9 })); // Simulate Tab key

                // Or, if you know the next field's name, you can focus it directly
                // self.$("input[name='next_serial_number_field']").focus();
            });
        },
    });
});