/** @odoo-module */

import { registry } from "@web/core/registry";
import { globalfunction } from '@ks_dashboard_ninja/js/dn_utils';
import { getCurrency } from "@web/core/currency";
import { formatFloat,formatInteger } from "@web/views/fields/formatters";
import { imageCacheKey } from "@web/views/fields/image/image_field";
import { url } from "@web/core/utils/urls";
import { Component, useState, useEffect } from "@odoo/owl";
import { DNTile } from '@ks_dashboard_ninja/components/ks_dashboard_tile_view/ks_dashboard_tile';
import { useRecordObserver } from "@web/model/relational_model/utils";


class TilePreview extends Component {

    static components = { DNTile }
    static template = 'ks_dashboard_ninja.tile_widget_view'

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


 export const tilePreviewWidget = {
    component: TilePreview,
 }
 registry.category("fields").add('ks_dashboard_item_preview_owl', tilePreviewWidget);

