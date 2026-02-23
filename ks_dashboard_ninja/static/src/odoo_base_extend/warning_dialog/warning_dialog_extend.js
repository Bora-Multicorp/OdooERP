/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { onMounted } from "@odoo/owl";
import { renderToString } from "@web/core/utils/render";
import { WarningDialog } from "@web/core/errors/error_dialogs";

patch(WarningDialog.prototype,{
    setup(){
        super.setup();

        onMounted( () => {
            let modalBody = this.env.services.ui.activeElement?.querySelector('.modal-body');
            this.env.services.ui.activeElement?.querySelector('.modal-content')?.classList?.add('error-modal-ks');
            if(modalBody && (this.env.services.menu?.getCurrentApp()?.xmlid === "ks_dashboard_ninja.board_menu_root" ||
                                                    this.env.services.action?.currentController?.action?.tag === 'ks_dashboard_ninja')){
                modalBody.innerHTML = renderToString('ks_dashboard_ninja.ksAccessErrorDialog', {
                    message: this.message ,
                });
            }
        });
    }
});