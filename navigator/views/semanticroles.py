import logging
import csv
import os.path
import collections
from functools import partial
from random import randint

from django.core.urlresolvers import reverse
from django.shortcuts import render

from navigator.utils.auth import check
from amcat.tools.table import table3, tableoutput
from amcat.tools.pysoh import  fuseki, SOHServer
from amcat.nlp.treetransformer import TreeTransformer, visualise_triples, Triple, AMCAT
from amcat.nlp.statementextraction import get_statements, Statement, fill_out

log = logging.getLogger(__name__)


from amcat.models import AnalysisSentence


_csvdir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../media/misc"))
LEXICONFILE = os.path.join(_csvdir, "lexicon{ruleset}.csv")
GRAMMARFILE = os.path.join(_csvdir, "rules{ruleset}.csv")
GOLDFILE = os.path.join(_csvdir, "gold_quotes.csv")

def get_tt(ruleset="", gold_relations=None):
    #TODO: find a way to open a new data set on an existing fuseki instance
    #port = randint(10000, 60000)
    #soh = fuseki.Fuseki(port=port)
    soh = SOHServer(url="http://localhost:3030/x")
    grammarfile = GRAMMARFILE.format(**locals())
    lexiconfile = LEXICONFILE.format(**locals())
    return TreeTransformer(soh, lexiconfile, grammarfile, gold_relations)

def colorize(diff):
    if diff > 0:
        return "<span style='background: #0f0'>%1.2f</span>" % diff
    elif diff < 0:
        return "<span style='background: #f66'>%1.2f</span>" % diff
    return diff
    
def index(request):
    # build table with gold standard sentences
    ruleset = request.GET.get('ruleset', '').lower()
    if ruleset: ruleset = "_" + ruleset

    goldfile = GOLDFILE.format(**locals())
    grammarfile = GRAMMARFILE.format(**locals())
    g, gold_relations =get_gold(goldfile)
    comments = get_gold_comments(goldfile)

    # if rules are modified, store current values
    grammar_modified = os.path.getmtime(grammarfile)
    store_score = request.session.get('grammartime', None) != grammar_modified
    request.session['grammartime'] = grammar_modified

    sentences = AnalysisSentence.objects.filter(pk__in=g.keys())

    metrics = {} # (sid, "tp"/"fn"/"fp") : score
    tt = get_tt(ruleset, gold_relations)
    for sentence in sentences:
        tt.load_sentence(sentence.id)
        tt.apply_lexical()
        tt.apply_rules()


        found = set(tt.get_roles())
        print "--->", found
        gold = g[sentence.id]
        gold = set(do_gold_reality(found, gold))
        tp = len(gold & found)
        fp = len(found - gold)
        fn = len(gold - found)
        pr = tp / float(tp + fp) if (tp + fp) else None
        re = tp / float(tp + fn) if (tp + fn) else None
        f = 2 * pr * re / (pr + re) if (pr or re) else 0
        if tp + fp + fn == 0: f = None
        for metric in "tp fp fn pr re f".split():
            metrics[sentence.id, metric] = locals()[metric]
        key = "semanticroles_fscore_%i" % sentence.id
        previous = request.session.get(key, None)
        metrics[sentence.id, "prev"] = "" if previous is None else previous
        metrics[sentence.id, "diff"] = "" if previous is None else colorize((f or 0) - previous)
        if store_score:
            request.session[key] = f

	    
	    

    sentencetable = table3.ObjectTable(rows=sentences)
    sentencetable.addColumn(lambda s : "<a href='{url}?ruleset={ruleset}'>{s.id}</a>".format(url=reverse('semanticroles-sentence', args=[s.id]), ruleset=ruleset[1:], s=s), "ID")
    sentencetable.addColumn(lambda s : unicode(s.sentence.sentence)[:60], "Sentence")
    sentencetable.addColumn(lambda s : "<br/>".join(comments.get(s.id, [])), "Remarks")
    def get_metric(metric, sentence):
        
        result = metrics[sentence.id, metric]
        if result is None: result = ""
        if isinstance(result, float): result = "%1.2f" % result
        return result
    for metric in ("tp","fp","fn", "f", "prev", "diff"):
        sentencetable.addColumn(partial(get_metric, metric), metric)

    sentencetablehtml = tableoutput.table2htmlDjango(sentencetable, safe=True)
   
    print grammar_modified, store_score
    
    return render(request, "navigator/semanticroles/index.html", locals())

