/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import {KsListViewPreview} from '@ks_dashboard_ninja/widgets/ks_list_view/ks_list_view';
import {DNGraph} from '@ks_dashboard_ninja/components/ks_dashboard_graphs/ks_dashboard_graphs'
import { localization } from "@web/core/l10n/localization";
import {formatDate,formatDateTime} from "@web/core/l10n/dates";
import { formatFloat,formatInteger } from "@web/views/fields/formatters";
import {parseDateTime,parseDate,} from "@web/core/l10n/dates";
import { session } from "@web/session";
import { convert_data_to_utc } from '@ks_dashboard_ninja/js/dn_utils'
import { debounce } from "@bus/workers/websocket_worker_utils";


patch(DNGraph.prototype,{
    setup(){
        super.setup()
        this.debouncedSortList = debounce(this.sortList, 500)
    },

    async sortList(column){
        let sortOrder = 'ASC'

        if(this.props.isFormPreview)    return

        if(this.listViewActionsConfig.listOrderConfig)
            sortOrder = this.listViewActionsConfig.listOrderConfig.sortOrder === 'ASC' ? 'DESC' : 'ASC'

        this.listViewActionsConfig.listOrderConfig = { fieldId: column.id, sortOrder }
        let args = [
            [this.props.itemId], column.id, sortOrder,
            this.listViewActionsConfig.currentOffset, this.getDomain(this.props)
        ]

        let kwargs = { context: this.getContext(this.props) }
        let listViewConfig = await this.orm.call('ks_dashboard_ninja.item', 'ks_get_list_data_orderby_extend', args, kwargs)
        this.state.listViewConfig = listViewConfig
    },

});

