#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html

#Adapted from Condor-COPSAI
#code.google.com/p/condor-copasi
import subprocess, os, re, math, time
from cloud_copasi import settings
from cloud_copasi.condor import condor_spec
from lxml import etree
from string import Template
xmlns = '{http://www.copasi.org/static/schema}'

condor_string_body = """transfer_input_files = ${copasiFile}${otherFiles}
log =  ${copasiFile}.log  
error = ${copasiFile}.err
output = ${copasiFile}.out
Requirements = ( (OpSys == "WINNT61" && Arch == "INTEL" ) || (OpSys == "WINNT61" && Arch == "X86_64" ) || (Opsys == "LINUX" && Arch == "X86_64" ) || (OpSys == "OSX" && Arch == "PPC" ) || (OpSys == "OSX" && Arch == "INTEL" ) || (OpSys == "LINUX" && Arch == "INTEL" ) ) && (Memory > 0 ) && (Machine != "e-cskc38c04.eps.manchester.ac.uk") && (machine != "localhost.localdomain")
#Requirements = (OpSys == "LINUX" && Arch == "X86_64" )
should_transfer_files = YES
when_to_transfer_output = ON_EXIT
queue\n"""


def get_time_per_job(job):
    #For benchmarking purposes, jobs with a name ending with ?t=0.5 will use the custom t for load balancing
    name_re = re.compile(r'.*t=(?P<t>.*)')
    name_match = name_re.match(job.name)
    if name_match:
        return float(name_match.group('t'))
    else:
        return settings.IDEAL_JOB_TIME
    

