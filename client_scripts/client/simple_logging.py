#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from datetime import datetime

class Log:
    #Simple class for logging events.
    #Message list should be flushed periodically and messages sent back to central server

    #Logging levels:
    
    write_to_file = True
    log_filename = '/home/ubuntu/cloud-copasi.log'

    logging_levels = {
                      'all': 0,
                      'debug': 1,
                      'info': 2,
                      'warning': 3,
                      'error': 4,
                      'critical': 5,
                      'none': 99,
                      }
    
    def __get_level__(self, name):
        return self.logging_levels.get(name, 0)
    
    def __init__(self, level):
        #Level name i.e. 'debug'. Messages below this level will not be stored
        self.message_list = []
        self.level = level
        
    def __add_message__(self, message_type, message):
        #Add the message and message type to the message list, with a timestamp
        message_level = self.__get_level__(message_type)
        current_level = self.__get_level__(self.level)
        
        if message_level >= current_level:
            m = (message_type, str(datetime.now()), message)
            self.message_list.append(m)
            if self.write_to_file:
                log_file = open(self.log_filename, 'a')
                log_file.write(str(m) + '\n')
                log_file.close()
    def debug(self, message):
        self.__add_message__('debug', message)
        
    def info(self, message):
        self.__add_message__('info', message)
        
    def warning(self, message):
        self.__add_message__('warning', message)
        
    def error(self, message):
        self.__add_message__('error', message)
        
    def critical(self, message):
        self.__add_message__('critical', message)
    
    def get_message_list(self):
        return self.message_list
    
    def clear(self):
        #Clear the message list
        self.message_list = []