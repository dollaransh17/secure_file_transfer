"""Independent specification: no application imports, no observed verdict inputs.
An oracle consumes scenario facts, never the gateway's result.
"""
from dataclasses import dataclass,field
@dataclass
class Oracle:
    current:int=1
    permission:bool=True
    tenant_match:bool=True
    epoch:int=1
    valid_until:float=100
    digests:dict=field(default_factory=lambda:{1:'a'})
    clean_versions:dict=field(default_factory=lambda:{1:(1,'a')})
    def permits(self,requested,at):
        if not self.permission or not self.tenant_match or requested!=self.current or at>=self.valid_until: return False
        return self.clean_versions.get(requested)==(self.epoch,self.digests.get(requested))

def scenario(name):
    o=Oracle();requested=1;at=10
    if name in ('new_version_pending','delayed_scan','out_of_order','concurrent_versions'):
        o.current=2;o.digests[2]='b';requested=2
    elif name=='revocation': o.permission=False
    elif name=='cross_tenant': o.tenant_match=False
    elif name in ('expiry','starvation'): at=101
    elif name in ('policy_change','late_policy_result'): o.epoch=2
    elif name=='integrity_mismatch': o.digests[1]='tampered'
    elif name in ('scanner_timeout','worker_crash','unsupported','retry_exhaustion'): o.clean_versions={}
    return o,requested,at
