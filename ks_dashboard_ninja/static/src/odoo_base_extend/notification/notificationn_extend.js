/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { onMounted, useRef, onWillUnmount } from "@odoo/owl";
import { Notification } from "@web/core/notifications/notification";
import { renderToElement } from "@web/core/utils/render";

patch(Notification.prototype,{
    setup(){
        super.setup();
        this.notificationRef = useRef('notificationRef');
        onMounted( () => {
            let notificationContainer = this.notificationRef.el ? [this.notificationRef.el] : document.querySelectorAll('.o-main-components-container .o_notification');
            if( (this.props.ks_dn_flag && notificationContainer) || (notificationContainer && (this.env.services.menu?.getCurrentApp()?.xmlid === "ks_dashboard_ninja.board_menu_root" ||
                                                    this.env.services.action?.currentController?.action?.tag === 'ks_dashboard_ninja'))){
                let image = renderToElement('ks_dashboard_ninja.ksNotificationImage', {
                                                type: this.props.type ,
                                            });
                notificationContainer.forEach((notification) => {
                    notification.parentElement.classList.add('ks-dn-website-notification');
                    notification.prepend(image);
                })
            }
        });
        onWillUnmount(() => {
            let notificationContainer = this.notificationRef.el ? [this.notificationRef.el] : document.querySelectorAll('.o-main-components-container .o_notification');
            if(notificationContainer){
                notificationContainer.forEach((notification) => {
                    notification.parentElement.classList.remove('ks-dn-website-notification');
                })
            }
        });
    }

});

Notification.props = {
    ...Notification.props,
    ks_dn_flag: { type: Boolean, optional: true },
};


