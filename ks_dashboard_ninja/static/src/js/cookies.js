
export function setSessionStorage(key, value, notificationService){
    try{
        sessionStorage.setItem(key, JSON.stringify(value))
    }
    catch(e){
        if (e.name === "QuotaExceededError")
            notificationService.add(_t('Session storage full. Cannot retain filter anymore'));
    }
}

export const sessionKeys = {
    dashboardDomainData: 'dashboardDomainData',
    domainData: 'domainData',
    subDomainData: 'subDomainData',
    cfFacets: 'cfFacets',
    cfLastGroupId: 'cfLastGroupId',
    pfFacets: 'pfFacets',
    pfData: 'pfData',
    ffActiveId: 'ffActiveId',
    mdfaFacets: 'mdfaFacets',
    dateFilter: 'dateFilter',
}

export function getSessionStorage(key){
    return JSON.parse(sessionStorage.getItem(key))
}

