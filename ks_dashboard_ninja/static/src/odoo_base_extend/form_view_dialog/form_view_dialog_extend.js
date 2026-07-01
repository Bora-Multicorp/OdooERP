/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';
import { onMounted } from "@odoo/owl";

patch(FormViewDialog.prototype,{
    setup(){
        super.setup();
        onMounted(()=>{
            if(this.props.is_expand_icon_visible){
                let expand_icon = this.modalRef.el?.querySelector('.o_expand_button')
                expand_icon?.remove?.()
            }

        });
    },
    async onExpand(){
        if(this.props.is_expand_icon_visible)   return;
        super.onExpand();
    }
});

FormViewDialog.props = {
    ...FormViewDialog.props,
    is_expand_icon_visible : { type: Boolean, optional: true }
}
