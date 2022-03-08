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
            filename = os.path.join(self.path, 'load_balancing_%d.cps' %repeat) #for production
            # filename = os.path.join(os.getcwd(), 'load_balancing_%d.cps' %repeat) #for pythonHelp
            target = str(repeat) + '_out.txt'
            assign_report('auto_pr_report', task=T.SCAN, filename=target, append=True, confirm_overwrite = False)
            self.scan_items[0]['num_steps'] = repeat
            set_scan_items(self.scan_items)
            self.write(filename)

        return ['load_balancing_%d.cps' % repeat for repeat in repeats]
