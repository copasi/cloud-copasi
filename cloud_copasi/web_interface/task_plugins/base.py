#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

#===============================================================================
# Base task plugin structure
#===============================================================================

class BaseTask:
    
    internal_name = ('base', 'Base task')
    
    #The number of subtasks this task is split into
    subtasks=0
    
    def __init__(self, task):
        self.task = task
    
    def validate(self):
        return True
    
    def prepare_subtask(self, subtask=0):
        """Prepare a particular subtask to run
        """
        
        #Ensure the correct files are on the system
        return []