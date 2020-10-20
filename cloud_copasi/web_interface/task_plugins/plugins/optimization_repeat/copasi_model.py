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

class ORCopasiModel(CopasiModel):

    def prepare_or_load_balancing(self, repeats=None):
        """Prepare copasi model files that can be used for the benchmarking step

        First sets up the scan task with a repeat. Write 3 files with 1, 10 and 100 repeats respectively
        """

        if not repeats:
            repeats = [1, 10, 100, 1000]
        #Clear tasks and set the scan task as scheduled
        self._clear_tasks()
        optTask = self._getTask('optimization')

        #Create a report
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
        optReport.set('target', '') # We don't want any output from the opt task. Will set later for scan task

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

        for repeat in repeats:
            #Write a new file with 1, 10 and 100 repeats

            #Set the number of repeats for the scan task
            p1.attrib['value'] = str(repeat)
            report.attrib['target'] = str(repeat) + '_out.txt'

            filename = os.path.join(self.path, 'load_balancing_' + str(repeat) + '.cps')
            self.write(filename)


        return ['load_balancing_%d.cps' % repeat for repeat in repeats]
