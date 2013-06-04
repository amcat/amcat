import sys

from amcat.models import CodingSchema, Codebook, Project, Code, Language, CodingSchemaField, CodingSchemaFieldType
from django.conf import settings

def copy_codebook(source_cb, target_project):

    print "Moving {source_cb} to {target_project}".format(**locals())
    target_cb = Codebook.objects.create(project=target_project, name=source_cb.name)
    print "Created codebook", target_cb

    codes = {} # uuid -> new code
    # create codes
    for code in source_cb.codebookcodes.all():
        uuid = code.code.uuid

        if uuid in codes:
            continue
        try:
            target_code = Code.objects.get(uuid=uuid)
        except Code.DoesNotExist:
            target_code = Code.objects.create(uuid=uuid)
            print "Created code ", uuid
            for label in code.code.labels.all():
                l = Language.objects.get(label=label.language.label)
                target_code.add_label(Language.objects.get(label=label.language.label), label.label)
                
        codes[uuid] = target_code

    # add to codebook

    for cc in source_cb.codebookcodes.all():
        c = codes[cc.code.uuid]
        p = None if cc.parent_id is None else codes[cc.parent.uuid]
        target_cb.add_code(c, p)
        
    return target_cb


def copy_codingschema(source_schema, target_project):
    print "Moving {source_schema} to {target_project}".format(**locals())

    attrs = {k : getattr(source_schema, k)
             for k in ["name","description","isnet","isarticleschema", "quasisentences"]}
    
    target_schema = CodingSchema.objects.create(project=target_project, **attrs)

    print "Created schema", target_schema.id

    # create fields
    codebooks = {} # old id : new codebook
    for field in source_schema.fields.all():
        cb = codebooks.get(field.codebook_id)
        if field.codebook_id and not cb:
            if field.codebook_id == -5001:
                continue
            cb = copy_codebook(field.codebook, target_project)
            print "Copied codebook ", field.codebook_id, ":",field.codebook.name, " to ", cb.id
            codebooks[field.codebook_id] = cb


        attrs = {k : getattr(field, k)
                 for k in ["fieldnr", "label", "required", "default"]}

        fieldtype = 1 if field.codebook_id == -5001 else field.fieldtype_id

        CodingSchemaField.objects.create(codingschema=target_schema, codebook=cb, fieldtype_id=fieldtype, **attrs)

if __name__ == '__main__':
    settings.DATABASES["source"] = dict(settings.DATABASES['default'].items())
    #settings.DATABASES["source"]['HOST']='amcatdb'
    settings.DATABASES["source"]['NAME']='amcat'

    target_project = Project.objects.get(pk=int(sys.argv[1]))
    
    source_schema = CodingSchema.objects.using('source').get(pk=int(sys.argv[2]))
    copy_codingschema(source_schema, target_project)
    
    #source = Codebook.objects.using('source').get(pk=int(sys.argv[2]))
    #copy_codebook(source, target_project)

