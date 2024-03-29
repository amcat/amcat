.STOP = c("english", "SMART", "danish", "french", "greek", "hungarian", "norwegian", "russian", "swedish", "catalan", "dutch", "finnish", "german", "italian", "portuguese", "spanish", "arabic")

formfields = djangoFormFields(max.words = IntegerField(initial=50, required=T),
                              remove.stopwords = ChoiceField(choices = c("No", .STOP)),
                              remove.query = ChoiceField(choices = c("No", "Yes")),
                              remove.words = CharField(required=F),
                              limit.window = IntegerField(required=F))

dependencies = c("RCurl", "quanteda", "corpustools", "dplyr")

run = function(max.words, remove.stopwords, remove.query, remove.words,query, limit.window=NULL, filters=NULL, ...) {
  library(quanteda)
  a = get_text(query=query, filters=filters, ...)
  print(limit.window)
  if (!is.null(limit.window)) {
    library(corpustools)
    tc = create_tcorpus(a, doc_column = "id")
    tc$subset_query(query=query, window = limit.window)
    dfm = tc$dtm(feature='token', form='quanteda_dfm')
  } else {
    dfm = dfm(paste(a$title, a$text), remove_punct=T)
  }
  if (remove.stopwords != "No") 
    dfm = dfm_remove(dfm, stopwords(remove.stopwords))
  if (remove.query == "Yes") {
    to_remove = str_remove_all(query, "[^\\p{LETTER}\\p{SPACE}*]+")
    to_remove = unlist(str_split(to_remove," "))
    dfm = dfm_remove(dfm, to_remove)
    }
if (! is.null(remove.words)) {
    to_remove = str_remove_all(remove.words, "[^\\p{LETTER}\\p{SPACE}*]+")
    to_remove = unlist(str_split(to_remove," "))
    dfm = dfm_remove(dfm, to_remove)
    }
  
  dfm=dfm_select(dfm, min_nchar = 2, pattern = "\\w+", valuetype="regex" )
  png(tf1 <- tempfile(fileext = ".png"))
  quanteda::textplot_wordcloud(dfm, max.words=max.words, colors=RColorBrewer::brewer.pal(9, "Set1"))
  dev.off()
  
  # Base64-encode file
  library(RCurl)
  txt <- base64Encode(readBin(tf1, "raw", file.info(tf1)[1, "size"]), "txt")
  html <- sprintf('<img src="data:image/png;base64,%s">', txt)
  return(html)
}


#dfm=dfm("dit is een oefening ! om speciale characters 1 ( a b te oefenen")
