// /** @odoo-module **/

// import { _t } from "@web/core/l10n/translation";
// import { patch } from "@web/core/utils/patch";
// import { BusService } from "@bus/bus_service";

// // Patch the BusService prototype to add your custom listener
// patch(BusService.prototype, {
//     /**
//      * @override
//      * This method runs when the BusService itself is set up in the frontend.
//      */
//     setup() {
//         this._super(); // Always call the original setup method of BusService.

//         // Add an event listener to the BusService.
//         // The "notification" event is a generic event emitted by BusService
//         // whenever a message is received from the backend bus.
//         // We will filter for our specific message type inside the handler.
//         this.addEventListener("notification", this._onCustomProductNotification);
//     },

//     /**
//      * This method is the handler for all "notification" events received by the BusService.
//      * It checks if the received notification is of our specific type.
//      * @param {CustomEvent} ev - The event object. ev.detail contains { type, payload }.
//      */
//     _onCustomProductNotification(ev) {
//         const { type, payload } = ev.detail; // Extract the type and payload from the event details.

//         // Check if the message type matches the 'notification_type' sent from your Python code.
//         if (type === 'my_custom_notification') {
//             console.log("Received custom product notification:", payload); // Log the received message for debugging.

//             // Get the Odoo notification service to display the alert.
//             // this.env.services provides access to all registered frontend services.
//             const notification = this.env.services.notification;

//             // Ensure the notification service is available before trying to use it.
//             if (notification) {
//                 notification.add(
//                     // Translatable message for the notification body.
//                     _t(`Product ${payload.product_name} (${payload.product_id}) status changed to ${payload.status_changed_to}!`),
//                     {
//                         title: _t("Product Status Update"), // Translatable title for the notification.
//                         type: 'success', // Type of notification (e.g., 'success', 'warning', 'danger', 'info').
//                         sticky: false, // If true, notification stays until user closes it; if false, it disappears automatically.
//                         // You can add more options here, like 'buttons' for interactive actions.
//                     }
//                 );
//             } else {
//                 console.warn("Notification service not found! Cannot display notification.");
//             }
//         }
//     }
// });

/** @odoo-module **/

// /** @odoo-module **/

// import { Component, onWillStart, xml } from "@odoo/owl";
// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";

// export class CustomBusNotification extends Component {
//     static template = xml`<div />`; // Dummy template to avoid render error
//     static props = {}; // 👈 Avoids the props warning

//     setup() {
//         const busService = useService("bus_service");
//         const notification = useService("notification");

//         onWillStart(() => {
//             busService.addEventListener("notification", (ev) => {
//                 const { type, payload } = ev.detail;
//                 if (type === 'my_custom_notification') {
//                     console.log("Received custom product notification:", payload);
//                     notification.add(
//                         `Product ${payload.product_name} (${payload.product_id}) status changed to ${payload.status_changed_to}!`,
//                         {
//                             title: "Product Status Update",
//                             type: "success",
//                         }
//                     );
//                 }
//             });
//         });
//     }
// }

// // Register your component to auto-run in backend
// registry.category("main_components").add("custom_bus_notification", {
//     Component: CustomBusNotification,
// });




/** @odoo-module **/

/** @odoo-module **/

// import { Component, onWillStart, xml } from "@odoo/owl";
// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";

// export class CustomBusNotification extends Component {
//     static template = xml`<div />`;  // Dummy template (still required)
//     static props = {};               // No props expected

//     setup() {
//         // ✅ Add this log to confirm JS is loading
//         console.log("🚀 CustomBusNotification JS loaded and setup() called");

//         const busService = useService("bus_service");
//         const notification = useService("notification");

//         onWillStart(() => {
//             console.log("🚀 onWillStart() called");

//             busService.addEventListener("notification", (ev) => {
//                 console.log("🔔 Received bus notification:", ev.detail); // Notification received

//                 const { type, payload } = ev.detail;

//                 if (type === 'my_custom_notification') {
//                     console.log("✅ Matched custom notification:", payload); // Type matched

//                     notification.add(
//                         `Product ${payload.product_name} (${payload.product_id}) status changed to ${payload.status_changed_to}!`,
//                         {
//                             title: "Product Status Update",
//                             type: "success",
//                         }
//                     );
//                 }
//             });
//         });
//     }
// }

// // Register to backend
// registry.category("main_components").add("custom_bus_notification", {
//     Component: CustomBusNotification,
// });




