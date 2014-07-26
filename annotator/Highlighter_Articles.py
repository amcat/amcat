# -*- coding: UTF-8 -*-

import snowballstemmer
import random

class HighlighterArticles:

#input: 
#article: two-dimensional array of the article: the first dimension corresponds to the paragraph, second corresponds to sentences. 
#variable_keywords: one-dimenstional array of comma-separated keywords
#variable_pages: array of the page numbers assigned to the variables (index identical to variable_keywords).
#output: three-dimensional array: paragraph-sentence-variable, meaning that for every sentence in a paragraph we have scores \in [0,1] giving the highlighting for each variable
	def getHighlightingsArticle(self, article, variable_keywords, variable_pages):
		stemmer = snowballstemmer.stemmer("german")
		#goodchars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÄÖÜäöüß'"
		for i in range(0, len(article)):
			for j in range(0, len(article[i])):
	  			article[i][j] = article[i][j].split(" ");
				for k in range(0, len(article[i][j])):
					#article[i][j][k]=chrtran(article[i][j][k], goodchars, "")
					article[i][j][k]=stemmer.stemWord(article[i][j][k])
	

		for i in range(0, len(variable_keywords)):
			#variable_keywords[i]=chrtran(variable_keywords[i], goodchars, "")
			variable_keywords[i]=stemmer.stemWord(variable_keywords[i])
	
		highlight = []

		for i in range(0, len(article)):
			highlight_article = []

			for j in range(0, len(article[i])):
				highlight_variables = []
				for k in range(0, len(variable_keywords)):
  					highlight_variables.append(random.random())
				highlight_article.append(highlight_variables)
	
			highlight.append(highlight_article)
			


 		return highlight

#input: 
#article: two-dimensional array of the article: the first dimension corresponds to the paragraph, second corresponds to sentences. 
#variable_keywords: one-dimenstional array of comma-separated keywords
#variable_pages: array of the page numbers assigned to the variables (index identical to variable_keywords).
#output: three-dimensional array: paragraph-sentence-variables, meaning that for every sentence in a paragraph we have a score for every variable \in [0,1]
	def getHighlightingsVariables(self, article, variable_keywords, variable_pages):
		stemmer = snowballstemmer.stemmer("german")
		#goodchars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÄÖÜäöüß'"
		for i in range(0, len(article)):
			for j in range(0, len(article[i])):
  				article[i][j] = article[i][j].split(" ");
				for k in range(0, len(article[i][j])):
					#article[i][j][k]=chrtran(article[i][j][k], goodchars, "")
					article[i][j][k]=stemmer.stemWord(article[i][j][k])


		for i in range(0, len(variable_keywords)):
			#variable_keywords[i]=chrtran(variable_keywords[i], goodchars, "")
			variable_keywords[i]=stemmer.stemWord(variable_keywords[i])

		highlight = []

		for i in range(0, len(article)):
			highlight_article = []
	
			for j in range(0, len(article[i])):
				highlight_variables = []
				for k in range(0, len(variable_keywords)):
	  				highlight_variables.append(random.random())
				highlight_article.append(highlight_variables)

			highlight.append(highlight_article)
			


	 	return highlight

pass

#article=[["eins zwei"],["drei vier fünf","sechs sieben acht"]]
#variable_keywords = ["test bla bla","test test test","bla bla bla"]
#highlighter = HighlighterArticles()
#highlighting = highlighter.getHighlightingsArticle(article,variable_keywords)
#print(highlighting[0][0])
#highlighting = highlighter.getHighlightingsVariables(article,variable_keywords)
#print(highlighting[0][0][0])
