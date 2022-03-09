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


class ORCopasiModel_BasiCO(CopasiModel_BasiCO):
    """ Implementation using BasiCO library"""

    def prepare_or_load_balancing(self, repeats=None):
        
        if not repeats:
            repeats = [1, 10, 100, 1000]

        #resetting all tasks
        self._clear_tasks()
        #check if this is really needed
        optTask = get_opt_settings()

        #Creating a report
        report_key = None
        self._create_report('OR', report_key, 'auto_or_report')

        #setting scan task settings
        # print("Initial Scan Settings")
        # print(get_scan_settings())

        # set_scan_items([{
        #                 'type': 'scan',
        #                 'num_steps': 0 #initially setting to 0
        #                 }])
        self.scan_items.remove(self.scan_items[1])
        self.scan_items[0]['num_steps'] = 0
        self.scan_items[0]['type'] = 'repeat'

        print("check:")
        print(self.scan_items)
        self.scan_items[0].pop('cn')
        self.scan_items[0].pop('log')
        self.scan_items[0].pop('min')
        self.scan_items[0].pop('max')
        self.scan_items[0].pop('values')
        self.scan_items[0].pop('use_values')
        self.scan_items[0].pop('item')

        print("Self.scan_items: ")
        print(self.scan_items)

        set_scan_settings(
                          scheduled = True,
                          update_model = True,
                          subtask = 'Optimization',
                          output_during_subtask = True,
                          scan_items = self.scan_items,
                        )

        # print("New Scan Settings")
        # print(get_scan_settings())

        #assigning report to scan task
        assign_report('auto_or_report', task=T.SCAN, append=True, confirm_overwrite = False)
        assign_report('auto_or_report', task=T.OPTIMIZATION, append=True, confirm_overwrite = False)

        for repeat in repeats:
            filename = os.path.join(self.path, 'load_balancing_%d.cps' %repeat) #for production
            # filename = os.path.join(os.getcwd(), 'load_balancing_%d.cps' %repeat) #for pythonHelp
            target = str(repeat) + '_out.txt'
            assign_report('auto_or_report', task=T.SCAN, filename=target, append=True)
            self.scan_items[0]['num_steps'] = repeat
            set_scan_items(self.scan_items)
            self.write(filename)

        return ['load_balancing_%d.cps' % repeat for repeat in repeats]
