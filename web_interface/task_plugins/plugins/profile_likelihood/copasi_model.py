#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2022 Hasan Baig.
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

class PLCopasiModel_BasiCO(CopasiModel_BasiCO):
    """ model for profile likelihood task """