class CopasiModel(object):
    """Class representing a Copasi model"""
    def __init__(self, filename, binary=settings.COPASI_LOCAL_BINARY, binary_dir=None, job=None):
        
        if binary_dir == None:
            binary_dir, binary_path = os.path.split(settings.COPASI_LOCAL_BINARY)
        
        #Load the copasi binary
        self.model = etree.parse(filename)
        self.binary = binary
        self.binary_dir = binary_dir
        self.name = filename
        (head, tail) = os.path.split(filename)
        self.path = head
        self.job=job
    def __unicode__(self):
        return self.name
    def __string__(self):
        return self.name
        
    def write(self, filename):
        """Write the contents of the model to the specified filename, preserving xml declaration"""
        
        return self.model.write(filename,xml_declaration=True, encoding='utf-8')
        
    def is_valid(self, job_type):
        """Check if the model has been correctly set up for a particular condor-copasi task"""
        #Check the version is correct
        if not (self._getVersionDevel() >= 33 or self._getVersionMajor() >= 2012):
            return 'The model must be saved using a supported version of Copasi. The model you submitted appears to have been saved using version ' + str(self._getVersionDevel())
        if job_type == 'SO':
            #Check that a single object has been set for the sensitivities task:
            if self.get_sensitivities_object() == '':
                return 'A single object has not been set for the sensitivities task'
            #And check that at least one parameter has been set
            if len(self.get_optimization_parameters()) == 0:
                return 'No parameters have been set for the optimization task'

            return True
            
        elif job_type == 'SS':
            if self.get_timecourse_method() == 'Deterministic (LSODA)':
                return 'Time course task must have a valid Stochastic or Hybrid algorithm set'
            return True
        
        elif job_type == 'PS':
            scanTask = self._getTask('scan')
            problem = scanTask.find(xmlns+'Problem')
            scanItems = problem.find(xmlns + 'ParameterGroup')
            if len(scanItems) == 0:
                return 'At least one scan must have been set'
            #Extract some details about the scan task
            firstScan = scanItems[0]
            for parameter in firstScan:
                if parameter.attrib['name'] == 'Type':
                    scan_type = parameter
                if parameter.attrib['name'] == 'Number of steps':
                    no_of_steps = parameter
            #Check that the first scan item is either a scan or a repeat
            if not (scan_type.attrib['value'] == '1' or scan_type.attrib['value'] == '0'):
                return 'The first item in the scan task must be either a Parameter Scan or a repeat'
            #Check that, if the first scan item is a parameter scan, there is at least 1 interval
            if scan_type.attrib['value'] == '1' and int(no_of_steps.attrib['value']) < 1:
                return 'The first-level Parameter Scan must have at least one interval. If only one repeat is required, consider replacing the Parameter Scan with a Repeat'
            report = scanTask.find(xmlns + 'Report')
            if report == None or report.attrib['reference'] == '':
                return 'A report must be set for the scan task'
            return True
            
        elif job_type == 'OR' or job_type == 'OD':
            #Check that at least one parameter has been set
            if len(self.get_optimization_parameters()) == 0:
                return 'No parameters have been set for the optimization task'
            #Check that an object has been set for the sensitivities task
            if self._get_optimization_object() == '':
                return 'No objective expression has been set for the optimization task'
            return True
        elif job_type == 'PR':
            #Check that at least one parameter has been set
            if len(self.get_parameter_estimation_parameters()) == 0:
                return 'No parameters have been set for the sensitivites task'
            return True
        elif job_type == 'SP':
            #Check that at least one parameter has been set
            if len(self.get_parameter_estimation_parameters()) == 0:
                return 'No parameters have been set for the parameter estimation task'
            return True
        else:
            return True
        
    def _copasiExecute(self, filename, tempdir, timeout=-1, save=False):
        """Private function to run Copasi locally in a temporary folder."""
        import process
        if not save:
            returncode, stdout, stderr = process.run([self.binary, '--nologo',  '--home', tempdir, filename], cwd=tempdir, timeout=timeout)
        else:
            returncode, stdout, stderr = process.run([self.binary, '--nologo',  '--home', tempdir, '--save', filename, filename], cwd=tempdir, timeout=timeout)
        return returncode, stdout, stderr
        
   
    def _getVersionMajor(self):
        """Get the major version of COPASI used to generate the model"""
        return int(self.model.getroot().attrib['versionMajor'])
   
    def _getVersionMinor(self):
        """Get the minor version of COPASI used to generate the model"""
        return int(self.model.getroot().attrib['versionMinor'])
   
    def _getVersionDevel(self):
        """Get the version of COPASI used to generate the model"""
        return int(self.model.getroot().attrib['versionDevel'])
   
    def _getTask(self,task_type, model=None):
        """Get the XML tree representing a task with type: 'type'"""
        if model == None:
            model = self.model
        #Get the task list
        try:
            listOfTasks = model.find(xmlns + 'ListOfTasks')
            assert listOfTasks != None
        except:
            raise
        #Find the appropriate task
        try:
            for task in listOfTasks:
                if (task.attrib['type'] == task_type):
                    foundTask = task
                    break
            assert foundTask != None
        except:
            raise
        return foundTask

    def _clear_tasks(self):
        """Go through the task list, and set all tasks as not scheduled to run"""
        listOfTasks = self.model.find(xmlns + 'ListOfTasks') 
        assert listOfTasks != None
        
        for task in listOfTasks:
            task.attrib['scheduled'] = 'false'
    
    def _get_compartment_name(self, key):
        """Go through the list of compartments and return the name of the compartment with a given key"""
        model = self.model.find(xmlns + 'Model')
        compartments = model.find(xmlns + 'ListOfCompartments')
        for compartment in compartments:
            if compartment.attrib['key'] == key:
                name = compartment.attrib['name']
                break
        assert name != None
        return name
    
    def get_name(self):
        """Returns the name of the model"""
        modelTree = self.model.find(xmlns + 'Model')
        return modelTree.attrib['name']

    def get_timecourse_method(self):
        """Returns the algorithm set for the time course task"""
        timeTask = self._getTask('timeCourse')
        timeMethod = timeTask.find(xmlns + 'Method')
        return timeMethod.attrib['name']

    def get_optimization_method(self):
        """Returns the algorithm set for the optimization task"""
        optTask = self._getTask('optimization')
        optMethod = optTask.find(xmlns + 'Method')
        return optMethod.attrib['name']

    def get_sensitivities_object(self, friendly=True):
        """Returns the single object set for the sensitvities task"""
        sensTask = self._getTask('sensitivities')
        sensProblem = sensTask.find(xmlns + 'Problem')
        parameterGroup = sensProblem.find(xmlns + 'ParameterGroup')
        parameter = parameterGroup.find(xmlns + 'Parameter')
        value_string = parameter.attrib['value']
        
        if friendly:
            #Use a regex to extract the parameter name from string of the format:
            #Vector=Metabolites[E1]
            string = r'Vector=(?P<name>(Reactions|Metabolites|Values)\[.+\])'
            r = re.compile(string)
            search = r.search(value_string)
            if search:
                value_string = search.group('name')
        return value_string
      
    def _get_optimization_object(self):
        """Returns the objective expression for the optimization task"""
        optTask = self._getTask('optimization')
        optProblem = optTask.find(xmlns + 'Problem')
        parameterText = optProblem.find(xmlns + 'ParameterText')
        return parameterText.text.strip()
      
            
    def get_optimization_parameters(self, friendly=True):
        """Returns a list of the parameter names to be included in the sensitvitiy optimization task. Will optionally process names to make them more user friendly"""
        #Get the sensitivities task:
        sensTask=self._getTask('optimization')
        sensProblem = sensTask.find(xmlns + 'Problem')
        optimizationItems = sensProblem.find(xmlns + 'ParameterGroup')
        parameters = []
        for subGroup in optimizationItems:
            name = None
            lowerBound = None
            upperBound = None
            startValue = None
            
            for item in subGroup:
                if item.attrib['name'] == 'ObjectCN':
                    name = item.attrib['value']
                elif item.attrib['name'] == 'UpperBound':
                    upperBound = item.attrib['value']
                elif item.attrib['name'] == 'LowerBound':
                    lowerBound = item.attrib['value']
                elif item.attrib['name'] == 'StartValue':
                    startValue = item.attrib['value']
            assert name !=None
            assert lowerBound != None
            assert upperBound != None
            assert startValue != None
              
            if friendly:
                #Construct a user-friendly name for the parameter name using regexs
                #Look for a match for global parameters: Vector=Values[Test parameter],
                values_string = r'.*Vector=Values\[(?P<name>.*)\].*'
                values_string_re = re.compile(values_string)
                values_match = re.match(values_string_re, name)
                
                if values_match:
                    name = 'Values[' + values_match.group('name') + ']'
                
                else:
                    #else check for a parameter match.
                    #Vector=Reactions[Reaction] Parameter=k1
                    parameter_string = r'.*Vector=Reactions\[(?P<reaction>.*)\].*Parameter=(?P<parameter>.*),Reference=Value.*'
                    parameter_string_re = re.compile(parameter_string)
                    parameter_match = re.match(parameter_string_re, name)
                    
                    if parameter_match:
                        reaction = parameter_match.group('reaction')
                        parameter = parameter_match.group('parameter')
                        name = '(%s).%s'%(reaction, parameter)
                        
                    else:
                        #Try again, this time looking for a string like: Vector=Metabolites[blah]
                        metabolites_string = r'.*Vector=Metabolites\[(?P<name>.*)\].*'
                        metabolites_string_re = re.compile(metabolites_string)
                        metabolites_match = re.match(metabolites_string_re, name)
                        if metabolites_match:
                            name = 'Metabolites[' + metabolites_match.group('name') + ']'

            parameters.append((name, lowerBound, upperBound, startValue))

        return parameters
    
    def get_parameter_estimation_parameters(self, friendly=True):
        """Returns a list of the parameter names to be included in the parameter estimation task. Will optionally process names to make them more user friendly"""
        #Get the sensitivities task:
        fitTask=self._getTask('parameterFitting')
        fitProblem = fitTask.find(xmlns + 'Problem')
        optimizationItems = fitProblem.find(xmlns + 'ParameterGroup')
        parameters = []
        for subGroup in optimizationItems:
            name = None
            lowerBound = None
            upperBound = None
            startValue = None
            
            for item in subGroup:
                if item.attrib['name'] == 'ObjectCN':
                    name = item.attrib['value']
                elif item.attrib['name'] == 'UpperBound':
                    upperBound = item.attrib['value']
                elif item.attrib['name'] == 'LowerBound':
                    lowerBound = item.attrib['value']
                elif item.attrib['name'] == 'StartValue':
                    startValue = item.attrib['value']
            assert name !=None
            assert lowerBound != None
            assert upperBound != None
            assert startValue != None
              
            if friendly:
                #Construct a user-friendly name for the parameter name using regexs
                #Look for a match for global parameters: Vector=Values[Test parameter],
                global_string = r'.*Vector=Values\[(?P<name>.*)\].*'
                global_string_re = re.compile(global_string)
                global_match = re.match(global_string_re, name)
                
                if global_match:
                    name = global_match.group('name')
                
                #else check for a local match.
                #Vector=Reactions[Reaction] Parameter=k1
                local_string = r'.*Vector=Reactions\[(?P<reaction>.*)\].*Parameter=(?P<parameter>.*),Reference=Value.*'
                local_string_re = re.compile(local_string)
                local_match = re.match(local_string_re, name)
                
                if local_match:
                    reaction = local_match.group('reaction')
                    parameter = local_match.group('parameter')
                    name = '(%s).%s'%(reaction, parameter)

            parameters.append((name, lowerBound, upperBound, startValue))

        return parameters
    
    def get_ps_number(self):
        """Returns the number of runs set up for the parameter scan task"""
        scanTask = self._getTask('scan')
        problem = scanTask.find(xmlns+'Problem')
        #scanItems contains a list of parameter groups, each of which represents a scan
        scanItems = problem.find(xmlns + 'ParameterGroup')
        #Now, go through each parameter group and get

        
        scan_number = 0
        for parameterGroup in scanItems:
            for parameter in parameterGroup:
                if parameter.attrib['name'] == 'Number of steps':
                    no_of_steps = int(parameter.attrib['value'])
                if parameter.attrib['name'] == 'Type':
                    type = int(parameter.attrib['value'])
             
            if type == 0:
                #Repeat task. Number of steps is simply the value of no_of_steps
                if scan_number == 0:
                    #If this is the first level of scans
                    scan_number += no_of_steps
                else:
                    scan_number *= no_of_steps
            elif type == 1:
                #Parameter scan task - no of steps is actually given in intervals, so add 1
                if scan_number == 0:
                    scan_number += no_of_steps + 1
                else:
                    scan_number *= no_of_steps + 1
            elif type == 2:
                #Random distribution, do nothing
                pass
        
        return scan_number
        
    
    def _create_report(self, report_type, report_key, report_name):
        """Create a report for a particular task, e.g. sensitivity optimization, with key report_key
        
        report_type: a string representing the job type, e.g. SO for sensitivity optimization"""

        listOfReports = self.model.find(xmlns + 'ListOfReports')
        
        #Check a report with the current key doesn't already exist. If it does, delete it
        foundReport = False
        for report in listOfReports:
            if report.attrib['key'] == report_key:
                foundReport = report
        if foundReport:
            listOfReports.remove(foundReport)

        #Next, look through and check to see if a report with the report_name already exists. If it does, delete it
        
        listOfReports = self.model.find(xmlns + 'ListOfReports')
        foundReport = False
        for report in listOfReports:
            if report.attrib['name'] == report_name:
                foundReport = report
        if foundReport:
            listOfReports.remove(foundReport)

        if report_type == 'SO':

            newReport = etree.SubElement(listOfReports, xmlns + 'Report')
            newReport.set('key', report_key)
            newReport.set('name', report_name)
            newReport.set('taskType', 'optimization')
            newReport.set('seperator', '&#x09;')
            newReport.set('precision', '6')
            
            newReport_Comment = etree.SubElement(newReport, xmlns + 'Comment')
            newReport_Comment_body = etree.SubElement(newReport_Comment, xmlns + 'body')
            newReport_Comment_body.set('xmlns', 'http://www.w3.org/1999/xhtml')
            newReport_Comment_body.text = 'Report automatically generated by condor-copasi'

            #Create the body
            newReport_Body = etree.SubElement(newReport, xmlns + 'Body')

            newReport_Body_Object1 = etree.SubElement(newReport_Body, xmlns + 'Object')
            newReport_Body_Object1.set('cn','String=#----\n')

            newReport_Body_Object2 = etree.SubElement(newReport_Body, xmlns + 'Object')
            newReport_Body_Object2.set('cn','String=Evals \= ')

            newReport_Body_Object3 = etree.SubElement(newReport_Body, xmlns + 'Object')
            newReport_Body_Object3.set('cn','CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Function Evaluations')

            newReport_Body_Object4 = etree.SubElement(newReport_Body, xmlns + 'Object')
            newReport_Body_Object4.set('cn','String=\nTime \= ')

            newReport_Body_Object5 = etree.SubElement(newReport_Body, xmlns + 'Object')
            newReport_Body_Object5.set('cn','CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Timer=CPU Time')

            newReport_Body_Object6 = etree.SubElement(newReport_Body, xmlns + 'Object')
            newReport_Body_Object6.set('cn','String=\n')

            newReport_Body_Object7 = etree.SubElement(newReport_Body, xmlns + 'Object')
            newReport_Body_Object7.set('cn','CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Best Value')
        
            #And put the same objects in the footer
            newReport_Footer = etree.SubElement(newReport, xmlns + 'Footer')

            newReport_Footer_Object1 = etree.SubElement(newReport_Footer, xmlns + 'Object')
            newReport_Footer_Object1.set('cn','String=#----\n')

            newReport_Footer_Object2 = etree.SubElement(newReport_Footer, xmlns + 'Object')
            newReport_Footer_Object2.set('cn','String=Evals \= ')

            newReport_Footer_Object3 = etree.SubElement(newReport_Footer, xmlns + 'Object')
            newReport_Footer_Object3.set('cn','CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Function Evaluations')

            newReport_Footer_Object4 = etree.SubElement(newReport_Footer, xmlns + 'Object')
            newReport_Footer_Object4.set('cn','String=\nTime \= ')

            newReport_Footer_Object5 = etree.SubElement(newReport_Footer, xmlns + 'Object')
            newReport_Footer_Object5.set('cn','CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Timer=CPU Time')

            newReport_Footer_Object6 = etree.SubElement(newReport_Footer, xmlns + 'Object')
            newReport_Footer_Object6.set('cn','String=\n')

            newReport_Footer_Object7 = etree.SubElement(newReport_Footer, xmlns + 'Object')
            newReport_Footer_Object7.set('cn','CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Best Value')
        
        elif report_type == 'SS':
            #Use the following xml string as a template
            report_string = Template(
            """<Report xmlns="http://www.copasi.org/static/schema" key="${report_key}" name="${report_name}" taskType="timeCourse" separator="&#x09;" precision="6">
      <Comment>
        A table of time, variable species particle numbers, variable compartment volumes, and variable global quantity values.
      </Comment>
      <Table printTitle="1">
        
      </Table>
    </Report>"""
            ).substitute(report_key=report_key, report_name=report_name)
            report = etree.XML(report_string)
            model_name = self.get_name()
            
            table = report.find(xmlns + 'Table')
            time_object = etree.SubElement(table, xmlns + 'Object')
            time_object.set('cn', 'Model=' + model_name + ',Reference=Time')
            
            for variable in self.get_variables():
                row = etree.SubElement(table, xmlns + 'Object')
                row.set('cn', variable) 
            
            listOfReports.append(report)
        
        elif report_type == 'OR':
            #Use the following xml string as a template
            report_string = Template(
            """<Report xmlns="http://www.copasi.org/static/schema" key="${report_key}" name="${report_name}" taskType="optimization" separator="&#x09;" precision="6">
      <Comment>
        
      </Comment>
      <Table printTitle="1">
        <Object cn="CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Best Parameters"/>
        <Object cn="CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Best Value"/>
        <Object cn="CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Timer=CPU Time"/>
        <Object cn="CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Function Evaluations"/>
      </Table>
    </Report>"""
            ).substitute(report_key=report_key, report_name=report_name)
            report = etree.XML(report_string)
                        
            listOfReports.append(report)
            
        elif report_type == 'PR':
            #Use the following xml string as a template
            report_string = Template(
            """<Report xmlns="http://www.copasi.org/static/schema" key="${report_key}" name="${report_name}" taskType="parameterFitting" separator="&#x09;" precision="6">
<Comment>
        Condor Copasi automatically generated report.
      </Comment>
      <Table printTitle="1">
        <Object cn="CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Reference=Best Parameters"/>
        <Object cn="CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Reference=Best Value"/>
        <Object cn="CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Timer=CPU Time"/>
        <Object cn="CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Reference=Function Evaluations"/>
      </Table>
    </Report>"""
            ).substitute(report_key=report_key, report_name=report_name)
            report = etree.XML(report_string)
            
            listOfReports.append(report)
            
            
                        
            
        elif report_type == 'SP':
            #Use the following xml string as a template
            report_string = Template(
            """<Report xmlns="http://www.copasi.org/static/schema" key="${report_key}" name="${report_name}" taskType="parameterFitting" separator="&#x09;" precision="6">
<Comment>
        Condor Copasi automatically generated report.
      </Comment>
      <Table printTitle="1">
        <Object cn="CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Reference=Best Parameters"/>
        <Object cn="CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Reference=Best Value"/>
        <Object cn="CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Timer=CPU Time"/>
        <Object cn="CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Reference=Function Evaluations"/>
      </Table>
    </Report>"""
            ).substitute(report_key=report_key, report_name=report_name)
            report = etree.XML(report_string)
            
            listOfReports.append(report)        
        else:
            raise Exception('Unknown report type')
            
    def prepare_so_task(self, subtask_index=1):
        """Generate the files required to perform the sensitivity optimization, 
        
        This involves creating the appropriate temporary .cps files. The .job files are generated seperately"""
        #First clear the task list, to ensure that no tasks are set to run
        self._clear_tasks()
        
        #Next, go to the sensitivities task and set the appropriate variables
        sensTask = self._getTask('sensitivities')
        problem = sensTask.find(xmlns + 'Problem')
        #And open the listofvariables
        for pG in problem:
            if (pG.attrib['name'] == 'ListOfVariables'):
                listOfVariables = pG
        assert listOfVariables != None
        
        #Reset the listOfVariables, and add the appropriate objects
        listOfVariables.clear()
        listOfVariables.set('name', 'ListOfVariables')

        #Add a new child element: <ParameterGroup name='Variables'>
        variables = etree.SubElement(listOfVariables, xmlns + 'ParameterGroup')
        variables.set('name', 'Variables')

        #Add two new children to variables:
        #<Parameter name='SingleObject')
        singleObject = etree.SubElement(variables, xmlns + 'Parameter')
        singleObject.set('name', 'SingleObject')
        singleObject.set('type', 'cn')
        #<Parameter name='ObjectListType'>
        objectListType = etree.SubElement(variables, xmlns + 'Parameter')
        objectListType.set('name', 'ObjectListType')
        objectListType.set('type', 'unsignedInteger')
        objectListType.set('value', '1')
        
        ############
        
        #Next, load the optimization task
        optTask = self._getTask('optimization')
        #And set it scheduled to run, and to update the model
        optTask.attrib['scheduled'] = 'true'
        optTask.attrib['updateModel'] = 'true'
        
        #Find the objective function we wish to change
        problemParameters = optTask.find(xmlns + 'Problem')
        for parameter in problemParameters:
            if (parameter.attrib['name'] == 'ObjectiveExpression'):
                objectiveFunction = parameter
                
            if (parameter.attrib['name'] == 'Maximize'):
                maximizeParameter = parameter
                
            #Set the subtask to sensitivities
            #TODO: At some point allow for other subtasks
            if (parameter.attrib['name'] == 'Subtask'):
                parameter.attrib['value'] = 'CN=Root,Vector=TaskList[Sensitivities]'

        assert objectiveFunction != None
        assert maximizeParameter != None

        #Set the appropriate objective function for the optimization task:
        objectiveFunction.text = '<CN=Root,Vector=TaskList[Sensitivities],Problem=Sensitivities,Array=Scaled sensitivities array[.]>'
        
        ############
        #Create a new report for the optimization task
        report_key = 'condor_copasi_sensitivity_optimization_report'
        self._create_report('SO', report_key, report_key)
        
        #And set the new report for the optimization task
        report = optTask.find(xmlns + 'Report')
    
        #If no report has yet been set, report == None. Therefore, create new report
        if report == None:
            report = etree.Element(xmlns + 'Report')
            optTask.insert(0,report)
        
        report.set('reference', report_key)
        report.set('append', '1')
        
        
        #############
        #get the list of strings to optimize
        #self.get_optimization_parameters(friendly=False) returns a tuple containing the parameter name as the first element
        optimizationStrings = []
        for parameter in self.get_optimization_parameters(friendly=False):
            optimizationStrings.append(parameter[0])
        
        #Build the new xml files and save them
        i = 0
        file_list = []
        for optString in optimizationStrings:
            maximizeParameter.attrib['value'] = '1'
            output = 'output_%d.%d.txt' % (subtask_index, i)
            report.attrib['target'] = output
            
            #Update the sensitivities object
            singleObject.set('value',optString)
            
            target = os.path.join(self.path, 'auto_copasi_%d.%d.cps' %(subtask_index, i))
            
            self.write(target)
            file_list.append(target)
            
            maximizeParameter.attrib['value'] = '0'
            output = 'output_%d.%d.txt' % (subtask_index, i + 1)
            report.attrib['target'] = output
            
            target = os.path.join(self.path, 'auto_copasi_%d.%d.cps' % (subtask_index, i+1))
            self.write(target)
            file_list.append(target)
            i = i + 2
            
        return file_list
        
    def prepare_so_condor_job(self, pool_type, pool_address, subtask_index=1, rank='0', extraArgs=''):
        """Prepare the neccessary .job file to submit to condor for the sensitivity optimization task"""
        #New: only prepares a single job which allows multiple jobs to be queued
        #We must change the ownership of each of the copasi files to the user running this script
        #
        #We assume that we have write privileges on each of the files through our group, but don't have permission to actually change ownership (must be superuser to do this)
        #Thus, we workaround this by copying the original file, deleting the original, and moving the copy back to the original filename
        
