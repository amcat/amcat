#CREATE VIEW [wva].[vw_lemmastringfreqs_par123] as 
#select analysisid, articleid, ws.stringid as id, count(*) as n from parses_words p 
#inner join words_words w on p.wordid = w.wordid
#inner join sentences s on s.sentenceid = p.sentenceid
#inner join words_lemmata l on w.lemmaid = l.lemmaid
#inner join words_strings ws on l.stringid = ws.stringid
#                where parnr in (1,2,3) and isword=1
#group by analysisid, articleid, ws.stringid 

from amcat.ml import ml, dbwordfeature, mlalgo

from amcat.scripts import externalscripts
from amcat.model.coding import codingjob, codedarticle
from amcat.model import project
from amcat.model.articleset import ArticleSet
from amcat.db import dbtoolkit
from amcat.tools.stat import amcatr

import random, csv, sys
import logging; log = logging.getLogger(__name__)

def readsample(sample):
    if not sample.strip() or sample.strip().lower() == 'none': return None
    if "." in sample: return float(sample)
    if "%" in sample: return float(sample.replace("%",""))/100
    return int(sample)
    


class MachineLearningScript(externalscripts.ExternalScriptBase):
    """ExternalScript to Run machine learning

    @param trainjobids: a list of codingjobs to use for training
    @param fieldname: the fieldname to predict. This field must exist in all the codingjobs specified!
    @param testjobids: the jobs to use for testing.
    @param predictbatchids: the batches to predict

    The action to take depends on the provided paramters. If neither testjobs nor predictbatches are given,
    conduct a 10-fold crossvalidation. If testjobs are given, predict those jobs and report performance. If predict
    batches are given, predict these and save results as a codingjob in the project of that batch.
    """

    def _run(self, dummy, out, err, trainjobids, fieldname, testjobids=None, predictbatchids=None, sample=None):
        super(MachineLearningScript, self)._run(dummy, out, err)

        # setup parameters
        self.db = dbtoolkit.amcatDB(use_app=True)
        trainjobs = argToObjects(codingjob.Codingjob, self.db, trainjobids)
        self.field = trainjobs[0].articleSchema.getField(fieldname)
        testjobs = argToObjects(codingjob.Codingjob, self.db, testjobids)  
        predictsets = argToObjects(ArticleSet, self.db, predictbatchids)  
        if sample: sample = float(sample)

	log.warn("Testjobs: %s" % testjobs)
	log.warn("PredictSets: %s" % predictsets)
	


        # setup learner and train model
        self.getModel(trainjobs)


        # do the required action
        if testjobs:
            matches = self.testModelTable(testjobs)
            self.reportMatches("testreport", matches)
            
            # # write matches to csv
            # matches = list(self.testModel(testjobs))
            # w = csv.writer(sys.stdout)
            # header = ["algo", "aid", "cjaid", "actual", "position"]
            # for i in range(1, 6):
            #     header += ["pref%i"%i,"conf%i"%i]
            # w.writerow(header)

            # def getCode(id):
            #     lbl = self.db.getValue("select label from labels where objectid=%s and languageid=2" % id)
            #     return int(lbl[:4])
                
            # for m in matches:
            #     data = ["maxent", m.unit.article.id, m.unit.id, getCode(m.getActual()), m.getActualPosition()]
            #     for i in range(1,6):
            #         val, conf = m.predictions[i-1]
            #         val = getCode(val)
                    
            #         data += [val, conf]
            #     w.writerow(data)
                

        if predictsets:
            matches = self.predict(predictsets, sample, testjobs)
	    print type(matches)
            self.writeCodingJob(trainjobs[0], matches)
            
            

    def getModel(self, trainjobs):
        log.info("Training model on %s in jobs %s" % (self.field, trainjobs))
        self.learner = ml.MachineLearner()

        where = "select articleid from codingjobs_articles where %s" % self.db.intSelectionSQL("codingjobid", [job.id for job in trainjobs])
	#where = "select top 10 articleid from codingjobs_articles where %s" % self.db.intSelectionSQL("codingjobid", [job.id for job in trainjobs])
        view = "wva.vw_lemmastringfreqs_nohl"
        view = "wva.vw_lemmastringfreqs_par123"
        #view = "wva.vw_lemmastringfreqs_par12"
        #view = "wva.vw_lemmastringfreqs"
        fthres = 1
        features = dbwordfeature.getFeatures(self.db, where, view, fthres)
        self.learner.featureset = dbwordfeature.DBWordFeatureSet(self.db, view, features)
        
        self.learner.targetFunc = self._getFieldValue
        log.info("Creating feature set from input data");

        for job in trainjobs:
            log.debug( "Adding data for job %s" % job.idlabel());
            self.learner.addData(job, unitlevel = False)

        self.learner.algorithm = mlalgo.ALGORITHM_FACTORIES["maxent"]()
        #self.learner.algorithm = mlalgo.ALGORITHM_FACTORIES["libsvm_rbf"]()
        
        self.learner.train()
        log.info("Created model!")
        
    def _getFieldValue(self, unit):
        val = getattr(unit.values, self.field.fieldname, None)
        if val: return val.id

    def testModel(self, jobs):
        testdata = ml.getUnits(False, *jobs)
        log.info("Predicting model on jobs %s" % (jobs))
        matches = self.learner.predict(data=testdata)
        return matches
        
    def testModelTable(self, testjobs):
        return ml.MatchesTable(self.testModel(testjobs))

    
    def reportMatches(self, function, table):
        log.info( "Creating R data sets")
        table = amcatr.table2RFrame(table)
        log.info( "Calling R")
        reportdata = amcatr.call("/home/wva/libpy/ml/r/ml.r", function, table, interpret=True)
        report = amcatr.Report(reportdata)
        report.printReport(out=self.out)

    def getCandidates(self, sets, sample, testjobs=None):
        #if testdata: codedarticles |= set(u.getArticle() for u in testdata)
        log.debug("Determining articles to predict")
        topredict = set()
        for articleset in sets:
            topredict |= set(articleset.articles)

        log.debug("Removing train/test articles from %i articles" % (len(topredict),))

        topredict -= set(u.getArticle() for u in self.learner.units)
        if testjobs:
            topredict -= set(u.getArticle() for u in ml.getUnits(False, *testjobs))

        
        if sample:
            if sample < 0: sample *= len(topredict)
            sample = int(sample)
            log.debug("Sampling %i out of %i articles" % (sample, len(topredict)))
            if sample < len(topredict):
                topredict = random.sample(topredict, sample)

        log.debug("Will predict %i articles" % len(topredict))
        return topredict

    def predict(self, sets, sample, testjobs=None):
        cands = self.getCandidates(sets, sample, testjobs)
	if cands:
	    matches = ml.MatchesTable(self.learner.predict(data=cands))
	    return matches
	else:
	    log.warn("No candidates to predict!")
	    return None

    

    def writeCodingJob(self, job, matches):
        cj = cloneCodingJob(self.db, job, newname="MachineLearning job", coders=[34])
        cjset = list(cj.sets)[0]
        articles = {}
        for match in matches.getRows(): # matchestable contains Match objects as rows
            a = match.unit.getArticle()
            ca = articles.get(a)
            if not ca:
                ca = createCodedArticle(self.db, cjset, a)
                articles[a] = ca
	    else: #if not self.unitlevel:
		print "Skipping duplicate article %r" % (a)
		continue
            data = dict(codingjob_articleid=ca.id)
            data[self.field.fieldname] = match.getPrediction()
            data['confidence'] = int(match.getConfidence() * 1000)
            #if self.unitlevel: data['sentenceid']=match.unit.sentence.id
            self.db.insert(self.field.schema.table, data, retrieveIdent=False)
        print "Created codingjob %i" % cj.id
        self.db.commit()
    
        
