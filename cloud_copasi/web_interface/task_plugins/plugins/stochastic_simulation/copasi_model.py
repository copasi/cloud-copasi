#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from basico import *
from cloud_copasi.copasi import model
from cloud_copasi.copasi.model import *
from cloud_copasi import settings
import os, time, math

class SSCopasiModel_BasiCO(CopasiModel_BasiCO):
    """ Implementation using BasiCO library"""

    def prepare_ss_load_balancing(self, repeats=None):
        """Prepare copasi model files that can be used for the benchmarking step

        First sets up the scan task with a repeat. Write 4 files with 1, 10, 100 and 1000 repeats respectively
        """
        check.debug("+++++++++++ Entered into prepare_ps_load_balancing method.")

        if not repeats:
            repeats = [1, 10, 100, 1000]

        #Create a new report for the ss task
        report_key = 'condor_copasi_stochastic_simulation_report'
        self._create_report('SS', report_key, 'auto_ss_report')

        #clear task. check if really needed.

        #replacing getTask method as follows
        #using basico we can directly set the scan task settings as
        try:
            set_scan_settings(update_model = True, scheduled = True)
        except:
            raise

        #Here the report is assigned to scan and timeCourse tasks
        assign_report('auto_ss_report', task=T.SCAN, append=True)
        assign_report('auto_ss_report', task=T.TIME_COURSE, append=True)

        #no need to set different attributes separately as done by Ed in LXML

        for repeat in repeats:
            filename = os.path.join(self.path, 'load_balancing_%d.cps' %repeat) #for production
            # filename = os.path.join(os.getcwd(), 'load_balancing_%d.cps' %repeat) #for pythonHelp
            target = str(repeat) + '_out.txt'
            assign_report('auto_ss_report', task=T.SCAN, filename=target, append=True)
            self.scan_items[0]['num_steps'] = repeat
            set_scan_items(self.scan_items)
            self.write(filename)

        return ['load_balancing_%d.cps' % repeat for repeat in repeats]
