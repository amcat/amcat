formfields = djangoFormFields(field1 = CharField(required=T),
                              field2 = IntegerField(initial=10, required=T))

run = function(field1, field2, ...) {
  print(list(...))
  return(paste("Hallo ", field1, "(", field2, ")"))
}

