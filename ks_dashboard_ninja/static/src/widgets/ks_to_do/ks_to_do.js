/** @odoo-module */

import { formatDate, parseDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { DNTodo } from '@ks_dashboard_ninja/components/ks_dashboard_to_do_item/ks_dashboard_to_do';
import { useRecordObserver } from "@web/model/relational_model/utils";

const { useEffect, useRef, onWillStart , Component } = owl;

class KsToDOViewPreview extends Component {
    static components = { DNTodo }

    setup() {
        super.setup();
        useRecordObserver( (record) => {
            const makeWidgetObservable = { ...record.data}
        })
    }
}
KsToDOViewPreview.template="ks_to_do_container";
export const KsToDOViewPreviewfield = {
    component:KsToDOViewPreview
}
registry.category("fields").add("ks_dashboard_to_do_preview", KsToDOViewPreviewfield);

