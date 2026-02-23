
import { useBus } from "@web/core/utils/hooks";
import { useComponent } from "@odoo/owl";


export function setupItemEventBus(bus){
    const component = useComponent();

    if(component.props.itemId && !component.props.isFormPreview){

        useBus(bus, `item_${component.props.itemId}`, ({ detail }) => {

            if(detail.isForced || component.allowItemFetching){
                if(component.activeChartActions){
                    component.showRefreshButton()
                    return;
                }
                component.fetchOrUpdateItem.bind(component)(component.props)
            }

            if(detail.allowItemFetching){
                component.allowItemFetching = true
                component.showRefreshButton()
            }

        })
    }
}

export function useChildCb(){
    let defined = false;
    let callBack;
    return function getCallBack(CB) {
        callBack = CB;
        if (defined) {
            return;
        }
        Object.defineProperty(getCallBack, "cb", {
            get() {
                return callBack;
            },
        });
        defined = true;
    };
}

export function useForwardCbToParent(cbName){
    const component = useComponent()
    const cb = component[cbName]?.bind(component)
    if(component.props[cbName]){
        component.props[cbName](cb);
    }
    return cb
}




