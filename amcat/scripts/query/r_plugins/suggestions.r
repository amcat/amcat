formfields = djangoFormFields(n = IntegerField(initial=50, required=T))
dependencies = c("corpustools", "knitr")

run = function(query, n, ...) {
  a = get_text(...)
  library(corpustools)
  tc = create_tcorpus(a, doc_column = "id")
  ass = tc$feature_associations(query=query)
  result = knitr::kable(head(ass, n=n), format="html", digits=2, row.names=F)
  return(as.character(result))
}