#         import shutil
#         for i in range(len(self.get_optimization_parameters())):
#             for max in (0, 1):
#                 copasi_file = os.path.join(self.path, 'auto_copasi_%d.cps' % (2*i + max))
#                 temp_file = os.path.join(self.path, 'temp.cps')
#                 shutil.copy2(copasi_file, temp_file)
#                 os.remove(copasi_file)
#                 os.rename(temp_file, copasi_file)
#                 os.chmod(copasi_file, 0664) #Set as group readable and writable
        
        ############
        #Build the appropriate .job files for the sensitivity optimization task, write them to disk, and make a note of their locations
        condor_jobs = []
        
        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = 'output_%d.$(Process).txt' % subtask_index
        
        n = len(self.get_optimization_parameters()) * 2
        
        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'
        
        
        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file, 
                                                                                   otherFiles='',
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = n,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )
        
        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename
    
    
#         for i in range(len(self.get_optimization_parameters())):
#             for max in (0, 1):
#                 copasi_file = 'auto_copasi_%d.cps' % (2*i + max)
#                 condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiPath=self.binary_dir, copasiFile=copasi_file, otherFiles='', rank=rank)
#                 condor_job_filename = 'auto_condor_%d.job' % (2*i + max)
#                 condor_job_full_filename = os.path.join(self.path, condor_job_filename)
#                 condor_file = open(condor_job_full_filename, 'w')
#                 condor_file.write(condor_job_string)
#                 condor_file.close()
#                 #Append a dict contining (job_filename, std_out, std_err, log_file, job_output and copasi file)
#                 condor_jobs.append({
#                     'spec_file': condor_job_filename,
#                     'std_output_file': str(copasi_file) + '.out',
#                     'std_error_file': str(copasi_file) + '.err',
#                     'log_file': str(copasi_file) + '.log',
#                     'job_output': 'output_%d.txt' % (2*i + max),
#                     'copasi_file': copasi_file,
#                 })
# 
#         return condor_jobs
        
    def get_so_results(self, save=False):
        """Collate the output files from a successful sensitivity optimization run. Return a list of the results"""
        #Read through output files
        parameters=self.get_optimization_parameters(friendly=True)
        parameterRange = range(len(parameters))

        results = []

        for i in parameterRange:
            result = {
                'name': parameters[i][0],
                'max_result': '?',
                'max_evals' : '?',
                'max_cpu' : '?',
                'min_result' : '?',
                'min_evals' : '?',
                'min_cpu' : '?',
            }
            #Read min and max files
            for max in [0, 1]:
                iterator = 0
                
                try:
                    file = open(os.path.join(self.path, 'output_1.%d.txt' % (2*i + max)),'r')
                    output=[None for r in range(4)]
                    for f in file.readlines():
                        value = f.rstrip('\n') #Read the file line by line.
                        #Line 0: seperator. Line 1: Evals. Line 2: Time. Line 3: result
                        index=parameterRange.index(i)
                        output[iterator] = value
                        iterator = (iterator + 1)%4
                    file.close()
                    evals = output[1].split(' ')[2]
                    cpu_time = output[2].split(' ')[2]
                    sens_result = output[3]
                    
                    if max == 0:
                        max_str = 'max'
                    else:
                        max_str = 'min'
                    result[max_str + '_result'] = sens_result
                    result[max_str + '_cpu'] = cpu_time
                    result[max_str + '_evals'] = evals
                    
                except:
                    raise
                    
            results.append(result)
            
        #Finally, if save==True, write these results to file results.txt
        if save:
            if not os.path.isfile(os.path.join(self.path, 'results.txt')):
                results_file = open(os.path.join(self.path, 'results.txt'), 'w')
                header_line = 'Parameter name\tMin result\tMax result\tMin CPU time\tMin Evals\tMax CPU time\tMax Evals\n'
                results_file.write(header_line)
                for result in results:
                    result_line = result['name'] + '\t' + result['min_result'] + '\t' + result['max_result'] + '\t' + result['min_cpu'] + '\t' + result['min_evals'] + '\t' + result['max_cpu'] + '\t' + result['max_evals'] + '\n'
                    results_file.write(result_line)
                results_file.close()
        return results



    def prepare_ss_task(self, runs, repeats_per_job, subtask_index=1):
        """Prepares the temp copasi files needed to run n stochastic simulation runs
        
        """ 
        self._clear_tasks()
        timeTask = self._getTask('timeCourse')
        
        #Letover code from benchmark. This bit sets the time course task report to an empty string
        ############
        #Create a new report for the ss task
        report_key = 'condor_copasi_stochastic_simulation_report'
        self._create_report('SS', report_key, 'auto_ss_report')
        
        #And set the new report for the ss task
        timeReport = timeTask.find(xmlns + 'Report')
    
        #If no report has yet been set, report == None. Therefore, create new report
        if timeReport == None:
            timeReport = etree.Element(xmlns + 'Report')
            timeTask.insert(0,timeReport)
        
        timeReport.set('reference', report_key)
        timeReport.set('append', '1')
        timeReport.set('target', '')
            
        no_of_jobs = int(math.ceil(float(runs) / repeats_per_job))        

        #First clear the task list, to ensure that no tasks are set to run
        self._clear_tasks()
        
        scanTask = self._getTask('scan')
        
        #And set it scheduled to run, and to update the model
        scanTask.attrib['scheduled'] = 'true'
        scanTask.attrib['updateModel'] = 'true'
 
        #Set up the appropriate report for the scan task, and clear the report for the time course task
        timeReport.attrib['target'] = ''

        report = scanTask.find(xmlns + 'Report')
        if report == None:
            report = etree.Element(xmlns + 'Report')
            scanTask.insert(0,report)
        
        report.set('reference', report_key)
        report.set('append', '1')
        
        #Set the XML for the problem task as follows:
