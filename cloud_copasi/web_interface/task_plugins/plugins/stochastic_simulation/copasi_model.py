from cloud_copasi.copasi.model import CopasiModel
from cloud_copasi.copasi import model
from cloud_copasi import settings
from lxml import etree
import os, time, math

xmlns = model.xmlns

class SSCopasiModel(CopasiModel):
    
    def prepare_ss_load_balancing(self, repeats):
        """Prepare a copasi model file that can be used for the benchmarking step
        """           
        ############
        #Benchmarking
        ############
        #Measure the time taken to run a single run of the timecourse task
        
        #Clear tasks, and get the time course task
        
        self._clear_tasks()
        timeTask = self._getTask('timeCourse')
        timeTask.attrib['scheduled'] = 'true'
        
        
        #Write a temp XML file
        filename = 'load_balancing.cps'
        
        
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
        timeReport.set('target', 'load_balancing_output.txt')
        
        self.model.write(os.path.join(self.path, filename))
        
        return filename