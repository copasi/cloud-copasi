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
import django
django.setup()

from tools.daemon import Daemon
import tools.background_script
from tools.response import RemoteLoggingResponse
from cloud_copasi import settings
import logging

log = logging.getLogger("daemon")

class MyDaemon(Daemon):

    #Set the level we wish to log at. Logs are sent back to the central server
    #Choices are all, debug, info, error, none


    def __init__(self, *args, **kwargs):

        return super(MyDaemon, self).__init__(*args, **kwargs)

    def stop(self, *args, **kwargs):

        return super(MyDaemon, self).stop(*args, **kwargs)

    def run(self):
        log.debug('Daemon running')

        while True:
            min_repeat_time = settings.DAEMON_POLL_TYME #Seconds
            start_time = time.time()

            try:
                tools.background_script.run()

            except Exception as e:
                log.exception(e)


            finish_time = time.time()
            difference = finish_time - start_time

            if difference < min_repeat_time:
                time.sleep(min_repeat_time - difference)


if __name__ == "__main__":
    daemon = MyDaemon('/tmp/Cloud-COPASI.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print ("Unknown command")
            sys.exit(2)
        sys.exit(0)
    else:
        print("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)
