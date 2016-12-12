import json
arts = json.load(open("test_body_sols.json"))
res = []
for art in arts:
    title, byline, text, date, medium, meta = art
    art = dict(title=title, byline=byline, text=text, date=date, medium=medium, **meta)
    art = {k: v for (k,v) in art.items() if v and v.strip()}
    res.append(art)

print(json.dumps(res, indent=4))