def argToObjects(cls, db, arg):
    """Create objects cls(db, id) for every id in , delimited arg"""
    if not arg: return None
    return [cls(db, int(id)) for id in arg.split(",")]


def createCodingJob(db, project, name, unitschema, articleschema, coders=[]):
    #TODO: move to CodingJob.Create
    if not type(unitschema) == int: unitschema = unitschema.id
    if not type(articleschema) == int: articleschema = articleschema.id
    cjid = db.insert("codingjobs", dict(projectid=project.id, unitschemaid=unitschema, articleschemaid=articleschema, name=name))
    for i, coder in enumerate(coders):
        if not type(coder) == int: coder = coder.id
        db.insert("codingjobs_sets", dict(codingjobid=cjid, setnr=i+1, coder_userid=coder), retrieveIdent=False)
    return codingjob.CodingJob(project.db, cjid)


def createCodedArticle(db, codingjobset, article):
    cjid, setnr = codingjobset.id
    if not type(article) == int: article = article.id 
    cjaid = db.insert("codingjobs_articles", dict(codingjobid=cjid, setnr=setnr, articleid=article))
    return codedarticle.CodedArticle(codingjobset.db, cjaid)

def cloneCodingJob(db, codingjob, newname = None, coders=[]):
    if newname is None: newname = "%s (kopie)" % (codingjob.label,)
    return createCodingJob(db, codingjob.project, newname, codingjob.unitSchema, codingjob.articleSchema, coders=coders)

                                        
