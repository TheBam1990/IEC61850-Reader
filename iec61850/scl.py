from __future__ import annotations
from pathlib import Path
import xml.etree.ElementTree as ET
from .backend import ModelItem

def load_scl(path: str | Path) -> list[ModelItem]:
    root=ET.parse(path).getroot(); result=[]
    for ied in root.iter():
        if ied.tag.rsplit("}",1)[-1] != "IED": continue
        ied_name=ied.get("name","")
        for node in ied.iter():
            tag=node.tag.rsplit("}",1)[-1]
            if tag == "LDevice":
                ld=f"{ied_name}{node.get('inst','')}"; result.append(ModelItem("LD",ld))
                for ln in node:
                    ltag=ln.tag.rsplit("}",1)[-1]
                    if ltag in ("LN","LN0"):
                        name=f"{ln.get('prefix','')}{ln.get('lnClass','LLN0')}{ln.get('inst','')}"
                        result.append(ModelItem("LN",f"{ld}/{name}"))
    return result
