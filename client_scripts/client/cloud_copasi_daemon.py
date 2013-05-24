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
from simple_logging import Log

def readline(path):
    return open(path, 'r').read().splitlines()[0]
log_level = readline('/etc/cloud-config/log_level').lower()
poll_time = int(readline('/etc/cloud-config/poll_time')) #seconds

class MyDaemon(Daemon):
    
    #Set the level we wish to log at. Logs are sent back to the central server
    #Choices are all, debug, info, error, none
    
    

    def __init__(self, *args, **kwargs):
        self.log = Log(log_level)

        return super(MyDaemon, self).__init__(*args, **kwargs)
    
    def stop(self, *args, **kwargs):
        self.log.info('Received request to stop. Daemon stopping')
        self.send_log()
        
        return super(MyDaemon, self).stop(*args, **kwargs)
    
    def run(self):
        self.log.info('Daemon running')

        while True:
            min_repeat_time = poll_time #Seconds
            start_time = time.time()

            try:
                
                client_script.run(self.log)

                self.log.debug('Client script finished')
            
            except Exception, e:
                self.log.error('%s' % str(e))
                
            self.send_log()
            
            finish_time = time.time()
            difference = finish_time - start_time
            
            if difference < min_repeat_time:
                time.sleep(min_repeat_time - difference)

    def send_log(self):
        #Try to send a response with the log from this run
        try:
            message_list = self.log.get_message_list()
            
            response_object = RemoteLoggingResponse(message_list)
            response_object.send_response()
            
            self.log.clear()
            
        except Exception, e:
            self.log.clear() # Couldn't send? Clear the log so it doesn't overflow
            self.log.error(str(e))


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