class MachineLearning(object):

    def writeCodingJob(self, kit, result):
        if not self.save: return
        # create new coding job with one set from the first job
        job = list(self.jobs)[0]
        cj = codingjob.cloneCodingJob(job, newname="MachineLearning job", coders=[user.currentUser(kit.db)])
        cjset = list(cj.sets)[0]
        articles = {}
        for match in result.getRows(): # matchestable contains Match objects as rows
            a = match.unit.getArticle()
            ca = articles.get(a)
            if not ca:
                ca = codingjob.createCodedArticle(cjset, a)
                articles[a] = ca
            data = dict(codingjob_articleid=ca.id)
            data[self.field.fieldname] = self.getIdForValue(match.getPrediction())
            data['confidence'] = int(match.getConfidence() * 1000)
            if self.unitlevel: data['sentenceid']=match.unit.sentence.id
            kit.db.insert(self.schema.table, data, retrieveIdent=False)
        kit.write("<h2>Created codingjob %i - <a href='https://amcat.vu.nl/dev/wva/codingjobDetails?codingjobid=%i'>View job</a> - <a href='https://amcat.vu.nl/dev/wva/codingjobResults?projectid=%i&codingjobids=%i'>View results</a></h2>" % (cj.id,cj.id,cj.project.id, cj.id))
        kit.db.commit()
            
    def writeCSV(self, kit, **tables):
        log.debug( "Writing test set as csv")
        kit.write("<h1>Download output file</h1>")
        for name, table in tables.iteritems():
            fn = toolkit.tempfilename(tempdir="/home/amcat/www/plain/test", prefix=name, suffix=".csv")
            outfile = open(fn, 'w')
            tableoutput.table2csv(table, outfile=outfile)
            kit.write("<p><a href='%s'>Download %s as csv</a></p>" % (fn.replace("/home/amcat/www/plain/","http://amcat.vu.nl/"), name))
    
    def reportMatches(self, kit, function, *tables, **kargs):
        log.debug( "Creating R data sets")
        tables = map(amcatr.table2RFrame, tables)
        log.debug( "Calling R")
        kargs["interpret"] = True
        report = amcatr.Report(amcatr.call("/home/wva/libpy/ml/r/ml.r", function, *tables, **kargs))
        report.printReport(out=kit)

    @property
    def unitlevel(self):
        return not self.schema.articleschema
        
    def testUnits(self):
        return ml.getUnits(self.unitlevel, *self.testjobs)

    def predictArticles(self):
        data = project.getArticles(*self.predictbatches)
        #data = list(data)[:100]
        return data
        
    def getModel(self, kit, jobs=None):
        learner = self.getLearner(overviewWriter=kit.req, jobs=jobs)
        log.debug( "Creating model");
        learner.train()
        return learner
        
    def traintest(self, kit):
        self.check(requireTestJobs=True)
        learner = self.getModel(kit)
        log.debug( "Testing")
        matches = ml.MatchesTable(learner.predict(data=self.testUnits()))
        self.writeCSV(kit, testdata=matches)
        self.writeCodingJob(kit, result=matches)
        self.reportMatches(kit, "testreport", matches)

        if self.steptraining:
            jobs = list(self.jobs)
            stepmatches=[]
            for i, job in enumerate(jobs):
                log.debug( "Stepwise training iteration %i / %i" % (i, len(jobs)))
                usejobs = jobs[:(i+1)]
                learner = self.getModel(kit, jobs=usejobs)
                log.debug( "... Testing")
                stepmatches.append(ml.MatchesTable(learner.predict(data=self.testUnits())))
            self.reportMatches(kit, "stepreport", stepmatches)
            
    def activelearning(self, kit):
        self.check(requireTestJobs=True, requirePredictBatches=True)
        learner = self.getModel(kit)
        log.debug( "Testing")
        testdata = list(self.testUnits())
        testmatches = ml.MatchesTable(learner.predict(data=testdata))
        cands = self.getCandidates(learner, testdata)
        log.debug( "Predicting")
        predicted = ml.MatchesTable(learner.predict(data=cands))
        self.writeCSV(kit, testdata=testmatches, predicted=predicted)
        self.writeCodingJob(kit, result=predicted)
        self.reportMatches(kit, "testreport", testmatches)
        #self.reportMatches(kit, "predictreport", predicted, testmatches)
        #tocode = amcatr.call("/home/wva/libpy/ml/r/ml.r", "sample", predicted, 10)
        #kit.write("<p>To code: %i</p>" % len(tocode))


    def getCandidates(self, learner, testdata = None):
        log.debug( "Determining articles to predict")
        codedarticles = set(u.getArticle() for u in learner.units)
        if testdata: codedarticles |= set(u.getArticle() for u in testdata) 
        cands = [a for a in self.predictArticles() if a not in codedarticles]
        orig = len(cands)
        if type(self.sample) == int: cands = cands[:self.sample]
        elif type(self.sample) == float: cands = cands[:int(len(cands) * self.sample)]
        log.debug( "Using %i from %i articles (sample was %r)" % (len(cands), orig,  self.sample))
        return cands
        

    def predict(self, kit):
        self.check(requirePredictBatches=True)
        learner = self.getModel(kit)
        log.debug( "Determining articles to predict")
        log.debug( "Predicting")
        cands = self.getCandidates(learner)
        matches = ml.MatchesTable(learner.predict(data=cands))
        self.writeCSV(kit, predicted=matches)
        self.writeCodingJob(kit, result=matches)
        #self.reportMatches(kit, "predictreport", matches)
        
    def nfold(self, kit, n=5):
        self.check()
        learner = self.getLearner(overviewWriter=kit.req)
        log.debug( "Calculating %i-fold results" % n);
        matches = ml.MatchesTable(learner.nfold(n=n))
        self.writeCSV(kit, testdata=matches)
        self.reportMatches(kit, "testreport", matches)#, byfold=True)
        
    def writePageEnd(self, kit):
        #kit.write("<script>hideDebug(); setvis();</script>")
        kit.write("<script>setvis();</script>")
        
    def writePageStart(self, kit, config):

        projectid = self.project and self.project.id
        projects = kit.db.projectListSelect()
        projectIds = [row[0] for row in projects]
        if projectid and not projectid in projectIds:
            projects.insert(0, kit.db.singleProjectListSelect(projectid))
        
        projectshtml = htmllib.select('projectid', projects, config=config,
                                      valueInName=1, 
                                      attributes='style="width:349px" onchange="reloadProject()"',
                                      startOption="[Please select a project]")


        algohtml = htmllib.select('algo', mlalgo.ALGORITHM_FACTORIES.keys(), config=config)

        if type(self.sample) == int: samplehtml = "%i" % self.sample
        elif type(self.sample) == float: samplehtml = "%.0i%%" % int(self.sample * 100)
        elif self.sample == None: samplehtml = ""
        else: raise Exeption(self.sample)
        samplehtml = '<input name="sample" value="%s">' % self.sample
        
        schemahtml = '[Select a project first]'
        batchhtml = '[Select a project first]'
        codingjobshtml = '[Select a coding schema first]'
        codingjobs2html = '[Select a coding schema first]'
        fieldnamehtml = '[Select a coding schema first]'

        savehtml = '<input type="checkbox" name="savetodb" %s>' % ("checked" if config['savetodb'] else "")
        stephtml = '<input type="checkbox" name="steptraining" %s>' % ("checked" if config['steptraining'] else "")
        
        if self.project:
            schemaid = self.schema and self.schema.id
            schemas = set()
            #cachable.cache(self.project, codingjobs=dict(unitSchema=["name"],articleSchema=["name"], name=[]))
            for job in self.project.codingjobs:
                schemas |= set([job.unitSchema, job.articleSchema])
            schemas = [(s.id, s.name) for s in sorted(schemas)]


            
            schemahtml = htmllib.select('schemaid', schemas, config=config,
                                          valueInName=1, 
                                          attributes='style="width:349px" onchange="reloadSchema()"',
                                          startOption="[Please select a coding schema]")
            

            batches = [(b.id, b) for b in self.project.batches]
            batchhtml = htmllib.select('batchids', batches, config=config, valueInName=1, 
                                       attributes='multiple="true" size="5" style="width:349px"')

            
            if self.schema:
                jobs = self.project.codingjobs
                if self.schema.articleschema:
                    jobs = [j for j in jobs if j.articleSchema == self.schema]
                else:
                    jobs = [j for j in jobs if j.unitSchema == self.schema]
                jobs = [(j.id, j) for j in jobs]
                codingjobshtml = htmllib.select('codingjobids', jobs,
                                                config=config, valueInName=1, 
                                                attributes='multiple="true" size="5" style="width:349px"')

                codingjobs2html = htmllib.select('codingjobids2', jobs,
                                                 config=config, valueInName=1, 
                                                 attributes='multiple="true" size="5" style="width:349px"')
                schemalabel = str
                fields  = [(f.fieldname, schemalabel(f)) for f in self.schema.fields]
                fieldnamehtml = htmllib.select('fieldname', fields,
                                               config=config, valueInName=1, 
                                               attributes='style="width:349px"',
                                               startOption="[Please select a field to predict]")
            
        actionHtml = htmllib.radio(OPTIONS.action, config=config)

        html = '''
        <div class="search">
           <form action="?" method="POST" name="form">
             <label class="textlabel-wide"><strong>Algorithm</strong></label> %(algohtml)s <br/>
             <label class="textlabel-wide"><strong>Project</strong></label> %(projectshtml)s <br/>
             <label class="textlabel-wide"><strong>Coding Schema</strong></label> %(schemahtml)s <br/>
             <div id="codingjobs"><label class="textlabel-wide">Training Jobs</label>%(codingjobshtml)s</div><br />
             <label class="textlabel-wide">Field</label>%(fieldnamehtml)s<br />
             <label class="textlabel-wide">Action</label>%(actionHtml)s<br/><br/>
      
             <div id="codingjobs2"><label class="textlabel-wide">Test Jobs</label>%(codingjobs2html)s</div><br />
             <div id="batches"><label class="textlabel-wide">Predict Batches</label>%(batchhtml)s</div><br />
             <div id="sample"><label class="textlabel-wide">Predict Sample</label>%(samplehtml)s (e.g. 1000, .25, 25%%)</div><br />
             <div id="sample"><label class="textlabel-wide">&nbsp;</label>%(savehtml)s Save results to codingjob</div><br />
             <div id="sample"><label class="textlabel-wide">&nbsp;</label>%(stephtml)s Insert training jobs one-at-a-time (to see learning rate) </div><br />
            <br /><br />
            <input type="submit" value="Submit" />
           </form>
        </div>''' % locals()
        kit.write(html)

from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()
        
if __name__ == '__main__':
    import dbtoolkit
    class fakekit():
        def write(self, html): print html
    db = dbtoolkit.amcatDB()
    ml = MachineLearning()
    ml.project = Project(kit.db, 282)
    ml.schema = annotationschema.AnnotationSchema(kit.db, 26)
    ml.field = ml.schema.getField('topic')
    ml.jobs =  [codingjob.CodingJob(kit.db, srid) for srid in [1756,1865,1885,2057,2227,2228,2259,2267,2273,2291,2300,2301,2304,2309,2483]]
    ml.predictbatches = [project.Batch(kit.db, bid) for bid in [5989]]
    ml.save = True
    ml.predict(fakekit())
