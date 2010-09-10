import dbtoolkit, ont2, categorise

db = dbtoolkit.amcatDB()
ont=  ont2.fromDB(db)

db.doQuery("truncate table o_objects_categorisations")

for catid, cat in ont.getCategorisations().items():
    for o in ont.nodes.values():
        (cl, clo), (r, ro), (c, co) = o.categorise(cat)
        if cl is None: continue
        db.insert("o_objects_categorisations", dict(
                categorisationid = catid,
                objectid = o.id,
                classid = cl.id,
                root_objectid  = r.id,
                rootomklap = ro == -1,
                cat_objectid = c.id,
                catomklap = co == -1,
                ))

db.conn.commit()
