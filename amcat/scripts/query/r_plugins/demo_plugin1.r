formfields = djangoFormFields(field1 = CharField(required=T),
                              field2 = IntegerField(initial=10, required=T))

run = function(api_token, field1, field2, ...) {
  return(paste("Hello", field1, "(", field2, ")"))
}

