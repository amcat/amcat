import re, logging

from django.db import transaction

from amcat.models import Article, AnalysisArticle, AnalysisSentence, Token, Triple, Sentence
from amcat.contrib.corenlp import StanfordCoreNLP
from amcat.tools.toolkit import stripAccents
from amcat.models.token import TokenValues, TripleValues, CoreferenceSet

log = logging.getLogger(__name__)
        
STANFORD_ANALYSIS_ID = 2

def get_text(article):
    text = u"{article.headline}\n\n{article.text}".format(**locals())
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "")
    text = stripAccents(text)
    
    #text = ". ALINEASCHEIDING. ".join(re.sub("\s+", " ", par) for par in re.split(r"\n\n+", text))
    text = re.sub("\s+", " ", text)    
    text = text.encode('ascii', 'ignore')

    if len(text) > 10000:
	text = text[:(text.find(".", 10000)+1)]
    
    return text

def get_tokenvalues(words, analysis_sentence):
    for i, info in enumerate(words):
	word = info['Text']
	pos = info['PartOfSpeech']
	poscat = POSMAP[pos]
	ner = info['NamedEntityTag']
	ner = NERMAP[ner] if ner != 'O' else None
	
	yield TokenValues(analysis_sentence.id, i, word, info['Lemma'], poscat, pos, None, ner)

def get_triplevalues(tuples, analysis_sentence):
    seen = set()
    for (relation, parent, child) in tuples:
	parent = int(parent.replace("'", ""))
	child = int(child.replace("'", ""))
	if relation == "root" and parent == 0:
	    continue
	if (child, parent) in seen: continue
	seen.add((child, parent))
	yield TripleValues(analysis_sentence.id, child-1, parent-1, relation)
		
@transaction.commit_on_success
def do_parse(nlp, article):
    text = get_text(article)
    sents, coref = nlp.parse(text)

    # create analysis article
    aa = AnalysisArticle.objects.create(article=article, analysis_id=STANFORD_ANALYSIS_ID)

    
    sentences = {} # for coref, asent.id -> stanford sent no
    tokenvalues, triplevalues = [], []
    for sent_no, sent in enumerate(sents, start=1):
        # create sentence
        sentence = Sentence.objects.create(article=article, parnr=2, sentnr=sent_no, sentence=sent["text"])
        asent = AnalysisSentence.objects.create(analysis_article=aa, sentence=sentence)
	sentences[asent.id] = sent_no
	
	tokenvalues += list(get_tokenvalues(sent["words"], asent))
	triplevalues += list(get_triplevalues(sent["tuples"], asent))

    # store tokens, triples
    tokens, triples = aa.do_store_analysis(tokenvalues, triplevalues)

    # create mapping of (stanford) sentence no + word no -> token for coreference
    token_map = {(sentences[tv.analysis_sentence], tv.position + 1) : token
		 for (tv, token) in tokens.iteritems()}

    store_coreference(coref, token_map, aa)

def store_coreference(coref, token_map, analysis_article):
    for corefset in coref:
	tokenset = set()
	seen = set()

	for pair in corefset:
	    for (sentence, position, _start, _end) in pair:
		tokenset.add(token_map[sentence, position])

	if len(tokenset) > 1:
	    s = CoreferenceSet(analysis_article = analysis_article)
	    s.save()
	    s.tokens.add(*tokenset)
		

POSMAP = {
   '$' :'.',
   '#' :'.',
   '"' :'.',
    "'" :'.',
   '``' : '.',
   "''" : '.',
   '(' :'.',
   ')' :'.',
   '-LRB-' : '.',
   '-RRB-' : '.',
   ',' :'.',
   '--' :'.',
   '.' :'.',
   ':' :'.',
   'CC' :'C',
   'CD' :'Q',
   'DT' :'D',
   'EX' :'R',
   'FW' :'?',
   'IN' :'P',
   'JJ' :'A',
   'JJR' :'A',
   'JJS' :'A',
   'LS' :'Q',
   'MD' :'V',
   'NN' :'N',
   'NNP' :'N',
   'NNPS' :'N',
   'NNS' :'N',
   'PDT' :'D',
   'POS' :'O',
   'PRP' :'O',
   'PRP$' :'O',
   'RB' :'B',
   'RBR' :'B',
   'RBS' :'B',
   'RP' :'R',
   'SYM' :'.',
   'TO' :'R',
   'UH' :'I',
   'VB' :'V',
   'VBD' :'V',
   'VBG' :'V',
   'VBN' :'V',
   'VBP' :'V',
   'VBZ' :'V',
   'WDT' :'D',
   'WP' :'O',
   'WP$' :'O',
   'WRB' :'B',
    }

NERMAP = {
    'LOCATION' : 'L',
    'ORGANIZATION' : 'O',
    'PERSON' : 'P',
    'DATE' : 'D',
    'DURATION' : 'D',
    'TIME' : 'D',
    'NUMBER' : '#',
    'ORDINAL' : '#',
    'MISC' : '?',
    'MONEY' : '#',
    'SET' : '#',
    'PERCENT' : '#',
    }


if __name__ == '__main__':
    from amcat.tools import amcatlogging
    amcatlogging.setup()
    amcatlogging.info_module("amcat.contrib.corenlp")

    from amcat.models import ArticleSet
    
    nlp = StanfordCoreNLP(corenlp_path="/home/amcat/resources/stanford-corenlp", models_version="2012-07-06")

    import sys
    if len(sys.argv) > 1:
	aids = map(int, sys.argv[1:])
	delete_existing = True
	amcatlogging.debug_module("amcat.contrib.corenlp")
    else:
	s = ArticleSet.objects.get(pk=22947)
	aids = [aid for (aid,) in s.articles.values_list("id")]
	delete_existing = False

    for aid in aids:
	try:
	    log.info("Parsing article %i" % aid)
	    if AnalysisArticle.objects.filter(article_id=aid, analysis_id=STANFORD_ANALYSIS_ID).count():
		if delete_existing:
		    log.info("Deleting existing analysed article")
		    aa = AnalysisArticle.objects.get(article_id=aid, analysis_id=STANFORD_ANALYSIS_ID)
		    super(AnalysisArticle, aa).delete()
		else:
		    log.info("Skipping due to existing analysed article")
		    continue

	    a = Article.objects.get(pk=aid)
	    do_parse(nlp, a)
	except Exception, e:
	    log.exception("Error on parsing %i; restarting server" % aid)
	    nlp = StanfordCoreNLP(corenlp_path="/home/amcat/resources/stanford-corenlp", models_version="2012-07-06")
	    
	    
