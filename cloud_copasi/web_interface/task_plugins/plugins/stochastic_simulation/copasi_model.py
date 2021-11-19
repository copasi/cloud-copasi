#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from basico import *
from cloud_copasi.copasi.model import CopasiModel
from cloud_copasi.copasi import model
from cloud_copasi import settings
from lxml import etree
import os, time, math

xmlns = model.xmlns

class SSCopasiModel(CopasiModel):

    def prepare_ss_load_balancing(self, repeats=None):
        """Prepare copasi model files that can be used for the benchmarking step

        First sets up the scan task with a repeat. Write 3 files with 1, 10 and 100 repeats respectively
        """

        if not repeats:
            repeats = [1, 10, 100, 1000]

        ############
        #Create a new report for the ss task
        report_key = 'condor_copasi_stochastic_simulation_report'
        self._create_report('SS', report_key, 'auto_ss_report')





        #clear the task list, to ensure that no tasks are set to run
        self._clear_tasks()

        scanTask = self._getTask('scan')

        #And set it scheduled to run, and to update the model
        scanTask.attrib['scheduled'] = 'true'
        scanTask.attrib['updateModel'] = 'true'

        #Set up the appropriate report for the scan task, and clear the report for the time course task
        #The report doesn't really matter, since it won't be transferred back.
        #Do this step any way though or COPASI will complain
        timeTask = self._getTask('timeCourse')
        timeReport = timeTask.find(xmlns + 'Report')

        #If no report has yet been set, report == None. Therefore, create new report
        if timeReport == None:
            timeReport = etree.Element(xmlns + 'Report')
            timeTask.insert(0,timeReport)

        timeReport.set('reference', report_key)
        timeReport.set('append', '1')


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


        for repeat in repeats:
            #Write a new file with 1, 10 and 100 repeats

            p1.attrib['value'] = str(repeat)

            report.set('target', str(repeat) + '_out.txt') #target doesn't really matter, since it won't be transferred back
            filename = os.path.join(self.path, 'load_balancing_' + str(repeat) + '.cps')
            self.write(filename)


        return ['load_balancing_%d.cps' % repeat for repeat in repeats]
