/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { setObjectInCookie, getObjectFromCookie, eraseCookie } from "@ks_dashboard_ninja/js/cookies";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { getSessionStorage, setSessionStorage, sessionKeys } from "@ks_dashboard_ninja/js/cookies";


export class FavFilterWizard extends Component{
    static template = "ks_dashboard_ninja.fav_filter_wizard"
    static components = { Dialog }

    setup(){
        this.notification = useService("notification")
        this.state = useState({
            name: '',
            accessId: false,
        })
    }

    onSave(ev){
        if(this.state.name){
            this.props.addFavFilterData({name: this.state.name, user_id: this.state.accessId ? false : user.userId})
            this.props.close()
            return
        }
        this.notification.add(_t("Name is required"), { type: "warning" })
    }
}


export class FavouriteFilter extends Component{
    static props = {
        data: { type: Object, optional: true },
        onDelete: { type: Function, optional: true },
        update: { type: Function, optional: true },
        remove: { type: Function, optional: true },
        options: { type: Object, optional: true },
    };
    static defaultProps = {

    };
    static template = "ks_dashboard_ninja.favourite_filter"
    static components = { Dropdown, DropdownItem }

    setup(){
        this.notification = useService('notification')
        this.orm = useService('orm')
        this.state = useState({
            activeId: getSessionStorage(sessionKeys.ffActiveId + this.props.options.ks_dashboard_id) ?? false
        })

    }

    onSelect(filter){
        if(filter.id !== this.state.activeId){
            if(this.state.activeId)    this.removeFilter(this.props.data[this.state.activeId])
            this.addFilter(filter)
        }
        else{
            this.removeFilter(filter)
        }
    }

    setSessionStorage(){
        setSessionStorage(sessionKeys.ffActiveId + this.props.options.ks_dashboard_id, this.state.activeId, this.notification)
    }

    removeSessionStorage(){
        sessionStorage.removeItem(sessionKeys.ffActiveId + this.props.options.ks_dashboard_id)
    }

    calcModelSubDomains(filter){
        let modelSubDomains = {}

        Object.keys(filter.ks_filter).forEach( (model) => {

            let domain = filter.ks_filter[model]
            modelSubDomains[model] = { [`FF_${filter.id}`]: domain }

        })
        return modelSubDomains
    }

    addFilter(filter){
        this.removeSessionStorage()
        this.state.activeId = filter.id
        this.setSessionStorage()
        this.props.update(this.calcModelSubDomains(filter))
    }

    removeFilter(filter){
        this.removeSessionStorage()
        this.state.activeId = false
        this.props.remove(this.calcModelSubDomains(filter))
        this.setSessionStorage()
    }

    ondelete(filter){
        let user_id = filter.user_id;

        this.env.services.dialog.add(ConfirmationDialog, {
            body: _t(`This filter is will be removed${user_id ? ' ' : ' for everybody '}if you continue.`),
            confirmLabel: _t("Delete Filter"),
            title: _t("Delete Filter"),
            confirm: () => {
                if(filter.id === this.state.activeId)   this.removeFilter(filter)
                this.props.onDelete(filter.id)
                this.orm.unlink('ks_dashboard_ninja.favourite_filters', [filter.id])
            }
        })
    }

}
