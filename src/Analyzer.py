'''
Created on Feb 21, 2012

@author: Moises Osorio [WCoder]
'''
from MOSolution import MOSolution
from Metrics import Metrics
from MetricsCalc import MetricsCalc
from ResultPlotter import ResultPlotter
import Utils
import dircache
import os
import shutil
import time
import types

class Analyzer:
    
    __PARETO__ = "pareto"
    __TEMPLATE_FILE__ = "report.tex"
    __TEMPLATE_DIR__ = Utils.__RESOURCES_DIR__ + "report/"
    __TEMPLATE_VAR__ = "%RESULTS%"
    __IMAGES_DIR__ = "images/"

    def __init__(self):
        self.plotter = ResultPlotter()
        self.metrics = MetricsCalc()
        
        self.pareto = None
        self.setResultDirectories([])
        
    def setPareto(self, pareto):
        self.pareto = pareto
        self.addResultDirectory(pareto)
        
    def addResultDirectory(self, result):
        if result not in self.resultDirectories:
            self.nResults += 1
            self.resultDirectories.append(result)
            self.resultNames.append(self.getResultName(result))
            self._scanDirectory(result)
        
    def removeResultDirectory(self, result):
        if result in self.resultDirectories:
            self.resultDirectories.remove(result)
            self.setResultDirectories(self.resultDirectories)
        
    def setResultDirectories(self, results):
        self.resultDirectories = []
        self.resultNames = []
        self.functions = {}
        self.nResults = 0
        
        if self.pareto is not None:
            self.setPareto(self.pareto)
        for result in results:
            self.addResultDirectory(result)
        
    def getResultName(self, directory):
        directory = str(directory)
        if directory[-1] == "/":
            directory = directory[:-1]
        slash = max(directory.rfind("/"), directory.rfind("\\"))
        return directory[slash+1:]
    
    def getResultsForFunction(self, functionName):
        return self.functions[functionName.lower()]
    
    def getFunctionNames(self, includeNotSolved=False):
        return [function.functionName for function in self.functions.values() if includeNotSolved or \
                self._hasNonPareto(function.functionImplementation) or \
                self._hasNonPareto(function.variableImplementation)]
    
    def exportAllImages(self, directory, resultNames=None):
        if resultNames is None:
            resultNames = self.resultNames
        for functionName in self.getFunctionNames():
            function = self.functions[functionName.lower()]
            filename = directory + "/" + function.functionName
            generation = [0] * len(resultNames)
            self.exportToImage(function, generation, True, resultNames, filename + "_fun.png")
            self.exportToImage(function, generation, False, resultNames, filename + "_var.png")
    
    def exportToImage(self, function, generation, functionSpace, resultNames, filename):
        toPlot = self._getSolutionsToPlot(function, generation, functionSpace, resultNames)
        axis = ["x1", "x2", "x3"]
        if functionSpace:
            axis = ["F1", "F2", "F3"]
        self.plotter.plotSolution(toPlot, function.functionName, None if functionSpace else "Parameter space", axis[0], axis[1], axis[2], filename)
      
    def _getSolutionsToPlot(self, problem, generation, functionSpace, resultNames):
        solutions = []
        k = 0
        if Analyzer.__PARETO__ in resultNames:
            resultNames.remove(Analyzer.__PARETO__)
            resultNames.insert(0, Analyzer.__PARETO__)
            
        for name in resultNames:
            k += 1
            if functionSpace:
                solution = problem.getFunctionSolution(name)
            else:
                solution = problem.getVariableSolution(name)
            if solution is not None:
                rgb = 3*[0]
                for p in xrange(3):
                    if k & (1 << p) > 0:
                        rgb[p] = 255
                points = solution.getSolutionPoints(generation[k-1])
                solutions.append([name, points, rgb])
            
        return solutions
            
    def _hasNonPareto(self, implementations):
        if len(implementations) > 1:
            return True
        if len(implementations) == 0:
            return False
        return Analyzer.__PARETO__ not in implementations.keys()
    
    def _scanDirectory(self, directory):
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return
        
        resultName = self.getResultName(directory)
        for filename in dircache.listdir(directory):
            filename = str(directory + "/" + filename)