#        """<Parameter name="Subtask" type="unsignedInteger" value="1"/>
#        <ParameterGroup name="ScanItems">
#          <ParameterGroup name="ScanItem">
#            <Parameter name="Number of steps" type="unsignedInteger" value="10"/>
#            <Parameter name="Type" type="unsignedInteger" value="0"/>
#            <Parameter name="Object" type="cn" value=""/>
#          </ParameterGroup>
#        </ParameterGroup>
#        <Parameter name="Output in subtask" type="bool" value="1"/>
#        <Parameter name="Adjust initial conditions" type="bool" value="0"/>"""

        #Open the scan problem, and clear any subelements
        scan_problem = scanTask.find(xmlns + 'Problem')
        scan_problem.clear()
        
        #Add a subtask parameter (value 1 for timecourse)
        subtask_parameter = etree.SubElement(scan_problem, xmlns + 'Parameter')
        subtask_parameter.attrib['name'] = 'Subtask'
        subtask_parameter.attrib['type'] = 'unsignedInteger'
        subtask_parameter.attrib['value'] = '1'
        
        #Add a single ScanItem for the repeats
        subtask_pg = etree.SubElement(scan_problem, xmlns + 'ParameterGroup')
        subtask_pg.attrib['name'] = 'ScanItems'
        subtask_pg_pg = etree.SubElement(subtask_pg, xmlns + 'ParameterGroup')
        subtask_pg_pg.attrib['name'] = 'ScanItem'
        
        p1 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p1.attrib['name'] = 'Number of steps'
        p1.attrib['type'] = 'unsignedInteger'
        p1.attrib['value'] = '0'# Assign this later

        
        p2 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p2.attrib['name'] = 'Type'
        p2.attrib['type'] = 'unsignedInteger'
        p2.attrib['value'] = '0'
        
        p3 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p3.attrib['name'] = 'Object'
        p3.attrib['type'] = 'cn'
        p3.attrib['value'] = ''
        
        p4 = etree.SubElement(scan_problem, xmlns+'Parameter')
        p4.attrib['name'] = 'Output in subtask'
        p4.attrib['type'] = 'bool'
        p4.attrib['value'] = '1'
        
        p5 = etree.SubElement(scan_problem, xmlns+'Parameter')
        p5.attrib['name'] = 'Adjust initial conditions'
        p5.attrib['type'] = 'bool'
        p5.attrib['value'] = '0'

        runs_left=runs # Decrease this value as we generate the jobs
        
        model_files = []
        
        for i in range(no_of_jobs):
            #Calculate the number of runs per job. This will either be repeats_per_job, or if this is the last job, runs_left
            
            no_of_steps = min(repeats_per_job, runs_left)
            p1.attrib['value'] = str(no_of_steps)
            runs_left -= no_of_steps
            
            report.set('target', 'output_%d.%d.txt' % (subtask_index, i))
            filename = os.path.join(self.path, 'auto_copasi_%d.%d.cps' % (subtask_index, i))
            self.write(filename)
            model_files.append(filename)
            
            #Also, write a file called filename.runs.txt containing the number of runs per job
            runs_file = open(filename + '.runs.txt', 'w')
            runs_file.write('Repeats per job:\n')
            runs_file.write(str(no_of_steps))
            runs_file.close()
            
        return model_files
            
    def prepare_ss_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index=1, rank='0', extraArgs=''):
        """Prepare the neccessary .job file to submit to condor for the sensitivity optimization task"""
        #New: only prepares a single job which allows multiple jobs to be queued
        #We must change the ownership of each of the copasi files to the user running this script
        #
        #We assume that we have write privileges on each of the files through our group, but don't have permission to actually change ownership (must be superuser to do this)
        #Thus, we workaround this by copying the original file, deleting the original, and moving the copy back to the original filename
        
#         import shutil
#         for i in range(len(self.get_optimization_parameters())):
#             for max in (0, 1):
#                 copasi_file = os.path.join(self.path, 'auto_copasi_%d.cps' % (2*i + max))
#                 temp_file = os.path.join(self.path, 'temp.cps')
#                 shutil.copy2(copasi_file, temp_file)
#                 os.remove(copasi_file)
#                 os.rename(temp_file, copasi_file)
#                 os.chmod(copasi_file, 0664) #Set as group readable and writable
        
        ############
        #Build the appropriate .job files for the sensitivity optimization task, write them to disk, and make a note of their locations
        condor_jobs = []
        
        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = 'output_%d.$(Process).txt' % subtask_index
        
        
        
        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'
        
        
        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file, 
                                                                                   otherFiles='',
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )
        
        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename
        
    def prepare_ss_process_job(self, pool_type, pool_address, jobs, script_path, rank='0'):
        """Collate the results from the stochastic simulation task"""
        ############
        #The rest of the processing is moved to condor, by the file ss_results_process.py
        ############
        
        #Prepare the condor job file
        
        input_file_string = ''
        args_string = ''
        for job in jobs:
            input_file_string += job.job_output + ', '
            args_string += job.job_output + ' '
        input_file_string = input_file_string.rstrip(', ')
        args_string = args_string.rstrip(' ')
        output = 'results.txt'
        
        job_template = Template(condor_spec.condor_string_header + condor_spec.results_process_spec_string)

        job_string = job_template.substitute(pool_type=pool_type,
                                             pool_address=pool_address,
                                             script=script_path,
                                             args=args_string,
                                             input_files=input_file_string,
                                             output='results',
                                             output_files = output,
                                             rank=rank)
        job_filename = 'results.job'
        job_file = open(os.path.join(self.path, job_filename), 'w')
        job_file.write(job_string)
        job_file.close()
        
        return job_filename
        
    def get_variables(self, pretty=False):
        """Returns a list of all variable metabolites, compartments and global quantities in the model.
        
        By default, returns the internal string representation, e.g. CN=Root,Model=Kummer calcium model,Vector=Compartments[compartment],Vector=Metabolites[a],Reference=ParticleNumber. Running pretty=True will parse the string and return a user-friendly version of the names.
        """
        
        output = []
        #Get the model XML tree
        model = self.model.find(xmlns + 'Model')
        #Get list of metabolites
        metabolites = model.find(xmlns + 'ListOfMetabolites')
        
        for metabolite in metabolites:
            name = metabolite.attrib['name']
            simulationType = metabolite.attrib['simulationType']
            compartment_key = metabolite.attrib['compartment']
            
            if simulationType != 'fixed':
                if pretty:
                    output.append(name + ' (Particle Number)')
                else:
                    #Format the metabolite string as: CN=Root,Model=modelname,Vector=Compartments[compartment],Vector=Metabolites[a],Reference=ParticleNumber
                    compartment_name = self._get_compartment_name(compartment_key)
                    model_name = self.get_name()
                    
                    output_template = Template('CN=Root,Model=${model_name},Vector=Compartments[${compartment_name}],Vector=Metabolites[${name}],Reference=ParticleNumber')
                    
                    output_string = output_template.substitute(model_name=model_name, compartment_name=compartment_name, name=name)
                    output.append(output_string)
        #Next, get list of non-fixed compartments:
        compartments = model.find(xmlns + 'ListOfCompartments')
        for compartment in compartments:
            name = compartment.attrib['name']
            simulationType = compartment.attrib['simulationType']
            
            if simulationType != 'fixed':
                if pretty:
                    output.append(name + ' (' + model.attrib['volumeUnit'] + ')')
                else:
                    #format the compartment string as: "CN=Root,Model=Kummer calcium model,Vector=Compartments[compartment_2],Reference=Volume"
                    model_name = self.get_name()
                    output_template = Template('CN=Root,Model=${model_name},Vector=Compartments[${name}],Reference=Volume')
                    output_string = output_template.substitute(model_name=model_name, name=name)
                    output.append(output_string)
                    
        #Finally, get non-fixed global quantities
        values = model.find(xmlns + 'ListOfModelValues')
        #Hack - If no values have been set in the model, use the empty list to avoid a NoneType error
        if values == None:
            values = []
        for value in values:
            name = value.attrib['name']
            simulationType = value.attrib['simulationType']
            
            if simulationType != 'fixed':
                if pretty:
                    output.append(name + ' (Value)')
                else:
                    #format as: CN=Root,Model=Kummer calcium model,Vector=Values[quantity_1],Reference=Value"
                    model_name = self.get_name()
                    output_template = Template('CN=Root,Model=${model_name},Vector=Values[${name}],Reference=Value')
                    output_string = output_template.substitute(model_name=model_name, name=name)
                    output.append(output_string)
                    
        return output
        
    def prepare_ps_jobs(self, subtask_index, time_per_step=None):
        """Prepare the parallel scan task
        
        Efficiently splitting multiple nested scans is a hard problem, and currently beyond the scope of this project.
        As such, we simplify the problem by only splitting along the first scan task. It is the user's prerogative to ensure the scan task is set up in a way that enables the scan task to be efficiently split.
        Because of a limitation with the Copasi scan task -- that there must be at least two parameters for each scan, i.e. min and max, we set the requirement that the first scan must have at least one interval (corresponding to two parameter values), and that when splitting, each new scan must also have a minimum of at least one interval.
        """
        
        def get_range(min, max, intervals, log):
            """Get the range of parameters for a scan."""
            if not log:
                min = float(min)
                max = float(max)
                difference = max-min
                step_size = difference/intervals
                output = [min + i*step_size for i in range(intervals+1)]
                return output
            else:
                from math import log10 as log
                log_min = log(min)
                log_max = log(max)
                log_difference = log_max - log_min
                step_size = log_difference/intervals
                output = [pow(10, log_min + i*step_size) for i in range(intervals+1)]
                return output
                
        
        #First, read in the task
        scanTask = self._getTask('scan')
        self._clear_tasks()
        scanTask.attrib['scheduled'] = 'true'
        problem = scanTask.find(xmlns+'Problem')
        scanTasks = problem.find(xmlns + 'ParameterGroup')
        
        #Find the report for the scan task and store as a variable the node containing it's output
        report = scanTask.find(xmlns+'Report')
        assert report != None
        
        
        #Get the first scan in the list
        firstScan = scanTasks[0]
        
        parameters = {} #Dict to store the parameters that we're interested in reading/changing
        for parameter in firstScan:
            if parameter.attrib['name'] == 'Number of steps':
                parameters['no_of_steps'] = parameter
            if parameter.attrib['name'] == 'Type':
                parameters['type'] = parameter
            if parameter.attrib['name'] == 'Maximum':
                parameters['max'] = parameter
            if parameter.attrib['name'] == 'Minimum':
                parameters['min'] = parameter
            if parameter.attrib['name'] == 'log':
                parameters['log'] = parameter
                    
        #Read the values of these parameters before we go about changing them
        no_of_steps = int(parameters['no_of_steps'].attrib['value'])
        assert no_of_steps > 0
        task_type = int(parameters['type'].attrib['value'])
        if task_type == 1:
            max_value = float(parameters['max'].attrib['value'])
            min_value = float(parameters['min'].attrib['value'])
            if parameters['log'].attrib['value'] == '0':
                log = False
            else:
                log = True
            no_of_steps += 1 #Parameter scans actually consider no of intervals, which is one less than the number of steps, or actual parameter values. We will work with the number of discrete parameter values, and will decrement this value when saving new files
            if time_per_step:
                time_per_step = time_per_step/2

                
            
        #We want to split the scan task up into subtasks of time ~= 10 mins (600 seconds)
        #time_per_job = no_of_steps * time_per_step => no_of_steps = time_per_job/time_per_step
        
        time_per_job = settings.IDEAL_JOB_TIME * 60
        #time_per_job = get_time_per_job(self.job) * 60
        
        if time_per_step:
            #Calculate the number of steps for each job. If this has been calculated as more than the total number of steps originally specified, use this value instead
            no_of_steps_per_job = min(int(round(float(time_per_job) / time_per_step)), no_of_steps)
        else:
            no_of_steps_per_job = 1
            
        #Because of a limitation of Copasi, each parameter must have at least one interval, or two steps per job - corresponding to the max and min parameters
        #Force this limitation:
        if task_type == 1:
            if no_of_steps_per_job < 2:
                no_of_steps_per_job = 2
        
        no_of_jobs = int(math.ceil(float(no_of_steps) / no_of_steps_per_job))
        
