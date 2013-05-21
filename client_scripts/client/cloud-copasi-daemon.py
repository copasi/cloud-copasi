#!/usr/bin/env python
 
#Script adapted from example by Sander Marechal, released into public domain
#Taken from http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/

#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------


import sys, time
from daemon import Daemon
import client_script

class MyDaemon(Daemon):
    def run(self):
        while True:
            try:
                min_repeat_time = 120 #Seconds
                start_time = time.time()
                
                client_script.run()
                
                finish_time = time.time()
                
                difference = finish_time - start_time
                if difference < min_repeat_time:
                    time.sleep(min_repeat_time - difference)
            except Exception, e:
                print 'Exception:'
                print e
                time.sleep(120)
 
if __name__ == "__main__":
    daemon = MyDaemon('/tmp/Condor-COPASI.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)