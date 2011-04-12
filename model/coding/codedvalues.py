class CodedValues(object):
    """Superclass for CodedSentence and CodedArticle to contain modification logic"""
    
    __slots__ = ()

    def updateValues(self, db, values):
        """Update this CodedValues object to the given values.
        Assume that values is complete, eg don't combine with existing values
        
        Steps:
        1. Validate the given values
        2. Serialise the given values
        3. Update the database and invalidate the cache

        @param db: A db connection with which the transaction is run
        @param values: A dict of AnnotationSchemaField : Deserialised Value Objects
        @raise ValidationError: If the given values were not valid
        """
        # Step 1: validate
        schema = self.annotationschema
        schema.validate(values)

        # Step 2: serialize fields:value objects to fieldname:valuestring
        svalues = dict((f.fieldname, f.serializer.serialize(v)) for (f,v) in values.items())

        # Step 3: update and invalidate
        idcol = "codingjob_articleid" if schema.isarticleschema else "codedsentenceid"
        table = schema.table
        if table.lower() == "vw_net_arrows": table = "net_arrows" #HACK, remove after migrating to amcat3
        if table == "net_arrows": idcol = "arrowid" #HACK, remove after migrating!
        db.update(table, svalues, {idcol: self.id})
        
        del self.values
    
