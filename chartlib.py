import sys, re, datetime, toolkit
sys.path.append('/home/amcat/resources/ChartDirector/lib')

formats = dict()

try:
    from pychartdir import PNG
    formats['png'] = PNG
except:
    pass

try:
    from pychartdir import SVG
    formats['svg'] = SVG
except:
    pass

from pychartdir import XYChart, Side
          

def chart(chartType, dataDict, labels, tempDir=None, interval=None, keywords=None, isArticleCount=1, extraJsParameters=None, isPercentage=False, format='png', title=None, orderkey=toolkit.naturalSortKey):


    chart = XYChart(770, 450)
    if format == 'svg':
        chart.enableVectorOutput()
    format = formats[format]
    
    labels = map(lambda s:s.encode('utf-8'), labels)

    # Set plotarea, size, background and grid lines
    chart.setPlotArea(55, 10, 500, 280, 0xffffff, -1, -1, 0xcccccc, 0xcccccc)

    chart.addLegend2(560, 10, -2, "", 8)

    keys = sorted(dataDict.keys(), key=orderkey)
    
    if chartType in ('date', 'stacked-date'):
        if not interval: raise Exception('interval parameter missing')
        allDates = getDates(labels, interval)
        if chartType == 'stacked-date':
            layer = chart.addAreaLayer2(Percentage)
        else:
            layer = chart.addLineLayer()
            chart.yAxis().setAutoScale(0.05, 0.1, 1)
        layer.setLineWidth(2)
        
        for key in keys:
            datesDict = dict(zip(labels, dataDict[key]))
            data = [datesDict.get(date, 0) for date in allDates]
            if type(key) == unicode: key = key.encode('utf-8')
            layer.addDataSet(data, -1, key)
            
        chart.yAxis().setMinTickInc(1)
        
        label = chart.xAxis().setLabels(allDates)
        label.setFontAngle(-45)
        
        # Do not show all labels, to keep them readable for large sets
        chart.xAxis().setLabelStep(len(allDates) / 20.0)
    elif chartType in ('bar', 'stacked-bar'):
        if chartType == 'stacked-bar':
            layer = chart.addBarLayer2(Percentage, 5)
        else:
            layer = chart.addBarLayer2(Side)
            chart.yAxis().setAutoScale(0.05, 0.1, 1)
        for key in keys:
            name = key
            if type(name) == unicode: name = name.encode('utf-8')
            try:
                layer.addDataSet(dataDict[key], -1, name)
            except Exception, e:
                raise Exception(key, dataDict[key], e)
        label = chart.xAxis().setLabels(labels)
        
        chart.yAxis().setMinTickInc(1)
        
        if len(labels) > 5:
            label.setFontAngle(-25)
    elif chartType == 'line':
        layer = chart.addLineLayer()
        chart.yAxis().setAutoScale(0.05, 0.1, 1)
        chart.yAxis().setAutoScale(0.0, 0.0, False)
        layer.setLineWidth(2)
     
        for key in keys:
            datesDict = dict(zip(labels, dataDict[key]))
            data = [datesDict.get(label, 0) for label in labels]
            #raise Exception(`data`)
            if type(key) == unicode: key = key.encode('utf-8')
            layer.addDataSet(data, -1, key)
            
        #chart.yAxis().setMinTickInc(1)
        
        label = chart.xAxis().setLabels(labels)
        label.setFontAngle(-45)
        
        # Do not show all labels, to keep them readable for large sets
        chart.xAxis().setLabelStep(len(labels) / 20.0)
    else:
        raise Exception('invalid chart chartType')

    if title is None:
        if isPercentage:
            title = "Association (%)"
        else:
            title = "Number of %s" % ('Articles' if isArticleCount else 'Hits')
    chart.yAxis().setTitle(title, "arialbd.ttf", 10)

    if tempDir:
        chartFileLocation = chart.makeTmpFile(tempDir, imageFormat=format)
        chartFileName = re.sub(tempDir, '', chartFileLocation)
    else:
        chartFileName = chart.makeChart2(format)

    if type(keywords) == unicode:
        keywords = keywords.encode('utf-8')
    if not extraJsParameters:
        extraJsParameters = ", '%s'" % keywords if keywords else ''
    chartHtmlImageMap = chart.getHTMLImageMap("javascript:showGraphArticles('{dataSetName}','{xLabel}','{value}'%s);" % extraJsParameters, " ",
        "title='{dataSetName} - {xLabel}: {value|0} articles'")
    chartHtmlImageMap = chartHtmlImageMap.replace('>','/>')

    return chartFileName, chartHtmlImageMap
    


def cropData(data):
    CMD = 'convert -trim - -'
    out, err = toolkit.execute(CMD, data)
    if err:
        raise Exception(err)
    return out
    

def getDates(labels, interval):
    minDate = sorted(labels)[0]
    maxDate = sorted(labels)[-1]
    minDate = map(int, minDate.split('-'))
    maxDate = map(int, maxDate.split('-'))
    result = []
    if interval == 'month':
        for year in range(minDate[0], maxDate[0]+1):
            if year == minDate[0]:
                minMonth = minDate[1]
            else:
                minMonth = 1
            if year == maxDate[0]:
                maxMonth = maxDate[1]
            else:
                maxMonth = 12
            for month in range(minMonth, maxMonth+1):
                key = '%s-%002d' % (year, month)
                result.append(key)
    elif interval == 'quarter':
        for year in range(minDate[0], maxDate[0]+1):
            if year == minDate[0]:
                minMonth = minDate[1]
            else:
                minMonth = 1
            if year == maxDate[0]:
                maxMonth = maxDate[1]
            else:
                maxMonth = 4
            for month in range(minMonth, maxMonth+1):
                key = '%s-%002d' % (year, month)
                result.append(key)
    elif interval == 'week':
        for year in range(minDate[0], maxDate[0]+1):
            if year == minDate[0]:
                minWeek = minDate[1]
            else:
                minWeek = 1
            if year == maxDate[0]:
                maxWeek = maxDate[1]
            else:
                maxWeek = 52
            for week in range(minWeek, maxWeek+1):
                key = '%s-%002d' % (year, week)
                # dateObj = time.strptime('%s-%s-0' % (year, week), '%Y-%W-%w')
                # key = time.strftime('%Y-%m-%d', dateObj[:3]+(0,)*6)
                result.append(key)
    elif interval == 'year':
        for year in range(minDate[0], maxDate[0]+1):
            key = '%s' % year
            result.append(key)
    elif interval == 'day':
        startOrd = datetime.date(minDate[0], minDate[1], minDate[2]).toordinal()
        endOrd = datetime.date(maxDate[0], maxDate[1], maxDate[2]).toordinal()
        for ord in range(startOrd, endOrd + 1):
            d = datetime.date.fromordinal(ord)
            key = d.strftime('%Y-%m-%d')
            result.append(key)
    else:
        raise Exception('invalid interval')
    #raise Exception(`labels` + '<br />' + `result`)
    return result    

if __name__=='__main__':
    fn, map = chart('line', {'a': [1,2,3,4], 'b' : [2,5,1,3]}, ["x","y","z","w"], "/tmp", format='svg')
    print fn
