
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { localization } from "@web/core/l10n/localization";
import {formatDate, formatDateTime} from "@web/core/l10n/dates";
import { formatFloat, formatInteger } from "@web/views/fields/formatters";
import {parseDateTime, parseDate,} from "@web/core/l10n/dates";
import { convert_data_to_utc } from '@ks_dashboard_ninja/js/dn_utils'
import { DNGraph } from '@ks_dashboard_ninja/components/ks_dashboard_graphs/ks_dashboard_graphs';
import { useRecordObserver } from "@web/model/relational_model/utils";



const { useEffect, useRef, xml, onWillUpdateProps, Component, useState} = owl;


class KsListViewPreview extends Component{
    static components = { DNGraph }
    setup() {
        super.setup();
        this.state = useState({
            count: 0
        })
        useRecordObserver( (record) => {
            this.state.count++
            const makeWidgetObservable = { ...record.data }
        })

    }

}
KsListViewPreview.template = "ks_list_view";
export const KsListViewPreviewfield={
    component :KsListViewPreview,
}

registry.category("fields").add("ks_dashboard_list_view_preview", KsListViewPreviewfield);
return {
    KsListViewPreview:KsListViewPreview
}





