#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from basico import *
from cloud_copasi.copasi.model import *
from cloud_copasi.copasi import model
from cloud_copasi import settings
from lxml import etree
import os, time, math

xmlns = model.xmlns

class PRCopasiModel(CopasiModel):

    def prepare_pr_load_balancing(self, repeats=None):
        """Prepare copasi model files that can be used for the benchmarking step

        First sets up the scan task with a repeat. Write 3 files with 1, 10 and 100 repeats respectively
        """

        if not repeats:
            repeats = [1, 10, 100, 1000]



        #Benchmarking.
        #As per usual, first calculate how long a single parameter fit will take

        self._clear_tasks()
        fitTask = self._getTask('parameterFitting')

        #Even though we're not interested in the output at the moment, we have to set a report for the parameter fitting task, or Copasi will complain!
        #Only do this if custom_report is false
        #Create a new report for the or task
        report_key = 'condor_copasi_parameter_fitting_repeat_report'
        self._create_report('PR', report_key, 'auto_pr_report')

        #And set the new report for the or task
        fitReport = fitTask.find(xmlns + 'Report')


        #If no report has yet been set, report == None. Therefore, create new report
        if fitReport == None:
            fitReport = etree.Element(xmlns + 'Report')
            fitTask.insert(0,fitReport)

        fitReport.set('reference', report_key)

        fitReport.set('append', '1')
        fitReport.set('target', '') #No output for this task

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

        for repeat in repeats:
            #Write a new file with 1, 10 and 100 repeats

            #Set the number of repeats for the scan task
            p1.attrib['value'] = str(repeat)
            report.attrib['target'] = str(repeat) + '_out.txt'

            filename = os.path.join(self.path, 'load_balancing_' + str(repeat) + '.cps')
            self.write(filename)


        return ['load_balancing_%d.cps' % repeat for repeat in repeats]

class PRCopasiModel_BasiCO(CopasiModel_BasiCO):

    def prepare_pr_load_balancing(self, repeats=None):

        if not repeats:
            repeats = [1, 10, 100, 1000]

        self._clear_tasks()
        fitTask = get_fit_parameters()

        report_key = None
        self._create_report('PR', report_key, 'auto_pr_report')

        self.scan_items[0]['num_steps'] = 0
        self.scan_items[0]['type'] = 'repeat'


        set_scan_settings(
                          scheduled = True,
                          update_model = True,
                          cn='',
                          subtask = 'Parameter Estimation',
                          output_during_subtask = True,
                          adjust_initial_conditions = False,
                          scan_items = self.scan_items,
                        )


        assign_report('auto_pr_report', task=T.SCAN, append=True)
        assign_report('auto_pr_report', task=T.PARAMETER_ESTIMATION, append=True)

        for repeat in repeats:
            # filename = os.path.join(self.path, 'load_balancing_%d.cps' %repeat) #for production
            filename = os.path.join(os.getcwd(), 'load_balancing_%d.cps' %repeat) #for pythonHelp
            target = str(repeat) + '_out.txt'
            assign_report('auto_pr_report', task=T.SCAN, filename=target, append=True, confirm_overwrite = False)
            self.scan_items[0]['num_steps'] = repeat
            set_scan_items(self.scan_items)
            self.write(filename)

        return ['load_balancing_%d.cps' % repeat for repeat in repeats]