#            fileType, _ = mimetypes.guess_type(filename)
            #if fileType is None or "text" not in fileType or not self.isSolutionFile(filename):
            if not Utils.isSolutionFile(filename):
                continue
            
            functionName = Utils.getFunctionName(filename)
            genPos = max(-1, functionName.rfind("."), functionName.rfind("-"), functionName.rfind("_"))
            generation = 1 << 30
            if genPos >= 0:
                try:
                    generation = int(functionName[genPos+1:])
                    functionName = functionName[:genPos]
                except:
                    pass
                
            fnId = functionName.lower()
            if fnId in self.functions:
                function = self.functions[fnId]
            else:
                function = MOSolution(functionName)
                self.functions[fnId] = function
                
            if Utils.isFunctionFile(filename):
                function.addFunctionSolution(resultName, filename, generation)
            else:
                function.addVariableSolution(resultName, filename, generation)
            
    def functionMatches(self, desc, testName):
        desc = desc.lower()
        testName = testName.lower()
        if desc == testName:
            return True
        if desc.endswith("*") and testName.startswith(desc[:-1]):
            return True
        try:
            testDim = None # FIXME: Get dimension?
            if desc.endswith("d") and testDim == int(desc[:-1]):
                return True
        except:
            None
        return False
    
    def getFunctionResults(self, functionName, resultNames):
        function = self.getResultsForFunction(functionName)
        solutions = []
        for name in resultNames:
            if name.lower() != Analyzer.__PARETO__:
                result = function.getFunctionSolution(name)
                if result is not None:
                    solutions.append([name, [result.getSolutionPoints(idx) for idx in xrange(result.count())]])
                
        return solutions
    
    def getFunctionPareto(self, functionName):
        pareto = self.getResultsForFunction(functionName).getFunctionSolution(Analyzer.__PARETO__)
        if pareto is None:
            return None
        return pareto.getSolutionPoints(0)
    
    def getFormattedValue(self, data1, data2, best, decimalFormat="%.4f", bestFormat="\\textbf{%s}"):
        if data1 is None:
            return "---"
        
        if isinstance(data1, types.StringType):
            return data1
        
        value = decimalFormat % data1
        if data2 is not None:
            value += " / " + (decimalFormat % data2)
        if best:
            value = bestFormat % value
        return value
    
    def _getBlockLatex(self, name, description, data1, data2, best):
        n = len(data1)
        if description is None or (len(description) == 1 and description[0] is None):
            latex = ["            \\multicolumn{2}{|c||}{%s}" % name]
        else:
            latex = ["            \\multirow{%d}{*}{%s}" % (n, name)]
        for block in xrange(n):
            latexRow = []
            if description is not None and description[block] is not None:
                latexRow.append(description[block])
            for i in xrange(len(data1[block])):
                latexRow.append(self.getFormattedValue(data1[block][i], None if data2 is None \
                                                       else data2[block][i], best[block][i] if best is not None else False))
            latex.append("                & " + " & ".join(latexRow) + " \\\\")
        latex.append("                \\hline")
        return "\n".join(latex)
    
    def _getTableStartLatex(self, nColumns, big=True):
        latex = ["\\begin{table}"]
        latex.append("    \\tiny \\centering")
        sizeFactor = ""
        if big:
            latex.append("    \\begin{adjustwidth}{-3cm}{-3cm}")
            sizeFactor = "1.5"
        latex.append("        \\begin{tabularx}{%s\\textwidth}{| c | c || %s |}" % (sizeFactor, " | ".join(["K"] * nColumns)))
        latex.append("        \\hline")
        return "\n".join(latex)
    
    def _getTableEndLatex(self, caption, label, big=True):
        latex = ["        \\end{tabularx}"]
        if big:
            latex.append("    \\end{adjustwidth}")
        latex.append("    \\caption{\\label{%s} %s}" % (label, caption))
        latex.append("\\end{table}")
        return "\n".join(latex)
    
    def getCurrentBestResult(self):
        convIdx = len(self.metrics.labels) - 2
        distIdx = convIdx + 1
        convergence = self.metrics.metricMean[convIdx]
        distribution = self.metrics.metricMean[distIdx]
        best = 0
        for i in xrange(1, self.nResults - 1):
            if convergence[i] > convergence[best] + Utils.__EPS__:
                best = i
            elif abs(convergence[i] - convergence[best]) < Utils.__EPS__ and distribution[i] > distribution[best]:
                best = i
                
        return best
    
    def getCurrentLatex(self, functionName):
        nRows = len(self.metrics.labels)
        nColumns = self.nResults - 1
        
        latex = [self._getTableStartLatex(nColumns)]
        latex.append(self._getBlockLatex("Metric / Algorithm", None, [self.metrics.solutionNames], None, None))
        latex.append("            \\hline")
        row = 0
        while row < nRows:
            if row < self.metrics.nUnaryMetrics:
                toRow = row + 1
            elif row < nRows-2:
                toRow = row + nColumns
            else:
                toRow = nRows

            name = self.metrics.labels[row]
            if row == nRows - 2:
                latex.append("            \\hline")
                name = "\\textbf{%s}" % name
            latex.append(self._getBlockLatex(name, self.metrics.sublabels[row:toRow], self.metrics.metricMean[row:toRow], \
                                             self.metrics.metricStd[row:toRow], self.metrics.metricIsBest[row:toRow]))
            row = toRow
        
        latex.append(self._getTableEndLatex("Results for function %s." % functionName, "%s-results-table" % functionName.lower()))
        return "\n".join(latex)
    
    def _getFigureLatex(self, functionName, highlight, filename, caption):
        latex = ["\\begin{figure}[!ht]"]
        latex.append("\\centering")
        latex.append("\\includegraphics[width=\\textwidth]{%s}" % filename)
        latex.append("\\caption{%s}" % caption)
        latex.append("\\end{figure}")
        return "\n".join(latex)
    
    def generateBestImage(self, functionName, highlight, filename, worst=False):
        print "    Generating %s figure for %s" % ("worst" if worst else "best", functionName)
        function = self.functions[functionName.lower()]
        resultNames = [Analyzer.__PARETO__, highlight]
        if highlight is None:
            resultNames = self.resultNames
        generation = [0] * len(resultNames)
        
        pareto = self.getFunctionPareto(functionName)
        factor = -1 if worst else 1
        for i in xrange(len(resultNames)):
            if resultNames[i] == Analyzer.__PARETO__:
                continue
            
            results = self.getFunctionResults(functionName, [resultNames[i]])
            bestValue = factor * (1 << 30)
            metrics = Metrics(pareto, [results[0][1]])
            for run in xrange(len(results[0][1])):
                metrics.setSolutionsToCompare(0, run, None, None)
                value = metrics.deltaP()
                if value*factor < bestValue*factor:
                    bestValue = value
                    generation[i] = run
        
        self.exportToImage(function, generation, True, resultNames, filename)
        
    def computeMetrics(self, functionName):
        pareto = self.getFunctionPareto(functionName)
        results = self.getFunctionResults(functionName, self.resultNames)
        self.metrics.computeMetrics(pareto, results)
        
    def _getFunctionLatex(self, functionName, reportDir, highlight):
        self.computeMetrics(functionName)
        
        imageDir = reportDir + Analyzer.__IMAGES_DIR__
        if not os.path.exists(imageDir):
            os.makedirs(imageDir)
        
        desc = highlight
        if desc is None:
            desc = "all results"
        caption = "run of %s for %s (according to DeltaP)." % (desc, functionName)
        
        bestImage = Analyzer.__IMAGES_DIR__ + functionName + "_best_fun.png"
        self.generateBestImage(functionName, highlight, reportDir + bestImage)
        latex = [self._getFigureLatex(functionName, highlight, bestImage, "Best %s" % caption)]
        
        worstImage = Analyzer.__IMAGES_DIR__ + functionName + "_worst_fun.png"
        self.generateBestImage(functionName, highlight, reportDir + worstImage, True)
        latex.append(self._getFigureLatex(functionName, highlight, worstImage, "Worst %s" % caption))
        
        latex.append(self.getCurrentLatex(functionName))
        return "\n".join(latex)
    
    def _getBest(self, data):
        n = len(data)
        best = [False] * n
        maxValue = max(data)
        for i in xrange(n):
            if abs(maxValue - data[i]) < Utils.__EPS__:
                best[i] = True
                
        return best
    
    def _getAllSummaryLatex(self, functionNames, convPoints, distPoints, innerLatex):
        best = [self._getBest(convPoints), self._getBest(distPoints)]
        
        latex = [self._getTableStartLatex(len(self.metrics.solutionNames), False)]
        latex.append(self._getBlockLatex("Function / Algorithm", None, [self.metrics.solutionNames], None, None))
        latex.append("            \\hline")
        latex += innerLatex
        latex.append(self._getBlockLatex("\\textbf{Total}", ["Convergence", "Distribution"], [convPoints, distPoints], None, best))
        latex.append(self._getTableEndLatex("Result summary.", "tab:results-summary", False))
        
        return "\n".join(latex)
    
    def generateReport(self, reportDir, functionNames, highlight):
        if reportDir[-1] != "/":
            reportDir += "/"
        if os.path.exists(reportDir):
            newResultDir = "%s-%s" % (reportDir[:-1], time.strftime("%Y%m%d-%H%M%S"))
            print "Backing up previous report at '%s' to '%s'" % (reportDir, newResultDir)
            shutil.move(reportDir, newResultDir)
            
        print "Copying template files"
        shutil.copytree(Analyzer.__TEMPLATE_DIR__, reportDir)
        print "Generating results latex"
        resultsLatex = self._getLatex(functionNames, reportDir, highlight)
        
        print "Adding results latex into report template"
        template = open(Analyzer.__TEMPLATE_DIR__ + Analyzer.__TEMPLATE_FILE__, "r")
        report = open(reportDir + Analyzer.__TEMPLATE_FILE__, "w")
        for line in template:
            if line.strip() == Analyzer.__TEMPLATE_VAR__:
                report.write(resultsLatex)
            else:
                report.write(line)
    
        template.close()
        report.close()
        print "Report successfully generated!"
    
    def _getLatex(self, functionNames, reportDir, highlight):
        latex = []
        innerSummaryLatex = []
        convPoints = [0] * (self.nResults - 1)
        distPoints = [0] * (self.nResults - 1)
        idx = 0
        for functionName in functionNames:
            idx += 1
            print "Generating results for function %s (%d/%d)" % (functionName, idx, len(functionNames))
            latex.append(self._getFunctionLatex(functionName, reportDir, highlight))
            if idx % 7 == 0:
                latex.append("\\clearpage")
            latex.append("")
            innerSummaryLatex.append(self._getBlockLatex(functionName, ["Convergence", "Distribution"], \
                                                         [self.metrics.convPoints, self.metrics.distPoints], None, \
                                                         self.metrics.metricIsBest[-2:]))
            innerSummaryLatex.append("            \\hline")
            for i in xrange(self.nResults - 1):
                convPoints[i] += self.metrics.convPoints[i]
                distPoints[i] += self.metrics.distPoints[i]
        
        print "Generating all summary results"
        latex.append(self._getAllSummaryLatex(functionNames, convPoints, distPoints, innerSummaryLatex))
        return "\n".join(latex)
    