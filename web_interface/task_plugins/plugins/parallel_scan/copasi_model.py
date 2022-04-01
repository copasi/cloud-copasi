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

class PSCopasiModel_BasiCO(CopasiModel_BasiCO):
    """ Implementation of this method using BasiCO library"""

    #def __init__(self, filename):
    #    self.model = load_model(filename)
    #    self.scan_settings = get_scan_settings()
    #    self.scan_items = get_scan_items()

    def prepare_ps_load_balancing(self, repeats=None):

        if not repeats:
            repeats = [1, 10, 100, 1000]

        firstScan = self.scan_items[0]
        no_of_steps = int(firstScan['num_steps'])
        task_type = firstScan['type']
        max = firstScan['max']
        min = firstScan['min']
        log = firstScan['log']
        values = firstScan['values']
        use_values = firstScan['use_values']
        item = firstScan['item']

        assert no_of_steps > 0

        if task_type == 'scan':
            max_value = float(max)
            min_value = float(min)

            no_of_steps += 1 #Parameter scans actually consider no of intervals, which is one less than the number of steps, or actual parameter values. We will work with the number of discrete parameter values, and will decrement this value when saving new files

        output_file = 'output'
        assign_report('Scan Parameters, Time, Concentrations, Volumes, and Global Quantity Values',
                  task=T.SCAN,
                  filename= output_file,
                  append= True
                 )

        import tempfile
        #writing copasi models for load balancing
        for repeat in repeats:
            print("repeat: %d"%repeat)
            filename = os.path.join(self.path, 'load_balancing_%d.cps' %repeat)
            self.scan_items[0]['num_steps'] = repeat
            set_scan_items(self.scan_items)
            self.write(filename)

        return ['load_balancing_%d.cps' % repeat for repeat in repeats]

    def get_number_of_intervals(self):
        """Get the number of intervals set for the top level scan task
        """
        return int(self.scan_items[0]['num_steps'])