#        print 'Benchmarking complete'
#        print '%s steps in total' %no_of_steps
#        print 'Estimated time per step: %s' % time_per_step
#        print 'No of steps per job: %s' % no_of_steps_per_job
        
        ##############
        #Job preparation
        ##############
        
        model_files = [] #Store the relative file names of the model files created here
        
        #Set the model to update
        scanTask.attrib['updateModel'] = 'true'
        #First, deal with the easy case -- where the top-level item is a repeat.

        if task_type == 0:
            step_count = 0
            for i in range(no_of_jobs):
                if no_of_steps_per_job + step_count > no_of_steps:
                    steps = no_of_steps - step_count
                else:
                    steps = no_of_steps_per_job
                step_count += steps
                
                if steps > 0:
                    parameters['no_of_steps'].attrib['value'] = str(steps)
                    report.attrib['target'] = 'output_%d.%d.txt' % (subtask_index, i)
                    filename = 'auto_copasi_%d.%d.cps' % (subtask_index, i)
                    self.write(os.path.join(self.path, filename))
                    model_files.append(filename)
            
        
        
        #Then, deal with the case where we actually scan a parameter
        #Example: parameter range = [1,2,3,4,5,6,7,8,9,10] - min 1, max 10, 9 intervals => 10 steps
        #Split into 3 jobs of ideal length 3, min length 2
        #We want [1,2,3],[4,5,6],[7,8,9,10]
        elif task_type == 1:
            scan_range = get_range(min_value, max_value, no_of_steps-1, log)
            job_scans = []
            for i in range(no_of_jobs):
                #Go through the complete list of parameters, and split into jobs of size no_of_steps_per_job
                job_scans.append(scan_range[i*no_of_steps_per_job:(i+1)*no_of_steps_per_job]) #No need to worry about the final index being outside the list range - python doesn't mind
            
            #If the last job is only of length 1, merge it with the previous job
            assert no_of_jobs == len(job_scans)
            if len(job_scans[no_of_jobs-1]) ==1:
                job_scans[no_of_jobs-2] = job_scans[no_of_jobs-2] + job_scans[no_of_jobs-1]
                del job_scans[no_of_jobs-1]
                no_of_jobs -= 1
            
            #Write the Copasi XML files
            for i in range(no_of_jobs):
                job_scan_range = job_scans[i]
                job_min_value = job_scan_range[0]
                job_max_value = job_scan_range[-1]
                job_no_of_intervals = len(job_scan_range)-1
                
                parameters['min'].attrib['value'] = str(job_min_value)
                parameters['max'].attrib['value'] = str(job_max_value)
                parameters['no_of_steps'].attrib['value'] = str(job_no_of_intervals)
                
                #Set the report output
                report.attrib['target'] = 'output_%d.%d.txt' % (subtask_index, i)
                
                filename = 'auto_copasi_%d.%d.cps' % (subtask_index, i)
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)
        
        return model_files
        
    def prepare_ps_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index=1, rank='0', extraArgs=''):
        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = 'output_%d.$(Process).txt' % subtask_index
        
        
        
        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'
        
        
        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file, 
                                                                                   otherFiles='',
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )
        
        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename
        
    def process_ps_results(self, results_files):
        output_file = open(os.path.join(self.path, 'results.txt'), 'w')
        
        #Copy the contents of the first file to results.txt
        for line in open(os.path.join(self.path, results_files[0]), 'r'):
            output_file.write(line)
        
        #And for all other files, copy everything but the last line
        for result_file in results_files[1:]:
            firstLine = True
            for line in open(os.path.join(self.path, result_file), 'r'):
                if not firstLine:
                    output_file.write(line)
                firstLine = False
                
        output_file.close()
        
        return
        
    def prepare_or_jobs(self, repeats, repeats_per_job, subtask_index):
        """Prepare jobs for the optimization repeat task"""
        
        #First, clear all tasks
        self._clear_tasks()
        
        #Get the optimization task
        optTask = self._getTask('optimization')
        
        #Even though we're not interested in the output at the moment, we'll set a report for the optimization task, or Copasi will complain!
        #Create a new report for the or task
        report_key = 'condor_copasi_optimization_repeat_report'
        self._create_report('OR', report_key, 'auto_or_report')
        
        #And set the new report for the or task
        optReport = optTask.find(xmlns + 'Report')
    
        #If no report has yet been set, report == None. Therefore, create new report
        if optReport == None:
            optReport = etree.Element(xmlns + 'Report')
            optTask.insert(0,optReport)
        
        optReport.set('reference', report_key)
        optReport.set('append', '1')
        optReport.set('target', '')
        
        
        
        no_of_jobs = int(math.ceil(float(repeats) / repeats_per_job))
    
    
        #Clear tasks and set the scan task as scheduled
        self._clear_tasks()
        
        #Get the scan task
        scanTask = self._getTask('scan')
        scanTask.attrib['scheduled'] = 'true'
        scanTask.attrib['updateModel'] = 'true'
        
        #Remove the report output for the optTask to avoid any unwanted output when running the scan task
        optReport.attrib['target'] = ''
        
        #Set the new report for the or task
        report = scanTask.find(xmlns + 'Report')
    
        #If no report has yet been set, report == None. Therefore, create new report
        if report == None:
            report = etree.Element(xmlns + 'Report')
            scanTask.insert(0,report)
        
        report.set('reference', report_key)
        report.set('append', '1')
                     
        #Open the scan problem, and clear any subelements
        scan_problem = scanTask.find(xmlns + 'Problem')
        scan_problem.clear()
        
        #Add a subtask parameter (value 4 for optimization)
        subtask_parameter = etree.SubElement(scan_problem, xmlns + 'Parameter')
        subtask_parameter.attrib['name'] = 'Subtask'
        subtask_parameter.attrib['type'] = 'unsignedInteger'
        subtask_parameter.attrib['value'] = '4'
        
        #Add a single ScanItem for the repeats
        subtask_pg = etree.SubElement(scan_problem, xmlns + 'ParameterGroup')
        subtask_pg.attrib['name'] = 'ScanItems'
        subtask_pg_pg = etree.SubElement(subtask_pg, xmlns + 'ParameterGroup')
        subtask_pg_pg.attrib['name'] = 'ScanItem'
        
        p1 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p1.attrib['name'] = 'Number of steps'
        p1.attrib['type'] = 'unsignedInteger'
        p1.attrib['value'] = '0'# Assign this later

        
        p2 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p2.attrib['name'] = 'Type'
        p2.attrib['type'] = 'unsignedInteger'
        p2.attrib['value'] = '0'
        
        p3 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p3.attrib['name'] = 'Object'
        p3.attrib['type'] = 'cn'
        p3.attrib['value'] = ''
        
        p4 = etree.SubElement(scan_problem, xmlns+'Parameter')
        p4.attrib['name'] = 'Output in subtask'
        p4.attrib['type'] = 'bool'
        p4.attrib['value'] = '1'
        
        p5 = etree.SubElement(scan_problem, xmlns+'Parameter')
        p5.attrib['name'] = 'Adjust initial conditions'
        p5.attrib['type'] = 'bool'
        p5.attrib['value'] = '0'
        
        
        ############
        #Prepare the copasi files
        ############
        
        repeat_count = 0
        model_files = []
        
        for i in range(no_of_jobs):
            if repeats_per_job + repeat_count > repeats:
                no_of_repeats = repeats - repeat_count
            else:
                no_of_repeats = repeats_per_job
            repeat_count += no_of_repeats
            
            #Set the number of repeats for the scan task
            p1.attrib['value'] = str(no_of_repeats)
            report.attrib['target'] = 'output_%d.%d.txt' % (subtask_index, i)
            
            filename = 'auto_copasi_%d.%d.cps' % (subtask_index, i)
            self.write(os.path.join(self.path, filename))
            model_files.append(filename)
        
        return model_files
        
    def prepare_or_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index=1, rank='0', extraArgs=''):
        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = 'output_%d.$(Process).txt' % subtask_index
        
        
        
        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'
        
        
        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file, 
                                                                                   otherFiles='',
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )
        
        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename
        
    def process_or_results(self, filenames):
        """Process the results of the OR task by copying them all into one file, named raw_results.txt.
        As we copy, extract the best value, and write the details to results.txt"""
        
        #Check if we're maximising or minimising
        optTask = self._getTask('optimization')
        problem =  optTask.find(xmlns + 'Problem')
        for parameter in problem:
            if parameter.attrib['name']=='Maximize':
                max_param = parameter.attrib['value']
        if max_param == '0':
            maximize = False
        else:
            maximize = True
        
        output_file = open(os.path.join(self.path, 'raw_results.txt'), 'w')
        

        #Match a string of the format (    0.0995749    0.101685    0.108192    0.091224    )    0.091224    0    
        #Contains parameter values, the best optimization value, the cpu time, and some other values.
        output_string = r'\(\s(?P<params>.+)\s\)\s+(?P<best_value>\S+)\s+(?P<cpu_time>\S+)\.*'
        output_re = re.compile(output_string)
        
        best_value = None
        best_line = None
        
        #Copy the contents of the first file to results.txt
        for line in open(os.path.join(self.path, filenames[0]), 'r'):
            output_file.write(line)
            if line != '\n':
                if output_re.match(line):
                    value = float(output_re.match(line).groupdict()['best_value'])
                    if best_value != None and maximize:
                        if value > best_value:
                            best_value = value
                            best_line = line
                    elif best_value != None and not maximize:
                        if value < best_value:
                            best_value = value
                            best_line = line
                    elif best_value == None:
                        best_value = value
                        best_line = line
            else:
                pass
                
        #And for all other files, copy everything but the last line
        for filename in filenames[1:]:
            firstLine = True
            for line in open(os.path.join(self.path,filename), 'r'):
                if not firstLine:
                    output_file.write(line)
                    if line != '\n':
                        if output_re.match(line):
                            value = float(output_re.match(line).groupdict()['best_value'])
                        if maximize:
                                if value > best_value:
                                    best_value = value
                                    best_line = line
                        elif not maximize:
                                if value < best_value:
                                    best_value = value
                                    best_line = line
                    else:
                        pass
                firstLine = False
                
                
        output_file.close()
        
        #Write the best value to results.txt
        output_file = open(os.path.join(self.path, 'results.txt'), 'w')
        
        output_file.write('Best value\t')
        
        for parameter in self.get_optimization_parameters():

            output_file.write(parameter[0].encode('utf8'))
            output_file.write('\t')
        output_file.write('\n')

        best_line_dict = output_re.match(best_line).groupdict()

        output_file.write(best_line_dict['best_value'])
        output_file.write('\t')
        
        for parameter in best_line_dict['params'].split('\t'):
            output_file.write(parameter)
            output_file.write('\t')
        output_file.close()
        
    def get_or_best_value(self):
        """Read the best value and best parameters from results.txt"""
        best_values = open(os.path.join(self.path, 'results.txt'),'r').readlines()
        
        headers = best_values[0].rstrip('\n').rstrip('\t').split('\t')
        values = best_values[1].rstrip('\n').rstrip('\t').split('\t')
