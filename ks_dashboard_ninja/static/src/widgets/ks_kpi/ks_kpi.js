/** @odoo-module */

import { registry } from "@web/core/registry";
import { dnNumberFormatter } from '@ks_dashboard_ninja/js/dn_utils';
import { getCurrency } from "@web/core/currency";
import { formatFloat,formatInteger } from "@web/views/fields/formatters";
import { imageCacheKey } from "@web/views/fields/image/image_field";
import { url } from "@web/core/utils/urls";
import { DNKpi } from "@ks_dashboard_ninja/components/ks_dashboard_kpi_view/ks_dashboard_kpi";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { useState } from "@odoo/owl";


const { useEffect, useRef,Component} = owl;

class KsKpiPreview extends Component {

    static components = { DNKpi }
    static template = "ks_kpi"

    setup() {
        this.state = useState({
            count: 0
        })
        // TODO: Find another approach to this
        useRecordObserver((record) => {
            this.state.count++
            const makeWidgetObservable = { ...record.data }
        })
    }

}


export const KsKpiPreviewfield = {
    component :KsKpiPreview,
}
registry.category("fields").add("ks_dashboard_kpi_owlpreview",KsKpiPreviewfield);
