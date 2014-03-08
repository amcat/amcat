# -*- coding: UTF-8 -*-

import snowballstemmer
import random

class HighlighterArticles:

#input: 
#article: two-dimensional array of the article: the first dimension corresponds to the paragraph, second corresponds to sentences. 
#variables: one-dimenstional array of comma-separated keywords
#output: two-dimensional array: paragraph-sentence, meaning that for every sentence in a paragraph we have a single score \in [0,1] giving its highlighting
  def getHighlightingsArticle(self, article, variables):
	stemmer = snowballstemmer.stemmer("german")
	#goodchars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÄÖÜäöüß'"
	for i in range(0, len(article)):
		for j in range(0, len(article[i])):
  			article[i][j] = article[i][j].split(" ");
			for k in range(0, len(article[i][j])):
				#article[i][j][k]=chrtran(article[i][j][k], goodchars, "")
				article[i][j][k]=stemmer.stemWord(article[i][j][k])


	for i in range(0, len(variables)):
		#variables[i]=chrtran(variables[i], goodchars, "")
		variables[i]=stemmer.stemWord(variables[i])

	highlight = []

	for i in range(0, len(article)):
		highlight_article = []

		for j in range(0, len(article[i])):
  			highlight_article.append(random.random())

		highlight.append(highlight_article)
			


 	return highlight

#input: 
#article: two-dimensional array of the article: the first dimension corresponds to the paragraph, second corresponds to sentences. 
#variables: one-dimenstional array of comma-separated keywords
#output: three-dimensional array: paragraph-sentence-variables, meaning that for every sentence in a paragraph we have a score for every variable \in [0,1]
  def getHighlightingsVariables(self, article, variables):
	stemmer = snowballstemmer.stemmer("german")
	#goodchars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÄÖÜäöüß'"
	for i in range(0, len(article)):
		for j in range(0, len(article[i])):
  			article[i][j] = article[i][j].split(" ");
			for k in range(0, len(article[i][j])):
				#article[i][j][k]=chrtran(article[i][j][k], goodchars, "")
				article[i][j][k]=stemmer.stemWord(article[i][j][k])


	for i in range(0, len(variables)):
		#variables[i]=chrtran(variables[i], goodchars, "")
		variables[i]=stemmer.stemWord(variables[i])

	highlight = []

	for i in range(0, len(article)):
		highlight_article = []

		for j in range(0, len(article[i])):
			highlight_variables = []
			for k in range(0, len(variables)):
  				highlight_variables.append(random.random())
			highlight_article.append(highlight_variables)

		highlight.append(highlight_article)
			


 	return highlight

pass

#article=[["eins zwei"],["drei vier fünf","sechs sieben acht"]]
#variables = ["test bla bla","test test test","bla bla bla"]
#highlighter = HighlighterArticles()
#highlighting = highlighter.getHighlightingsArticle(article,variables)
#print(highlighting[0][0])
#highlighting = highlighter.getHighlightingsVariables(article,variables)
#print(highlighting[0][0][0])