@check(AnalysisSentence)
def sentence(request, analysis_sentence):
    donukes = request.GET.get('donukes', 'n')[0].lower() == 'y'
    ruleset = request.GET.get('ruleset', '').lower()
    statements_without_object = ruleset == "en"
    if ruleset: ruleset = "_" + ruleset

    goldfile = GOLDFILE.format(**locals())
    grammarfile = GRAMMARFILE.format(**locals())
    lexiconfile = LEXICONFILE.format(**locals())
    
    tt = get_tt(ruleset)
    log.info("Loading syntax graph for sentence {analysis_sentence.id}".format(**locals()))
    tt.load_sentence(analysis_sentence.id)

    graphs = []
    graphs += [("raw", "Raw syntax graph", get_graph(tt))]
    tt.apply_lexical()
    graphs += [("lex", "After lexical processing", get_graph(tt))]
    
    graphs += apply_rules(tt)
    
    graphs += check_gold(goldfile, analysis_sentence.id, tt)

    nuketable = get_nukes(analysis_sentence, tt, statements_without_object)
    nuketable = tableoutput.table2htmlDjango(nuketable)

    lexfn, grammarfn, goldfn = lexiconfile, grammarfile, goldfile # into locals
    return render(request, "navigator/semanticroles/sentence.html", locals())



def get_graph(transformer):
    g = visualise_triples(transformer.get_triples())
    print(g.getDot())
    return g.getHTMLObject()

def grey_rel(triple):
    if "rel_" in triple.predicate:
        return dict(color="grey")
    return {}

def apply_rules(transformer):
    for rule in transformer.rules:
        log.info(u".. {}".format(rule.name))
        rule.apply(transformer)
        if rule.show:
            g = visualise_triples(transformer.get_triples(), grey_rel)
            yield (rule.name, "After rule: "+rule.name, g.getHTMLObject())

### Gold standard logic ###

class NoGoldFound(Exception): pass

def gold_colors(gold, gold_relations, triple):
    if triple.predicate not in gold_relations: return dict(color="grey")
    triple = Triple(int(triple.subject.position), triple.predicate, int(triple.object.position))
    if triple in gold: return dict(color="green")
    return dict(color="red")

def get_gold(goldfile):
    gold = collections.defaultdict(set)
    f = open(goldfile)
    gold_relations = csv.reader(f).next()
    for line in  csv.DictReader(f):
        triples = gold[int(line["id"])]
        if line["subject"] != "-" and line["rel"]: # marker to allow for empty set gold standard
            triples.add(Triple(int(line["subject"]), line["rel"], int(line["object"])))
    return gold, gold_relations

def get_gold_comments(goldfile):
    comments = collections.defaultdict(list)
    f = open(goldfile)
    csv.reader(f).next()
    for line in  csv.DictReader(f):
        comment = line["remarks"]
        if comment and comment.strip():
            comments[int(line["id"])].append(comment.strip())
    return comments

def do_gold_reality(found, gold):
    """Yield the triples in gold, changing -1 Y Z into -N Y Z if the latter is in found"""
    rea = dict(((p,o), s) for (s, p, o) in found if s<0)
    print rea
    for s, p, o in gold:
        if s == -1:
            print "XXX", s, p, o, (p,o) in rea, rea.get((p,o))
            if (p,o) in rea:
                s = rea[p, o]
        yield Triple(s, p, o)

def check_gold(goldfile, sid, transformer):
    gold, gold_relations = get_gold(goldfile)
    if sid not in gold: return
    gold = gold[sid]
    log.info("Comparing with gold standard")
    triples = transformer.get_triples()
    found = set(Triple(int(t.subject.position), t.predicate, int(t.object.position))
        for t in triples if t.predicate in gold_relations)
    gold = set(do_gold_reality(found, gold))
    
    g = visualise_triples(triples, partial(gold_colors, gold, gold_relations))
    for t in gold - found: # add false negatives
        g.addEdge("node_%i" % t.subject, "node_%i" % t.object, label=t.predicate, color="orange")
    yield"Gold", "Gold Standard", g.getHTMLObject()

