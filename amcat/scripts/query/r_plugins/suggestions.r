formfields = djangoFormFields(n = IntegerField(initial=50, required=T))


run = function(query, n, ...) {
  depends("corpustools", "knitr")
  a = get_text(...)
  library(corpustools)
  tc = create_tcorpus(a, doc_column = "id")
  ass = tc$feature_associations(query=query)
  result = knitr::kable(head(ass, n=n), format="html", digits=2, row.names=F)
  return(as.character(result))
}
