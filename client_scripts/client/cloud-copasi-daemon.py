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
from response import RemoteLoggingResponse

class MyDaemon(Daemon):
    def run(self):
        logging_level = 'all'
        log = Log(logging_level)
        log.info('Daemon starting')

        while True:
            try:
                min_repeat_time = 120 #Seconds
                start_time = time.time()
                
                client_script.run()
                
                finish_time = time.time()
                
                logging.debug('Client script finished')
                
                difference = finish_time - start_time
                if difference < min_repeat_time:
                    time.sleep(min_repeat_time - difference)
            except Exception, e:
                logging.error('%s' % str(e))
                
                time.sleep(120)
            
            #Try to send a response with the log so far
            try:
                message_list = log.get_message_list()
                
                response = RemoteLoggingResponse()
            except:
                pass
            
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