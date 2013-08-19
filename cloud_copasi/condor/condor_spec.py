#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html

#Adapted from Condor-COPSAI
#code.google.com/p/condor-copasi


#This file contains the outline used for creating the condor job specification files
#Changes to requirements, etc, can be made here

condor_string_header = """#Condor job
universe       = grid
grid_resource = batch ${pool_type} ${pool_address}
"""

#For normal jobs. All arguments to the COPASI binary are hardcoded here
#CopasiSE binary now X86_64 only...
condor_string_args = """executable = ${binary_dir}CopasiSE
transfer_executable = ${transfer_executable}
arguments = --nologo --home . ${copasiFile} --save run_${copasiFile}
"""

#For raw mode. Allows for custom arguments to be added
condor_string_no_args = """executable = ${binary_dir}CopasiSE
transfer_executable = ${transfer_executable}
arguments = $args
"""

condor_string_body = """transfer_input_files = ${copasiFile}${otherFiles}
log =  ${copasiFile}.log  
error = ${copasiFile}.err
output = ${copasiFile}.out
rank = ${rank}
Requirements = ( Arch == "X86_64" && OpSys == "LINUX") 
should_transfer_files = YES
when_to_transfer_output = ON_EXIT
transfer_output_files = run_${copasiFile}, ${outputFile}
${extraArgs}
queue ${n}\n"""

raw_condor_job_string = condor_string_header + condor_string_args + condor_string_body

raw_mode_string = condor_string_header + condor_string_no_args + condor_string_body

#This spec is used for the stochastic simulation results processing task
#Since processing for this task is quite computationally expensive, we run it
#on Condor. A few slight differences to the usual spec, such as executable,
#requirement for python to be present...

stochastic_processing_spec_string = """#Condor job
executable = ${script}
universe       = vanilla 
arguments = 
transfer_input_files = ${raw_results}
log =  results.log
error = results.err
output = results.out
rank = ${rank}
Requirements = ( OpSys == "LINUX" || OpSys=="OSX") && ( Arch=="X86_64" || Arch=="INTEL" ) && (HAS_PYTHON26 == True) && (machine != "localhost.localdomain")
should_transfer_files = YES
when_to_transfer_output = ON_EXIT
queue\n"""


load_balancing_spec_string = """
executable = ${script}
arguments = 
transfer_input_files = ${copasi_files}, ${copasi_binary}
log =  load_balancing.log
error = load_balancing.err
output = load_balancing.out
rank = ${rank}
Requirements = ( OpSys == "LINUX") && ( Arch=="X86_64")
should_transfer_files = YES
when_to_transfer_output = ON_EXIT
queue\n"""


results_process_spec_string = """
executable = ${script}
arguments = ${args}
transfer_input_files = ${input_files}
log =  ${output}.log
error = ${output}.err
output = ${output}.out
rank = ${rank}
Requirements = ( OpSys == "LINUX") && ( Arch=="X86_64")
should_transfer_files = YES
when_to_transfer_output = ON_EXIT
transfer_output_files = ${output_files}
queue\n"""
