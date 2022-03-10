#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

import re, datetime
import logging

log = logging.getLogger(__name__)

class Log:
    """Class for reading and processing condor log files using regex patterns"""

    def __init__(self, path):
        """Initialise the class, reading from the condor file located at absolute path 'path'"""

        #First, define some regexes

        #Job execution string will be of the format:
        #001 (20949.000.000) 02/07 11:27:10 Job executing on host: <130.88.110.118:60608>
        execution_string = r'\d+\s\S+\s(?P<month>\d\d)\/(?P<day>\d\d)\s(?P<hour>\d+)\:(?P<minute>\d+)\:(?P<second>\d+)\sJob executing on host\:\s\<(?P<host>.+)\>.*'
        execution_re = re.compile(execution_string)
        execution_match = False

        #Job termination string:
        #005 (20949.000.000) 02/07 11:28:10 Job terminated.
        termination_string = r'\d+\s\S+\s(?P<month>\d\d)\/(?P<day>\d\d)\s(?P<hour>\d+)\:(?P<minute>\d+)\:(?P<second>\d+)\sJob terminated\..*'
        termination_re = re.compile(termination_string)
        termination_match = False
        #Termination status:
        #       (1) Normal termination (return value 0) #TODO:this only works for normal termination, so status will always be 0
        termination_status_string = r'\s+\(\d+\)\s(Normal|Abnormal) termination\s\((return value|signal) (?P<return_value>\d+)\).*'
        termination_status_re = re.compile(termination_status_string)
        termination_status_match = False
        #Remote usage time
        #               Usr 0 00:00:54, Sys 0 00:00:00  -  Total Remote Usage
        remote_usage_string = r'\s+Usr\s(?P<usr_days>\d+)\s(?P<usr_hours>\d+)\:(?P<usr_minutes>\d+)\:(?P<usr_seconds>\d+)\,\sSys\s(?P<sys_days>\d+)\s(?P<sys_hours>\d+)\:(?P<sys_minutes>\d+)\:(?P<sys_seconds>\d+)\s+\-\s+Total Remote Usage.*'
        remote_usage_re = re.compile(remote_usage_string)
        remote_usage_match = False
        #We'll use this string to search for the phrase 'Job terminated'. We'll then use this to decide whether or not the job has finished running yet. If not, then don't try and match anything else yet - there's no point
        termination_confirmation_string = r'.*Job terminated.'
        termination_confirmation_re = re.compile(termination_confirmation_string)

        self.has_terminated = False
        #Search to see if the job has actually terminated. Only continue if it has...
        for line in open(path, 'r'):
            if termination_confirmation_re.match(line):
                self.has_terminated = True
                break

        if not self.has_terminated:
            return

        try:
            for line in open(path, 'r'):
                if execution_re.match(line):
                    execution_match = execution_re.match(line)

                elif termination_re.match(line):
                    termination_match = termination_re.match(line)

                elif termination_status_re.match(line):
                    termination_status_match = termination_status_re.match(line)

                elif remote_usage_re.match(line):
                    remote_usage_match = remote_usage_re.match(line)


            if remote_usage_match:
                g = remote_usage_match.group
                usr_days = int(g('usr_days'))
                usr_hours = int(g('usr_hours'))
                usr_minutes = int(g('usr_minutes'))
                usr_seconds = int(g('usr_seconds'))

                sys_days = int(g('sys_days'))
                sys_hours = int(g('sys_hours'))
                sys_minutes = int(g('sys_minutes'))
                sys_seconds = int(g('sys_seconds'))

                usr_time = datetime.timedelta(days=usr_days, hours=usr_hours, minutes=usr_minutes, seconds=usr_seconds)
                sys_time = datetime.timedelta(days=sys_days, hours=sys_hours, minutes=sys_minutes, seconds=sys_seconds)


                self.remote_usage_time = usr_time + sys_time

            if execution_match:
                g = execution_match.group
                day = int(g('day'))
                month = int(g('month'))
                hour = int(g('hour'))
                minute = int(g('minute'))
                second = int(g('second'))
                host = g('host')
#                port = g('port')

                #Create datetime object for execution start time
                #Since log file doesn't store the date, we'll have to guess it
                #If remote_usage time is stored, take the current date, and subtract the usage time
                try:
                    assert self.remote_usage_time != None
                    year = (datetime.datetime.today() - self.remote_usage_time).year
                except AssertionError:
                    year = datetime.datetime.today().year

                self.execution_start = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
                self.host = host

            if termination_status_match:
                self.termination_status = int(termination_status_match.group('return_value'))


            if termination_match:
                g = termination_match.group
                day = int(g('day'))
                month = int(g('month'))
                hour = int(g('hour'))
                minute = int(g('minute'))
                second = int(g('second'))

                log.debug("**** termination_match: day=%d, month=%d, hour=%d, minute=%d, second=%d" %(day, month, hour, minute, second))

                #Again, guess the year
                year=datetime.datetime.today().year
                log.debug("**** guessing the year: ")
                log.debug(year)

                log.debug("**** guessing the termination_time: ")
                self.termination_time = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
                log.debug(self.termination_time)


            #For some reason, the remote usage time sometimes appears as zero. In this case, set running time as follows:
            if self.remote_usage_time == datetime.timedelta() and hasattr(self, 'execution_start'):
                self.running_time = self.termination_time - self.execution_start
            else:
                self.running_time = self.remote_usage_time
            self.running_time_in_days = float(self.running_time.days) + (float(self.running_time.seconds) / 86400.00)



        except:
            raise
