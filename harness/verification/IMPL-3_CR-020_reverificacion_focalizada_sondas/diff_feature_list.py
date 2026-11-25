import json,sys
def load(p): return json.load(open(p))
a,b=load(sys.argv[1]),load(sys.argv[2])
fa={f["id"]:f for f in a["features"]}; fb={f["id"]:f for f in b["features"]}
print("ids equal:", fa.keys()==fb.keys())
for k in fa:
    x,y=fa[k],fb[k]
    for fld in ("status","acceptance_criteria","acceptance_criteria_status"):
        if x.get(fld)!=y.get(fld): print("DIFF",k,fld)
    if (x.get("evidence") or {}).get("covered")!=(y.get("evidence") or {}).get("covered"): print("DIFF",k,"evidence.covered")
    if k!="FEAT-017" and x!=y: print("DIFF other FEAT",k)
    if k=="FEAT-017":
        ks=set(x)|set(y); print("FEAT-017 changed top keys:",[q for q in ks if x.get(q)!=y.get(q)])
        ev=set(x["evidence"])|set(y["evidence"]); print("FEAT-017 changed evidence keys:",[q for q in ev if x["evidence"].get(q)!=y["evidence"].get(q)])
print("meta diff:",{q:(a["metadata"].get(q),b["metadata"].get(q)) for q in set(a["metadata"])|set(b["metadata"]) if a["metadata"].get(q)!=b["metadata"].get(q)})
print("other top-level diff:",[q for q in set(a)|set(b) if q not in("features","metadata") and a.get(q)!=b.get(q)])