#        print values
        
        output = []
        
        for i in range(len(headers)):
            output.append((headers[i], values[i]))


        return output
        
        
    def prepare_pr_jobs(self, repeats, repeats_per_job, subtask_index, custom_report=False):
        """Prepare jobs for the parameter estimation repeat task"""
        
        
        #Benchmarking.
        #As per usual, first calculate how long a single parameter fit will take
        
        self._clear_tasks()
        fitTask = self._getTask('parameterFitting')
        
        fitTask.attrib['updateModel'] = 'false'
        
        #Even though we're not interested in the output at the moment, we have to set a report for the parameter fitting task, or Copasi will complain!
        #Only do this if custom_report is false
        if not custom_report:
            #Create a new report for the or task
            report_key = 'condor_copasi_parameter_fitting_repeat_report'
            self._create_report('PR', report_key, 'auto_pr_report')
            
        #And set the new report for the or task
        fitReport = fitTask.find(xmlns + 'Report')
    
        if custom_report:
            custom_report_key = fitReport.attrib['reference']
    
    
        #If no report has yet been set, report == None. Therefore, create new report
        if fitReport == None:
            fitReport = etree.Element(xmlns + 'Report')
            fitTask.insert(0,fitReport)
        
        if not custom_report:
            fitReport.set('reference', report_key)
    
        fitReport.set('append', '1')
        fitReport.set('target', '')        

        
            
        no_of_jobs = int(math.ceil(float(repeats) / repeats_per_job))
        
        
        ############
        #Job preparation
        ############
        self._clear_tasks()
        fitReport.attrib['target'] = ''
        #Get the scan task
        scanTask = self._getTask('scan')
        scanTask.attrib['scheduled'] = 'true'
        scanTask.attrib['updateModel'] = 'true'
        #Set the new report for the scan task
        report = scanTask.find(xmlns + 'Report')
    
        #If no report has yet been set, report == None. Therefore, create new report
        if report == None:
            report = etree.Element(xmlns + 'Report')
            scanTask.insert(0,report)
        
        if custom_report:
            report.set('reference', custom_report_key)
        else:
            report.set('reference', report_key)
        report.set('append', '1')
        
        #Prepare the scan task
        
        #Open the scan problem, and clear any subelements
        scan_problem = scanTask.find(xmlns + 'Problem')
        scan_problem.clear()
        
        #Add a subtask parameter (value 5 for parameter estimation)
        subtask_parameter = etree.SubElement(scan_problem, xmlns + 'Parameter')
        subtask_parameter.attrib['name'] = 'Subtask'
        subtask_parameter.attrib['type'] = 'unsignedInteger'
        subtask_parameter.attrib['value'] = '5'
        
        #Add a single ScanItem for the repeats
        subtask_pg = etree.SubElement(scan_problem, xmlns + 'ParameterGroup')
        subtask_pg.attrib['name'] = 'ScanItems'
        subtask_pg_pg = etree.SubElement(subtask_pg, xmlns + 'ParameterGroup')
        subtask_pg_pg.attrib['name'] = 'ScanItem'
        
        p1 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p1.attrib['name'] = 'Number of steps'
        p1.attrib['type'] = 'unsignedInteger'
        p1.attrib['value'] = '0'# Assign this later

        
        p2 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p2.attrib['name'] = 'Type'
        p2.attrib['type'] = 'unsignedInteger'
        p2.attrib['value'] = '0'
        
        p3 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p3.attrib['name'] = 'Object'
        p3.attrib['type'] = 'cn'
        p3.attrib['value'] = ''
        
        p4 = etree.SubElement(scan_problem, xmlns+'Parameter')
        p4.attrib['name'] = 'Output in subtask'
        p4.attrib['type'] = 'bool'
        p4.attrib['value'] = '1'
        
        p5 = etree.SubElement(scan_problem, xmlns+'Parameter')
        p5.attrib['name'] = 'Adjust initial conditions'
        p5.attrib['type'] = 'bool'
        p5.attrib['value'] = '0'
        
        
        ############
        #Prepare the Copasi files
        ############
        model_files = []
        repeat_count = 0
        for i in range(no_of_jobs):
            if repeats_per_job + repeat_count > repeats:
                no_of_repeats = repeats - repeat_count
            else:
                no_of_repeats = repeats_per_job
            repeat_count += no_of_repeats
            
            #Set the number of repeats for the scan task
            p1.attrib['value'] = str(no_of_repeats)
            #And the report target output
            report.attrib['target'] = 'output_%d.%d.txt' % (subtask_index, i)
            
            filename = 'auto_copasi_%d.%d.cps' % (subtask_index, i)
            self.write(os.path.join(self.path, filename))
            model_files.append(filename)
        
        return model_files
        
        
    def prepare_pr_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index, data_files, rank='0', extraArgs=''):
        """Prepare the condor jobs for the parallel scan task"""
        ############
        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = 'output_%d.$(Process).txt' % subtask_index
        
        
        
        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'
        
        input_files_string = ', '
        for data_file in data_files:
            input_files_string += (data_file + ', ')
        input_files_string = input_files_string.rstrip(', ')

        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file, 
                                                                                   otherFiles=input_files_string,
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )
        
        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename
        
    def process_pr_results(self, results_files, custom_report):
        """Process the results of the PR task by copying them all into one file, named raw_results.txt.
        As we copy, extract the best value, and write the details to results.txt"""
        

        
        output_file = open(os.path.join(self.path, 'raw_results.txt'), 'w')
        
        #Keep track of the last read line before a newline; this will be the best value from an optimization run
        last_line = ''
        #Match a string of the format (    0.0995749    0.101685    0.108192    0.091224    )    0.091224    0   100
        #Contains parameter values, the best optimization value, the cpu time, and some other values, e.g. particle numbers that Copasi likes to add. These could be removed, but they seem useful.
        output_string = r'.*\(\s(?P<params>.+)\s\)\s+(?P<best_value>\S+)\s+(?P<cpu_time>\S+)\s+(?P<function_evals>\S+)\.*'
        output_re = re.compile(output_string)
        
        best_value = None
        best_line = None
        
        #Copy the contents of the first file to results.txt
        for line in open(os.path.join(self.path, results_files[0]), 'r'):
            output_file.write(line)
            try:
                if line != '\n':
                    if output_re.match(line):
                        current_value = float(output_re.match(line).groupdict()['best_value'])
                        if best_value != None:
                            if current_value < best_value:
                                best_value = current_value
                                best_line = line
                        elif best_value == None:
                            best_value = current_value
                            best_line = line
                else:
                    pass
            except Exception as e:
                if custom_report:
                    pass
                else:
                    raise e
                
        #And for all other files, copy everything but the last line
        for filename in results_files[1:]:
            firstLine = True
            for line in open(os.path.join(self.path, filename), 'r'):
                if not firstLine:
                    output_file.write(line)
                    try:
                        if line != '\n':
                            if output_re.match(line):
                                current_value = float(output_re.match(line).groupdict()['best_value'])
                                if current_value < best_value:
                                    best_value = current_value
                                    best_line = line
                        else:
                            pass
                    except Exception as e:
                        if custom_report:
                            pass
                        else:
                            raise e
                firstLine = False
                
                
        output_file.close()
        
        #Write the best value to results.txt
        output_file = open(os.path.join(self.path, 'results.txt'), 'w')
        
        output_file.write('Best value\tCPU time\tFunction evals\t')
        
        for parameter in self.get_parameter_estimation_parameters():

            output_file.write(parameter[0].encode('utf8'))
            output_file.write('\t')
        output_file.write('\n')

        best_line_dict = output_re.match(best_line).groupdict()

        output_file.write(best_line_dict['best_value'])
        output_file.write('\t')
        output_file.write(best_line_dict['cpu_time'])
        output_file.write('\t')
        output_file.write(best_line_dict['function_evals'])
        output_file.write('\t')
        
        for parameter in best_line_dict['params'].split('\t'):
            output_file.write(parameter)
            output_file.write('\t')
        output_file.close()
        
        if best_value != None:
            return True
        else:
            return False
        
    def get_pr_best_value(self):
        """Read the best value and best parameters from results.txt"""
        best_values = open(os.path.join(self.path, 'results.txt'),'r').readlines()
        
        headers = best_values[0].rstrip('\n').rstrip('\t').split('\t')
        values = best_values[1].rstrip('\n').rstrip('\t').split('\t')
        
        output = []
        
        for i in range(len(headers)):
            output.append((headers[i], values[i]))


        return output
        
    def create_pr_best_value_model(self, subtask_index, custom_report=False):
        """Create a .CPS model containing the best parameter values found by the PR task, and save it to filename"""
        #We do this in an indirect way - set up the parameter estimation task again, set to executable,
        # set the start values as the best values found by the task, set to current solution statistics,
        # set to update model, and run.
        
        #Step 1 - set up the parameter estimation task
        
        #Clear all tasks
        self._clear_tasks()
        
        #get the parameter estimation task

        fitTask = self._getTask('parameterFitting')
        
        fitTask.attrib['scheduled'] = 'true'
        fitTask.attrib['updateModel'] = 'true'
        
        #Even though we're not interested in the output at the moment, we have to set a report for the parameter fitting task, or Copasi will complain!
        #Only do this if custom_report is false
        if not custom_report:
            #Create a new report for the or task
            report_key = 'condor_copasi_parameter_fitting_repeat_report'
            self._create_report('PR', report_key, 'auto_pr_report')
            
        #And set the new report for the or task
        fitReport = fitTask.find(xmlns + 'Report')
    
        if custom_report:
            custom_report_key = fitReport.attrib['reference']
    
    
        #If no report has yet been set, report == None. Therefore, create new report
        if fitReport == None:
            fitReport = etree.Element(xmlns + 'Report')
            fitTask.insert(0,fitReport)
        
        if not custom_report:
            fitReport.set('reference', report_key)
    
        fitReport.set('append', '1')
        fitReport.set('target', 'copasi_temp_output.txt')   
        
        ########
        #Step 2 - go through the parameter fitting task, and update the parameter start values
        
        fitProblem = fitTask.find(xmlns + 'Problem')
        
        randomizeStartValue = None
        for parameter in fitProblem.iterfind(xmlns + 'Parameter'):
            if parameter.attrib['name'] == 'Randomize Start Values':
                randomizeStartValue = parameter
                break;
        randomizeStartValue.attrib['value'] = '0'

        itemList = None
        for group in fitProblem.iterfind(xmlns + 'ParameterGroup'):
            if group.attrib['name'] == 'OptimizationItemList':
                itemList = group
                break
        assert itemList != None

        #get the best parameter values from results.txt. We'll assume they're in the same order, so we don't need to check the names
        best_parameter_values = self.get_pr_best_value()
        
        #Index 0 = best value, 1 = CPU time, 2 = Function Evals, 3...n+3 = parameter values
        #Therefore, start at 3
        parameter_index = 3


        #Get each parameter
        for parameterGroup in itemList.iterfind(xmlns + 'ParameterGroup'):
            if parameterGroup.attrib['name'] != 'FitItem':
                continue
            
            startValue = None
            for parameter in parameterGroup.iterfind(xmlns + 'Parameter'):
                if parameter.attrib['name'] == 'StartValue':
                    startValue = parameter
                    break
            assert startValue != None

            #Set the start value:
            startValue.attrib['value'] = best_parameter_values[parameter_index][1]
            
            parameter_index += 1
        
        ########
        #Step 3 - get the method, and set to current solution statistics
        
        method = fitTask.find(xmlns + 'Method')
        method.clear()
        method.attrib['name'] = 'Current Solution Statistics'
        method.attrib['type'] = 'CurrentSolutionStatistics'
        
        #Save to filename
        
        filename = 'auto_copasi_%d.0.cps' % subtask_index
        self.write(os.path.join(self.path, filename))

        return filename
    
    def prepare_pr_optimal_model_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index, data_files, rank='0', extraArgs=''):
        """Prepare the condor jobs for the parallel scan task"""
        ############
        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = ''
        
        
        
        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'
        
        input_files_string = ', '
        for data_file in data_files:
            input_files_string += (data_file + ', ')
        input_files_string = input_files_string.rstrip(', ')

        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file, 
                                                                                   otherFiles=input_files_string,
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )
        
        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename
        
        
        

        
    def prepare_rw_jobs(self, repeats):
        """Prepare the jobs for the new raw mode.
         
        We assume that the model file is already set up for raw mode, i.e. at least one task marked as executable, reports set etc.
        Therefore, all we need to do is, for each repeat, append the report name with an appropriate suffix so the names are unique"""
        
         
        #The tasks we need to go through to append the report output
        taskList = [
            'steadyState',
            'timeCourse',
            'scan',
            'metabolicControlAnalysis',
            'optimization',
            'parameterFitting',
            'fluxMode',
            'lyapunovExponents',
            'timeScaleSeparationAnalysis',
            'sensitivities',
            'moieties'
            ]
        
        
        task_report_targets = {} #Store the report output targets 
        #Create a new COPASI file for each repeat
        #Keep a note of the output files we're creating
        model_files = []
        output_files = []
        for i in range(repeats):
            #For each task, if the report output is set, append it with '_i'
            for taskName in taskList:
                try:
                    task = self._getTask(taskName)
                    report = task.find(xmlns + 'Report')
                    if i==0:
                        task_report_targets[taskName] = report.attrib['target']
                    report.attrib['target'] = str(i) + '_' + task_report_targets[taskName]
                    if i==0:
                        if task.attrib['scheduled'] == 'true':
                            output_files.append(task_report_targets[taskName])
                    
                except:
                    pass #It's possible not every task has a report set. If this is the case, ignore it!
                    
            filename = 'auto_copasi_1.%d.cps'%i
            target = os.path.join(self.path, filename)
            model_files.append(filename)
            
            self.write(target)
         
        return model_files, output_files



    
    def prepare_rw_condor_job(self, pool_type, address, repeats, raw_mode_args, data_files, output_files, rank='0'):
        """Prepare the condor jobs for the raw mode task"""
        
        #Prepare a customized condor job string
        #Somewhat confusingly, the original string was called raw_condor_string
        #We'll call this one raw_mode_string_with_args
        
        #We want to substitute '$filename' to ${copasiFile}
        args_string = Template(raw_mode_args).substitute(filename = '${copasiFile}', new_filename='run_${copasiFile}')

        raw_mode_string_with_args = Template(condor_spec.raw_mode_string).safe_substitute(args=args_string)
        
        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'

        
        #Build up a string containing a comma-seperated list of data files
        input_files_string = ', '
        output_files_string = ' ,'
        for data_file in data_files:
            input_files_string += data_file + ', '
        #And the same for the output files
        for output_file in output_files:
            output_files_string += '$(Process)_' + output_file + ', '
        input_files_string = input_files_string.rstrip(', ')
        output_files_string = output_files_string.rstrip(', ')
        ############
        #Build the appropriate .job file for the raw task
        copasi_file = 'auto_copasi_1.$(Process).cps'
        
        condor_job_string = Template(raw_mode_string_with_args).substitute(pool_type=pool_type,
                                                                           pool_address=address,
                                                                           binary_dir=binary_dir,
                                                                           transfer_executable=transfer_executable,
                                                                           copasiFile=copasi_file,
                                                                           otherFiles=input_files_string,
                                                                           outputFile=output_files_string,
                                                                           n=repeats,
                                                                           extraArgs='',
                                                                           rank=rank,
                                                                           )
        
        condor_job_filename = 'auto_condor_1.job'
        condor_file = open(os.path.join(self.path, condor_job_filename), 'w')
        condor_file.write(condor_job_string)
        condor_file.close()


        return condor_job_filename
    
    def prepare_sp_jobs(self, no_of_jobs, skip_load_balancing=False, custom_report=False):
        """Prepare jobs for the sigma point method"""
        import shutil
        i=0
        
        #ALTER -- Bring back skip_load_balancing?  
        
        
        #Benchmarking.
        #As per usual, first calculate how long a single parameter fit will take
        
        self._clear_tasks()                #Program stops here.
        
        
        fitTask = self._getTask('parameterFitting')
        fitTask.attrib['scheduled'] = 'true'
        fitTask.attrib['updateModel'] = 'false'
        
        #Even though we're not interested in the output at the moment, we have to set a report for the parameter fitting task, or Copasi will complain!
        #Only do this if custom_report is false
        #if not custom_report:
        #Create a new report for the or task
        report_key = 'condor_copasi_parameter_fitting_repeat_report'
        self._create_report('SP', report_key, 'auto_pr_report')
            
        #And set the new report for the or task
        fitReport = fitTask.find(xmlns + 'Report')
        if custom_report:
            custom_report_key = fitReport.attrib['reference']
    
    
        #If no report has yet been set, report == None. Therefore, create new report
        if fitReport == None:
            fitReport = etree.Element(xmlns + 'Report')
            fitTask.insert(0,fitReport)
        
        
        #if not custom_report:
        fitReport.set('reference', report_key)
    
        fitReport.set('append', '1')
        fitReport.set('target', 'copasi_temp_output.txt')     
        
        '''
        if not skip_load_balancing:
            import tempfile
            tempdir = tempfile.mkdtemp()
            
            temp_filename = os.path.join(tempdir, 'auto_copasi_temp.cps')
            
            #Copy the data file(s) over to the temp dir
            import shutil
            for data_file_line in open(os.path.join(self.path, 'data_files_list.txt'),'r'):
                data_file = data_file_line.rstrip('\n')
                shutil.copy(os.path.join(self.path, data_file), os.path.join(tempdir, data_file))
            
            #Write a temp XML file
            self.write(temp_filename)
            
            #Note the start time
            start_time = time.time()
            self._copasiExecute(temp_filename, tempdir, timeout=int(settings.IDEAL_JOB_TIME*60))
            finish_time = time.time()
            time_per_step = finish_time - start_time
            
            #Remove the temp directory tree
            shutil.rmtree(tempdir)

            
            #We want to split the scan task up into subtasks of time ~= 10 mins (600 seconds)
            #time_per_job = repeats_per_job * time_per_step => repeats_per_job = time_per_job/time_per_step
            
            time_per_job = settings.IDEAL_JOB_TIME * 60
            
            #Calculate the number of repeats for each job. If this has been calculated as more than the total number of steps originally specified, use this value instead
            repeats_per_job = min(int(round(float(time_per_job) / time_per_step)), repeats)

        else:
            repeats_per_job = 1
        #no_of_jobs = int(math.ceil(float(repeats) / repeats_per_job))
        '''
        ############
        #Job preparation
        ############
        
        self._clear_tasks()    #This also stops the program.
        
        
        fitReport.attrib['target'] = ''
        # Hack - Copasi does not update parameters if only update model set in scan, so we have to set it also in parameterFitting task
        #Get the parameter estimation task
        fitTask = self._getTask('parameterFitting')


        fitTask.attrib['updateModel'] = 'false'
        #Get the scan task
        scanTask = self._getTask('scan')
        
        
        scanTask.attrib['scheduled'] = 'true'
        scanTask.attrib['updateModel'] = 'false'

        #Set the new report for the scan task
        report = scanTask.find(xmlns + 'Report')
        
        #If no report has yet been set, report == None. Therefore, create new report
        if report == None:
            report = etree.Element(xmlns + 'Report')
            scanTask.insert(0,report)
        
        
        if custom_report:
            report.set('reference', custom_report_key)
            
        else:
            report.set('reference', report_key)
            report.set('append', '1')
        
        #Prepare the scan task
        #Open the scan problem, and clear any subelements
        scan_problem = scanTask.find(xmlns + 'Problem')
        scan_problem.clear()
        
        
        #Add a subtask parameter (value 5 for parameter estimation)
        subtask_parameter = etree.SubElement(scan_problem, xmlns + 'Parameter')
        subtask_parameter.attrib['name'] = 'Subtask'
        subtask_parameter.attrib['type'] = 'unsignedInteger'
        subtask_parameter.attrib['value'] = '5'
        
        
        #Add a single ScanItem for the repeats
        subtask_pg = etree.SubElement(scan_problem, xmlns + 'ParameterGroup')
        subtask_pg.attrib['name'] = 'ScanItems'
        subtask_pg_pg = etree.SubElement(subtask_pg, xmlns + 'ParameterGroup')
        subtask_pg_pg.attrib['name'] = 'ScanItem'
        p1 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p1.attrib['name'] = 'Number of steps'
        p1.attrib['type'] = 'unsignedInteger'
        p1.attrib['value'] = '0'# Assign this later

        
        p2 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p2.attrib['name'] = 'Type'
        p2.attrib['type'] = 'unsignedInteger'
        p2.attrib['value'] = '0'
        
        p3 = etree.SubElement(subtask_pg_pg, xmlns+'Parameter')
        p3.attrib['name'] = 'Object'
        p3.attrib['type'] = 'cn'
        p3.attrib['value'] = ''
        
        p4 = etree.SubElement(scan_problem, xmlns+'Parameter')
        p4.attrib['name'] = 'Output in subtask'
        p4.attrib['type'] = 'bool'
        p4.attrib['value'] = '1'
        
        p5 = etree.SubElement(scan_problem, xmlns+'Parameter')
        p5.attrib['name'] = 'Adjust initial conditions'
        p5.attrib['type'] = 'bool'
        p5.attrib['value'] = '0'
        
                
        ############
        #Prepare the Copasi files
        ############
        
        repeat_count = 0
        
        for j in range(no_of_jobs):
            '''if repeats_per_job + repeat_count > repeats:
                no_of_repeats = repeats - repeat_count
            else:
                no_of_repeats = repeats_per_job
            repeat_count += no_of_repeats
            '''
            #Set the number of repeats for the scan task
            #ALTER think this should be 1.
            p1.attrib['value'] = str(1)
            #And the report target output
            report.attrib['target'] = str(j) + '_out.txt'
            
            filename = os.path.join(self.path, str(j), 'auto_copasi_' + str(j) +'.cps')
            self.write(filename)
                    
        return no_of_jobs
        
        
    def prepare_sp_condor_jobs(self, jobs, rank='0'):
        """Prepare the condor jobs for the parallel scan task"""
        ############
        #Build the appropriate .job files for the sensitivity optimization task, write them to disk, and make a note of their locations
        condor_jobs = []
        
        #Build up a string containing a comma-separated list of data files
        files_string = ','
        for data_file_line in open(os.path.join(self.path, 'data_files_list.txt'), 'r'):
            data_file = data_file_line.rstrip('\n')
            files_string += data_file + ','
        

        files_string = files_string.rstrip(',')

        
        for i in range(jobs):
            copasi_file = Template('auto_copasi_$index.cps').substitute(index=i)
            #In addition to the copasi file, also transmit the data files. These are listed in files_string
            condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiPath=self.binary_dir, copasiFile=copasi_file, otherFiles=files_string, rank=rank)            
            condor_job_filename = os.path.join(self.path, str(i), Template('auto_condor_$index.job').substitute(index=i))
            condor_file = open(condor_job_filename, 'w')
            condor_file.write(condor_job_string)
            condor_file.close()
            #Append a dict contining (job_filename, std_out, std_err, log_file, job_output)
            condor_jobs.append({
                'spec_file': condor_job_filename,
                'std_output_file': str(copasi_file) + '.out',
                'std_error_file': str(copasi_file) + '.err',
                'log_file': str(copasi_file) + '.log',
                'job_output': str(i) + '_out.txt'
            })
            
            

        return condor_jobs
        
    def process_sp_results(self, jobs, custom_report=False):
        """Calculates the mean, covariance, and coefficients of variation for the parameters from the results of the parameter estimation tasks.  Prints these results to three files.  All equations numbers reference "Optimal experimental design with the sigma point method" (2009) by Schenkendorf, et. al."""
        
        ##ALTER --- figure out how to remove the commented lines without indentation errors...
        #    it looks like we also don't have permission to delete the auto_copasi files, which really balloons memory demand.
        
        
        #Keep track of the last read line before a newline; this will be the best value from an optimization run
        last_line = ''
        #Match a string of the format (    0.0995749    0.101685    0.108192    0.091224    )    0.091224    0   100
        #Contains parameter values, the best optimization value, the cpu time, and some other values, e.g. particle numbers that Copasi likes to add. These could be removed, but they seem useful.
        output_string = r'.*\(\s(?P<params>.+)\s\)\s+(?P<best_value>\S+)\s+(?P<cpu_time>\S+)\s+(?P<function_evals>\S+)\.*'
        output_re = re.compile(output_string)
        
        best_value = None
        best_line = None
        
        #Copy the contents of the first file to results.txt
        for j in range(jobs):
            for line in open(os.path.join(self.path, str(j), str(j)+'_out.txt'), 'r'):  
                try:
                    if line == '\n':
                        last_value = output_re.match(last_line).groupdict()['best_value']
                        if best_value != None:
                            if last_value < best_value:
                                best_value = last_value
                                best_line = last_line
                        elif best_value == None:
                            best_value = last_value
                            best_line = last_line
                    else:
                        last_line = line
                except:
                    if custom_report:
                        t=0#pass ALTER
                    else:
                        t=0#raise
                   
            #And for all other files, copy everything but the last line
            '''for i in range(jobs)[1:]:
                firstLine = True
                for line in open(os.path.join(self.path, str(i), str(i) + '_out.txt'), 'r'):
                    if not firstLine:
                        output_file.write(line)
                        try:
                            if line == '\n':
                                last_value = output_re.match(last_line).groupdict()['best_value']
                                if last_value < best_value:
                                    best_value = last_value
                                    best_line = last_line
                            else:
                                last_line = last_line
                        except:
                            if custom_report:
                                pass
                            else:
                                raise
                    firstLine = False'''                    
                    
            
            #Write the best value to results.txt
            output_file = open(os.path.join(self.path, str(j), str(j)+'_results.txt'), 'w')
            
            output_file.write('Best value\tCPU time\tFunction evals\t')
            
            for parameter in self.get_parameter_estimation_parameters():

                output_file.write(parameter[0])
                output_file.write('\t')
            output_file.write('\n')

            best_line_dict = output_re.match(best_line).groupdict()

            output_file.write(best_line_dict['best_value'])
            output_file.write('\t')
            output_file.write(best_line_dict['cpu_time'])
            output_file.write('\t')
            output_file.write(best_line_dict['function_evals'])
            output_file.write('\t')
            
            for parameter in best_line_dict['params'].split('\t'):
                output_file.write(parameter)
                output_file.write('\t')
            output_file.close()
        
        ####
        
      
        
        i = 0
        dir = os.path.join(self.path, '')
        parameters = self.get_parameter_estimation_parameters()
        number_of_parameters = len(parameters)    
        storage = [[0]*number_of_parameters for x in xrange(jobs)]
   
        
        with open(os.path.join(dir, 'ScalingFactors.txt')) as scaling_factors_list:
            factor_array = scaling_factors_list.read().split('\n')
            scaling_factors_list.close()
        
        alpha = float(factor_array[0])
        beta = float(factor_array[1])
        kappa = float(factor_array[2])
        measurement_error = float(factor_array[3])
        data_points = float(factor_array[4])
        
        scaling_factors_list.close()
        
        lambd=alpha*alpha*(data_points+kappa)-data_points
        lambdterm=math.sqrt(data_points+lambd)
        
        m_weight_0 = lambd/(data_points+lambd)                                #0th mean weight in (30)
        c_weight_0 = lambd/(data_points+lambd)+1-(alpha*alpha)+beta            #0th covariance weight in (31)
        i_weight = (1/(2*(data_points+lambd)))                              #ith weight in (32)
       
       
        #Stores the results from all parameter estimation tasks in a 2D array
        for k in range(jobs):
            
            number=0
            with open(os.path.join(dir, str(k), str(k)+'_results.txt')) as data_list:
                raw_data  = data_list.read().rstrip('\t').split('\t')
                
                #Skips the header (number_of_parameters + 3) and the values for 'Best value', 'CPU time,' 'Function evaluations' (3). 
                start = number_of_parameters + 6            
                for value in raw_data[(start):]:
                    
                    storage[i][number] = float(value)
                    number=number+1
            
                
            i = i+1
            data_list.close()
            
        #TODO:iweight variable referenced below before assigment
        #Find out what this actually should be
        iweight=1

        #Calculates the mean vector in (28) and the covariance matrix cov in (29)
        mean = [0] * number_of_parameters
        covariance = [[0]*number_of_parameters for x in xrange(number_of_parameters)]

        if kappa > 0:                   #Excludes the initial data set stored in the jobs-1 directory
            #Mean           
            for j in range(number_of_parameters):
                sum =0
                for l in range(jobs)[:-1]:                         
                    sum = sum + storage[l][j]
                mean[j]=sum*i_weight
                sum = sum + m_weight_0*storage[jobs-1][j]
                
            #Covariance    
            for p in range(0, number_of_parameters):
                for m in range(0, number_of_parameters):
                    sum = 0
                    for q in range(jobs)[:-1]:
                        sum = sum + (iweight * (storage[q][p] - mean[p]) * (storage[q][m] - mean[m]))
                    sum = sum + (c_weight_0 * (storage[jobs-1][p] - mean[p]) * (storage[jobs-1][m] - mean[m]))
                    covariance[p][m] = sum                    
                

        else:
            #Mean
            for j in range(number_of_parameters):
                sum = 0
                for l in range(jobs):
                    sum = sum + storage[l][j]
                mean[j]=sum*i_weight
            
            
            #Covariance              
            for p in range(number_of_parameters):
                for m in range(number_of_parameters):
                    sum = 0
                    for q in range(jobs):
                        sum = sum + (i_weight * (storage[q][p] - mean[p]) * (storage[q][m] - mean[m]))
                    covariance[p][m] = sum
                
        
        
        #Calculates the coefficients of variation.
        coefficient_of_variation = [0] * number_of_parameters
        for i in range(number_of_parameters):
            coefficient_of_variation[i] = (math.sqrt(covariance[i][i]))/(abs(mean[i]+0.0))
            #Since the noisy data is truncated at values less than 0, we get negative values for the mean.  This problem may also involve the scaling factors..
        
       
        
        #Calculates the bias.
        bias = [0] * number_of_parameters
        for i in range(number_of_parameters):
            bias[i] = mean[i] - storage[jobs-1][i]
        
        #Print the values of each vector to its respective file:
                
        
        mean_string = ''
        coefficient_string = ''
        covariance_string =''
        bias_string=''
        head_string =''
        
        
        
        #Adds the horizontal headers
        for parameter in parameters:
            head_string = head_string + str(parameter[0]) + '\t'
        head_string.rstrip('\t')
            
          
            
        mean_string = head_string+'\n'
        coefficient_string = head_string +'\n'
        covariance_string = '\t'+ head_string + '\n'
        bias_string = head_string + '\n'
        
        #Diagnostic - prints the storage matrix to all_tasks.txt
        with open(os.path.join(dir, 'all_tasks.txt'),'w') as storage_text:
            storage_text.write(head_string+'\n')
            for i in storage:
                for element in i:
                    storage_text.write(str(element)+'\t')
                storage_text.write('\n')
        storage_text.close()
        

        
        #Adds the values to mean
        for i in mean:
            mean_string = mean_string + str(i) + '\t'
        mean_string = mean_string.rstrip('\t')
        
        
        #Adds the vertical header and the values to the covariance matrix.
        index = 0
        for i in covariance:
            covariance_string = covariance_string + str(parameters[index][0])+'\t'
            index = index+1
            for j in i:
                covariance_string = covariance_string + str(j) + '\t'
            covariance_string = covariance_string.rstrip('\t')
            covariance_string = covariance_string + '\n'

        covariance_string = covariance_string.rstrip('\n')       
        
       
        #Adds the values to coefficients of variation
        for i in coefficient_of_variation:
            coefficient_string = coefficient_string + str(i) + '\t'
        coefficient_string = coefficient_string.rstrip('\t')
        

        
        #Adds the values to the bias
        for i in bias:
            bias_string = bias_string + str(i) + '\t'
        bias_string = bias_string.rstrip('\t')
        
   
        
        #Writes mean, covariance, and coefficients of variation to their respective files and also to a single file results.txt
        out_file_coefficient = open(os.path.join(dir, '', 'coefficients_of_variation.txt'),'w')
        out_file_covariance= open(os.path.join(dir, '', 'covariance.txt'),'w')
        out_file_mean = open(os.path.join(dir, '', 'mean.txt'),'w')
        out_file_bias = open(os.path.join(dir, '', 'bias.txt'),'w')
        out_file_results = open(os.path.join(dir, '', 'results.txt'), 'w')
        out_file_mean.write(mean_string)        
        out_file_coefficient.write(coefficient_string)
        out_file_covariance.write(covariance_string)
        out_file_bias.write(bias_string)
        out_file_results.write('Mean' + '\n' + mean_string + '\n' + '\n' + '\n' + 'Coefficients' + '\n' + coefficient_string + '\n' + '\n' + '\n' + 'Biases' + '\n' + bias_string + '\n' + '\n' + '\n' + 'Covariances' + '\n' + covariance_string)
        out_file_mean.close()
        out_file_coefficient.close()
        out_file_covariance.close()
        out_file_bias.close()
        out_file_results.close()
              

        
    def get_sp_mean(self):
        """Read the mean values from mean.txt"""
        best_values = open(os.path.join(self.path, 'mean.txt'),'r').readlines()
        
        headers = best_values[0].rstrip('\n').rstrip('\t').split('\t')
        values = best_values[1].rstrip('\n').rstrip('\t').split('\t')
#        print values
        
        output = []
        
        for i in range(len(headers)):
            output.append((headers[i], values[i]))


        return output
    
