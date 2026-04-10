
import json, os
from collections import defaultdict

with open("include.txt") as f:
    modules = [line.strip().split("/")[1] for line in f if line.strip()]

regions = ["ap-south-1"]
if os.path.exists("regions.txt"):
    regions = [r.strip() for r in open("regions.txt") if r.strip()]

deps = {}
if os.path.exists("dependencies.json"):
    deps = json.load(open("dependencies.json"))

changed = []
if os.path.exists("changed.txt"):
    changed = [c.strip() for c in open("changed.txt") if c.strip()]

impacted = set()
for f in changed:
    parts = f.split("/")
    if len(parts) > 1 and parts[0] == "stacks":
        impacted.add(parts[1])

if not impacted:
    impacted = set(modules)

levels = {}
def lvl(m):
    if m in levels: return levels[m]
    if not deps.get(m): levels[m]=0
    else: levels[m]=1+max(lvl(d) for d in deps[m])
    return levels[m]

for m in impacted: lvl(m)

stages = defaultdict(list)
for m in impacted:
    stages[levels[m]].append(m)

out={}
for s,mods in stages.items():
    out[f"stage_{s}"]=[
        {"path":f"stacks/{m}","module":m,"region":r}
        for m in mods for r in regions
    ]

print(json.dumps(out))
