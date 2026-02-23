
import { Component, useState, useRef } from "@odoo/owl"
import { DateTimeInput } from "@web/core/datetime/datetime_input";
//import { setObjectInCookie, getObjectFromCookie, eraseCookie } from "@ks_dashboard_ninja/js/cookies";
import { parseDateTime, parseDate, formatDate, formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { setObjectInCookie, getObjectFromCookie, eraseCookie } from "@ks_dashboard_ninja/js/cookies";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { getSessionStorage, setSessionStorage, sessionKeys } from "@ks_dashboard_ninja/js/cookies";



export class KsDateFilter extends Component{
    static props = {
        dashboardData: { type : Object, optional : true },
        data: { type : Object, optional : true },
        updateHeaderMode: { type : Function, optional : true },
        update: { type : Function, optional : true }
    }
    static components = { Dropdown, DateTimeInput, DropdownItem }
    static template = "ks_dashboard_ninja.Ks_date_filter"

    setup(){
        this.notification = useService('notification')

        //todo: freeze dashboard_manager  for no changes during debugging
        this.userMode = this.props.dashboardData.ks_dashboard_manager ? "manager" : "user"

        this.dateFilters = {
            'l_none': _t('All Time'),
            'l_day': _t('Today'),
            't_week': _t('This Week'),
            'td_week': _t('Week To Date'),
            't_month': _t('This Month'),
            'td_month': _t('Month to Date'),
            't_quarter': _t('This Quarter'),
            'td_quarter': _t('Quarter to Date'),
            't_year': _t('This Year'),
            'td_year': _t('Year to Date'),
            'n_day': _t('Next Day'),
            'n_week': _t('Next Week'),
            'n_month': _t('Next Month'),
            'n_quarter': _t('Next Quarter'),
            'n_year': _t('Next Year'),
            'ls_day': _t('Last Day'),
            'ls_week': _t('Last Week'),
            'ls_month': _t('Last Month'),
            'ls_quarter': _t('Last Quarter'),
            'ls_year': _t('Last Year'),
            'l_week': _t('Last 7 days'),
            'l_month': _t('Last 30 days'),
            'l_quarter': _t('Last 90 days'),
            'l_year': _t('Last 365 days'),
            'ls_past_until_now': _t('Past Till Now'),
            'ls_pastwithout_now': _t('Past Excluding Today'),
            'n_future_starting_now': _t('Future Starting Now'),
            'n_futurestarting_tomorrow': _t('Future Starting Tomorrow'),
            'l_custom': _t('Custom Filter'),
        }

        let config = getSessionStorage(sessionKeys.dateFilter + this.props.dashboardData.id) ?? this.props.data.config
        this.state = useState({
            showCustomDates : false,
            showCustomDatesSymbol : config?.dateSelection === 'l_custom', // used after applying custom dates to show that custom date filter is applied
            dateFilters : this.dateFilters,
            config: config,
        })
    }

    get isMobile(){
        return isMobileOS();
    }

    get startDate(){
        if(this.state.config.startDate){
            return typeof this.state.config.startDate === 'string' ? parseDateTime(this.state.config.startDate) : this.state.config.startDate
        }
        return luxon.DateTime.now()
    }

    get endDate(){
        if(this.state.config.endDate){
            return typeof this.state.config.endDate === 'string' ? parseDateTime(this.state.config.endDate) : this.state.config.endDate
        }
        return this.props.data.ks_default_end_time ? luxon.DateTime.now().endOf('day') : luxon.DateTime.now();
    }

    // TODO: data should get updated while applying same date filter again bcz time d=gets updated
    dateFilterSelect(dateSelection) {
        sessionStorage.removeItem('dateFilter' + this.props.dashboardData.id);

        this.state.config = {
            dateSelection: dateSelection,
            startDate: dateSelection === 'l_custom' ? this.startDate : false,
            endDate: dateSelection === 'l_custom' ? this.endDate : false,
        }

        if(dateSelection === 'l_custom'){
            this.props.updateHeaderMode("custom_date")
            Object.assign(this.state, { showCustomDates: true, showCustomDatesSymbol: false })
            return
        }
        else{
            this.props.updateHeaderMode(this.userMode)
            Object.assign(this.state, { showCustomDates: false, showCustomDatesSymbol: false })
        }

        this.applyFilter()

        // TODO: mode updattion and more
    }

    getDateTime(value){
        return typeof value === 'string' ? parseDateTime(value) : value
    }

    customDateChecks(){
        let startDate = this.getDateTime(this.state.config.startDate)
        let endDate = this.getDateTime(this.state.config.endDate)

        if (startDate && endDate) {
            if (startDate <= endDate) {
                return true;
            }
            else{
                this.notification.add(_t("Start date should be less than end date."), { type: "warning"})
            }
        } else {
            let notification_text = !this.state.config.startDate && !this.state.config.endDate
                ? "Please enter start date and end date." : `Please enter ${ !this.state.config.startDate ? "start" : "end" } date`;
            this.notification.add(_t(notification_text), { type: "warning"});
        }
        return false;
    }

    applyFilter() {

        if(this.state.config.dateSelection === 'l_custom'){
            let isOk = this.customDateChecks()
            if(!isOk)   return

            this.props.updateHeaderMode(this.userMode)
            Object.assign(this.state, { showCustomDates: false, showCustomDatesSymbol: true })
        }

        setSessionStorage(sessionKeys.dateFilter + this.props.dashboardData.id, this.state.config, this.notification)

        this.props.update(this.state.config)

    }

    changeStartDate(args){
        this.state.config.startDate = args ? args : luxon.DateTime.now()
    }

    changeEndDate(args){
        this.state.config.endDate = args ? args : luxon.DateTime.now()
    }

    resetFilter(){
        sessionStorage.removeItem('dateFilter' + this.props.dashboardData.id)
        Object.assign(this.state, {
            config: { dateSelection: 'l_none', startDate: false, endDate: false },
            showCustomDates: false,
            showCustomDatesSymbol: false
        })
        this.props.updateHeaderMode(this.userMode)
        this.applyFilter()
    }

    showCustomDates(){
        this.props.updateHeaderMode("custom_date")
        Object.assign(this.state, { showCustomDates: true, showCustomDatesSymbol: false })
    }

}