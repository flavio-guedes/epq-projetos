import os, json, urllib.parse
from pathlib import Path
from PIL import Image

ROOT = Path("/Users/mac/epq-next/epq-projetos/assets/images")
OUT = Path("/Users/mac/epq-next/epq-projetos/images/index.json")

def scan():
    out=[]
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in [".png",".jpg",".jpeg",".webp"]:
            continue
        try:
            with Image.open(p) as img:
                w,h=img.size
            out.append({
                "filename": p.name,
                "url": f"/images/{p.name}",
                "path": str(p),
                "size_bytes": p.stat().st_size,
                "width": w,
                "height": h,
                "ratio": round(w/h,2),
                "provider":"unknown","model":"unknown","aspect":f"{w}:{h}","created_at":p.stat().st_mtime
            })
        except Exception:
            continue
    return sorted(out, key=lambda x: x.get("created_at",0), reverse=True)

def enrich(items):
    log = Path("/Users/mac/HermesWorkspace/outputs/logs/imagegen.log")
    logs=[]
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            line=line.strip()
            if not line: continue
            try: logs.append(json.loads(line))
            except: pass
    by_name={}
    for e in logs:
        p = ((e.get("payload") or {}).get("path") or "")
        if p: by_name[Path(p).name] = e.get("payload") or {}

    for it in items:
        meta=by_name.get(it["filename"],{})
        it.setdefault("original_prompt", meta.get("original_prompt"))
        it.setdefault("enhanced_prompt", meta.get("enhanced_prompt"))
        it.setdefault("provider", meta.get("provider", it.get("provider")))
        it.setdefault("model", meta.get("model", it.get("model")))
        it.setdefault("aspect", meta.get("aspect", it.get("aspect")))
        it.setdefault("status","ok" if Path(it["path"]).exists() else "missing")
    return items

def handler():
    qs = os.environ.get("QUERY_STRING","")
    params=urllib.parse.parse_qs(qs)
    params={k:(v[0] if v else "") for k,v in params.items()}
    items=scan()
    q=(params.get("q") or "").strip().lower()
    if q:
        blob=lambda it: " ".join(filter(None,[it.get("filename",""),it.get("original_prompt","") or "",it.get("provider","") or "",it.get("model","") or "",it.get("aspect","") or ""])).lower()
        items=[it for it in items if q in blob(it)]
    provider=(params.get("provider") or "").strip().lower()
    if provider:
        items=[it for it in items if (it.get("provider") or "").lower()==provider]
    aspect=(params.get("aspect") or "").strip()
    if aspect:
        items=[it for it in items if it.get("aspect")==aspect]
    page=max(1,int(params.get("page") or 1)); per_page=max(1,int(params.get("per_page") or 30))
    total=len(items); start=(page-1)*per_page; end=start+per_page
    body={"items":items[start:end],"total":total,"page":page,"per_page":per_page,"pages":(total+per_page-1)//per_page if per_page else 1}
    payload=json.dumps(body, ensure_ascii=False).encode("utf-8")
    OUT.write_text(payload.decode("utf-8"), encoding="utf-8")
    print("Content-Type: application/json")
    print("Access-Control-Allow-Origin: *")
    print(f"Content-Length: {len(payload)}")
    print()
    print(payload.decode("utf-8"))

if __name__ == "__main__":
    handler()
