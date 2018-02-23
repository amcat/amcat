.STOP = c("english", "SMART", "danish", "french", "greek", "hungarian", "norwegian", "russian", "swedish", "catalan", "dutch", "finnish", "german", "italian", "portuguese", "spanish", "arabic")

formfields = djangoFormFields(max.words = IntegerField(initial=50, required=T),
                              remove.stopwords = ChoiceField(choices = c("No", .STOP)))


run = function(max.words, remove.stopwords, ...) {
  depends("RCurl", "quanteda", "dplyr")
  library(quanteda)
  a = get_text(...)
  dfm = dfm(paste(a$headline, a$text), remove_punct=T)
  if (remove.stopwords != "No") 
    dfm = dfm_remove(dfm, stopwords(remove.stopwords))
  
  png(tf1 <- tempfile(fileext = ".png"))
  quanteda::textplot_wordcloud(dfm, max.words=max.words)
  dev.off()
  
  # Base64-encode file
  library(RCurl)
  txt <- base64Encode(readBin(tf1, "raw", file.info(tf1)[1, "size"]), "txt")
  html <- sprintf('<img src="data:image/png;base64,%s">', txt)
  return(html)
}
