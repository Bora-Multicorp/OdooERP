/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";

class ReadOnlyProductTemplateFormController extends FormController {
    /**
     * @override
     * The setup method runs once when the component is instantiated.
     */
    setup() {
        // Call the parent's setup method FIRST to ensure proper initialization
        // For direct class extension, 'super.setup()' is correct.
        super.setup();

        // Check if this controller instance is for the 'product.template' model
        // and if it's the main form view (if that's your intent)
        // If you've used a specific XML view for your inheritance, you might check this.props.viewId
        // or ensure your XML has a js_class attribute pointing to this controller.
        if (this.props.resModel === 'product.template') { // && this.props.viewId === 'product.product_template_only_form_view'
            // Set the form mode to 'readonly'. This is the most effective way to make it read-only.
            this.props.mode = 'readonly';
            console.log("ReadOnlyProductTemplateFormController: Forced mode to readonly.");
        }
    }

    /**
     * @override
     * This method controls whether the "Edit" button is enabled/visible
     * and generally if the form can transition to edit mode.
     */
    async canEdit() {
        // Prevent editing for the product.template model
        if (this.props.resModel === 'product.template') {
            console.log("ReadOnlyProductTemplateFormController: canEdit() returning false.");
            return false; // Always return false to disable editing
        }
        // For other models, let the default behavior apply
        return await super.canEdit();
    }
}

// Register this controller with a unique key.
// This key will be referenced in your XML view's 'js_class' attribute.
registry.category("views").add("product_template_readonly_controller", {
    ...registry.category("views").get("form"), // Inherit properties from the base form view type
    Controller: ReadOnlyProductTemplateFormController,
});