def resolve_equivalence(statements):
    equivalences = collections.defaultdict(set)
    for s in statements:
        if  "Equivalent" in s.type:
            nodes = s.subject | s.object
            for node in nodes:
                equivalences[node] |= nodes
            yield Statement(s.sentence, s.object, s.predicate, s.subject, type=s.type)
    for s in statements:
        if  "Equivalent" not in s.type:
            for place in ["source", "subject", "predicate", "object"]:
                nodes = set(getattr(s, place))
                for node in set(getattr(s, place)):
                    if node in equivalences:
                        setattr(s, place, getattr(s,place) | equivalences[node])
        yield s
    
def get_nukes(sentence, transformer, statements_without_object):
    """Return a sequence of statements extracted from the roles"""
    read_node = lambda n : int(n) if n.strip() else None
    roles = [(read_node(s), p.replace(AMCAT, ""), read_node(o)) for (s,p,o) in 
             transformer.query(select=["?spos", "?p", "?opos"],
                               where="""?s ?p [:position ?opos] OPTIONAL {?s :position ?spos}
                                        FILTER (?p IN (:su, :obj, :quote, :eqv,  :om))""")] 

    statements = list(get_statements(sentence, roles, statements_without_object))
    statements = [fill_out_statement(sentence, statement, roles) for statement in statements]
    statements = list(resolve_equivalence(statements))
    statements = [add_frames(s) for s in statements]
	
    nuketable = table3.ObjectTable(rows = statements)

    nuketable.addColumn(lambda s : "/".join(s.type), "type")
    for col in "source", "subject", "predicate", "condition", "object":
        nuketable.addColumn(partial(Statement.get_lemmata, position=col), col)
    nuketable.addColumn(lambda s : s.frames, "frames")

    return nuketable

def add_coreferents(nodes):
    for node in nodes:
        yield node
        #print " --> ", node
        if node is None: return
        for cs in node.coreferencesets.all():
            #print "   #", cs.id
            for n2 in cs.tokens.all():
                #print "    ###" ,n2
                yield n2

def fill_out_statement(sentence, statement, roles):
    for col in "source", "subject", "predicate", "condition", "object":
	nodes = fill_out(sentence, getattr(statement, col), roles)
        nodes = set(add_coreferents(nodes))
	setattr(statement, col, nodes)
    return statement

def has_single_lemma(nodes, lemma):
    for node in nodes:
        if node is None: continue
	l = node.word.lemma.lemma.lower()
	if l.startswith(lemma):
	    return True
	    
def has_lemma(nodes, lemmata):
    for lemma in lemmata:
	if type(lemma) != tuple: lemma = (lemma, )
	if all(has_single_lemma(nodes, l) for l in lemma):
	    return True



ATTACK = ["shoot", "attack", "kill", "fire", "strike", "raid", "offensive", "aggression", "fight",
          "munition", "violence", "assault", "shell", "target", ('military','pressure'), "unleash", "bomb",
          "invasion", "battle", "hit", "pummel", "killer", "operation", "blow"]
