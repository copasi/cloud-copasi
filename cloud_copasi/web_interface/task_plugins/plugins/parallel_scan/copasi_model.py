#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from copasi.model import CopasiModel
from copasi import model
from cloud_copasi import settings
from lxml import etree
import os, time, math

xmlns = model.xmlns

class PSCopasiModel(CopasiModel):

    def prepare_ps_load_balancing(self, repeats=None):
        """Prepare copasi model files that can be used for the benchmarking step

        First sets up the scan task with a repeat. Write 3 files with 1, 10 and 100 repeats respectively
        """

        if not repeats:
            repeats = [1, 10, 100, 1000]



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

        ############
        #Benchmarking
        ############
        #Set report output to be something
        report.attrib['target'] = 'output'

        import tempfile
        #Set the number of steps as 1, 10, 100, 1000, and write files

        for repeat in repeats:
            filename=os.path.join(self.path, 'load_balancing_%d.cps' % repeat)

            parameters['no_of_steps'].attrib['value'] = '%d'%repeat

            self.write(filename)


        #############################
        return ['load_balancing_%d.cps' % repeat for repeat in repeats]

    def get_number_of_intervals(self):
        """Get the number of intervals set for the top level scan task
        """
        #First, read in the task
        scanTask = self._getTask('scan')
        problem = scanTask.find(xmlns+'Problem')
        scanTasks = problem.find(xmlns + 'ParameterGroup')

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

        return no_of_steps
