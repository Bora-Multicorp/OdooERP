
import { Component, useRef } from "@odoo/owl";
import { standardDashboardItemProps, standardDashboardItemDefaultProps } from '@ks_dashboard_ninja/js/dn_utils';
import { user } from "@web/core/user";
import { useChildRef } from "@web/core/utils/hooks";
import { useChildCb } from '@ks_dashboard_ninja/js/access_utils';


export class Chart extends Component{

    static props = {
        ...standardDashboardItemProps()
    }

    static defaultProps = {
        ...standardDashboardItemDefaultProps()
    }

    setup(){
        // TODO: find another approach for useChildCb
        this.fetchExplanation = useChildCb();
        this.resetChart = useChildRef();
    }

    // todo: applying date filter through contexts should be removed
    getContext(props){
        return {
            ...user.context,
            ksDateFilterSelection: props.dateFilterConfig.dateSelection || 'l_none',
            ksDateFilterStartDate: props.dateFilterConfig.startDate,
            ksDateFilterEndDate: props.dateFilterConfig.endDate
        }
    }

    // Note: props is passed bcz props doesnt change  in case of calling from willUpdateProps

    getDomain(props){
        return {
            ks_domain_1: props.filtersConfig.domainData?.[props.basicData.ks_model_name] ?? [],
            ks_domain_2: props.filtersConfig.domainData?.[props.basicData.ks_model_name_2] ?? [],
        }
    }

    showRefreshButton(){
        this.resetChart.el?.classList.remove('d-none')
    }

    hideRefreshButton(){
        this.resetChart.el?.classList.add('d-none')
    }
}