HAMAS = ["hamas", ("palestinian", "terrorist")]
ISRAEL = ["israel", "zionist", "tank", "helicopter", "jewish", "idf", "olmert"]
ANTIISRAEL = ["anti-israel"]
AIRSTRIKE = [("air", "strike"), "aerial"]
CIVILIAN = ["civilian", "village", "town", "home", "resident", "woman", "child", "innocent", "citizen", "un", "convoy", "humanit"]
ISRAELI = ["israeli"]
PALEST = ["gaza", "palest"]
PALESTINIANS = ["palestinian"]
TERROR = ["terror"]
THREAT = ["threat", "rearm"]
AGRESSOR = ["disproportion", "agressor", "genocide", "oppress", "atrocity", "savage", "savagery", "aggression", "aggressive", "brutal", "brutality", "massacre"]
STOP = ["stop", "cease", "end", "halt", "prevent", "reduce", "renounce", "eliminate", "stem", "monitor"]
OCCUPY = ["occupy", "blockade", "confiscate", "occupation"]
CEASEFIRE = ["ceasefire", ("cease", "fire"), "truce", "cease-fire", "peace", "compromise", "diplomat"]
RECOGNIZE = ["recognize", "recognise", "recognition"]
BOYCOT = ["boycot", "embargo"]
SMUGGLE = ["smuggl", "acquir", "obtain"]
WEAPONS = ["weapon", "rockets", "explosive", "missile"]
ROCKET = ["rocket", "missile", "mortar"]
DEMONSTRATION = ["demonstration", "protest"]
DIE = ["die", "casualty"]
PROTECT = ["protect"]

def add_frames(nuke):
    nuke.frames = set()
    
    if "Equivalent" in nuke.type:
	predobj = nuke.subject | nuke.object
    else:
	predobj = nuke.predicate | nuke.object
    supredobj = nuke.predicate | nuke.object | nuke.subject


    if has_lemma(supredobj, CEASEFIRE):
	nuke.frames.add("6_CEASEFIRE")
        #if has_lemma(predobj, CEASEFIRE) and not has_lemma(predobj, STOP):
	#nuke.frames.add("6_CEASEFIRE") # makes it worsE!
        
    if has_lemma(nuke.predicate, ["not"]):
        return nuke # is this wise?
    
    if has_lemma(nuke.subject, HAMAS) and has_lemma(predobj, ATTACK) and has_lemma(predobj, CIVILIAN):
	nuke.frames.add("1_HAMAS_IS_PROBLEM_KILL_CIVILIANS")
    elif has_lemma(supredobj, ATTACK) and has_lemma(supredobj, ROCKET) and has_lemma(supredobj, ISRAEL):
	if has_lemma(predobj, STOP):
	    nuke.frames.add("4_SOLUTION_STOP_ROCKETSa")
        nuke.frames.add("1_HAMAS_IS_PROBLEM_SOMEON_FIRES_ROCKETS_AT_ISRAEL")
    if has_lemma(supredobj, HAMAS) and has_lemma(supredobj, ROCKET):
        if has_lemma(predobj, STOP):
	    nuke.frames.add("4_SOLUTION_STOP_ROCKETSb")
        nuke.frames.add("1_HAMAS_IS_PROBLEM_FIRES_ROCKETS")
    if has_lemma(nuke.predicate, ATTACK) and has_lemma(nuke.object, ISRAELI):
	nuke.frames.add("1_HAMAS_IS_PROBLEM_SOMEONE_KILLS_ISRAELI")
    if ((has_lemma(nuke.subject, PALEST) or has_lemma(nuke.subject, HAMAS))
        and has_lemma(predobj, SMUGGLE) and has_lemma(predobj, WEAPONS)):
	if has_lemma(predobj, STOP):
	    nuke.frames.add("4_SOLUTION_STOP_SMUGGLING")
        nuke.frames.add("1_HAMAS_IS_PROBLEM_SMUGGLE")
    if has_lemma(nuke.subject, ISRAEL) and has_lemma(predobj, OCCUPY):# and has_lemma(predobj, PALEST):
	nuke.frames.add("2_ISRAEL_IS_PROBLEM_OCCUPY")
    if has_lemma(nuke.subject, ISRAEL) and has_lemma(predobj, ATTACK) and not has_lemma(supredobj, ROCKET):
	nuke.frames.add("3_ISRAEL_ATTACKS")
    if has_lemma(predobj, ISRAEL) and has_lemma(predobj, ATTACK) and not has_lemma(supredobj, ROCKET)  and not has_lemma(supredobj, HAMAS) :
	nuke.frames.add("3_ISRAEL_ATTACKS_OBJ")
    if has_lemma(supredobj, AIRSTRIKE):
        nuke.frames.add("3_AIR_STRIKE")
    if has_lemma(predobj, ISRAEL) and has_lemma(predobj, BOYCOT):
	nuke.frames.add("5_SOLUTION_BOYCOTT_ISRAEL")

    if has_lemma(predobj, STOP) and has_lemma(predobj, ROCKET):
        nuke.frames.add("4_SOLUTION_STOP_ROCKETSc")
        nuke.frames.add("1_HAMAS_IS_PROBLEM_ROCKETS_ARE_FIRED")
    elif has_lemma(predobj, STOP) and has_lemma(predobj, ATTACK):
        if has_lemma(nuke.subject, HAMAS) or has_lemma(predobj, HAMAS):
            nuke.frames.add("4_SOLUTION_HAMAS_STOP_VIOLENCE")
        elif has_lemma(nuke.subject, ISRAEL) or has_lemma(predobj, ISRAEL):
            if not has_lemma(predobj, ROCKET):
                nuke.frames.add("6_ISRAEL_SHOULD_STOP")
        else:
            nuke.frames.add("6_FIGHTING_SHOULD_STOP")
                                          
    if has_lemma(predobj, DEMONSTRATION) and (has_lemma(predobj, ISRAEL) or has_lemma(predobj, ANTIISRAEL)):
        nuke.frames.add("5_DEMONSTRATION")
        
    if has_lemma(nuke.subject, HAMAS) and has_lemma(predobj, TERROR):
	nuke.frames.add("7_HAMAS_IS_EVIL")
    if has_lemma(supredobj, ISRAEL) and has_lemma(predobj, AGRESSOR):
	nuke.frames.add("8_ISRAEL_IS_EVIL")

        
    if has_lemma(nuke.subject, ISRAEL) and has_lemma(predobj, ATTACK) and has_lemma(predobj, CIVILIAN):# and has_lemma(predobj, PALEST):
	nuke.frames.add("2_ISRAEL_IS_PROBLEM_KILL_CIVILIANS")
    elif has_lemma(predobj, ATTACK) and has_lemma(predobj, PALESTINIANS) and not has_lemma(supredobj, HAMAS):
	nuke.frames.add("2_ISRAEL_IS_PROBLEM_SOMEONE_KILLS_PALESTINIANS")

        
    if has_lemma(nuke.subject, CIVILIAN) and has_lemma(predobj, DIE) and has_lemma(nuke.subject, PALESTINIANS):
        nuke.frames.add("2_ISRAEL_IS_PROBLEM_PALESTINIANS_DIE")
    elif has_lemma(supredobj, CIVILIAN) and (has_lemma(supredobj, DIE) or has_lemma(supredobj, ATTACK)) and not (
        has_lemma(supredobj, ISRAEL) or has_lemma(supredobj, HAMAS)):
        #civilian casualties, but whose fault?
        tokens = set(nuke.sentence.tokens.all())
        if has_lemma(tokens, ISRAEL) and not has_lemma(tokens, HAMAS):
            nuke.frames.add("2_ISRAEL_IS_PROBLEM_LETS_CIVILIANS_DIE")
        elif has_lemma(tokens, HAMAS) and not has_lemma(tokens, ISRAEL):
            nuke.frames.add("1_HAMAS_IS_PROBLEM_LETS_CIVILIANS_DIE")
        
    if has_lemma(predobj, TERROR) and has_lemma(predobj, ATTACK):
	nuke.frames.add("7_HAMAS_IS_EVIL")
	nuke.frames.add("1_HAMAS_IS_PROBLEM_TERROR_ATTACKS")

    if has_lemma(predobj, PROTECT) and has_lemma(predobj, CIVILIAN) and has_lemma(supredobj, ISRAEL):
        nuke.frames.add("4_ISRAEL_GOAL_PROTECT_CITIZENS")
        
    if has_lemma(predobj, STOP) and has_lemma(predobj, THREAT) and has_lemma(predobj, HAMAS):
        nuke.frames.add("4_ISRAEL_GOAL_STOP_HAMAS_THREAT")
        
    if has_lemma(predobj, RECOGNIZE) and has_lemma(predobj, ISRAEL):
        nuke.frames.add("4_SOLUTION_RECOGNIZE_ISRAEL")
    return nuke
