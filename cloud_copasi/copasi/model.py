#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html

#Adapted from Condor-COPSAI
#code.google.com/p/condor-copasi

from basico import *
import subprocess, os, re, math, time
from cloud_copasi import settings
from cloud_copasi.condor import condor_spec
from string import Template
import logging

log = logging.getLogger(__name__)
slog = logging.getLogger("special")

condor_string_body = """transfer_input_files = ${copasiFile}${otherFiles}
log =  ${copasiFile}.log
error = ${copasiFile}.err
output = ${copasiFile}.out
Requirements = ( (OpSys == "WINNT61" && Arch == "INTEL" ) || (OpSys == "WINNT61" && Arch == "X86_64" ) || (Opsys == "LINUX" && Arch == "X86_64" ) || (OpSys == "OSX" && Arch == "PPC" ) || (OpSys == "OSX" && Arch == "INTEL" ) || (OpSys == "LINUX" && Arch == "INTEL" ) ) && (Memory > 0 ) && (Machine != "e-cskc38c04.eps.manchester.ac.uk") && (machine != "localhost.localdomain")
#Requirements = (OpSys == "LINUX" && Arch == "X86_64" )
should_transfer_files = YES
when_to_transfer_output = ON_EXIT
queue\n"""


def get_time_per_job(job):
    #For benchmarking purposes, jobs with a name ending with ?t=0.5 will use the custom t for load balancing
    name_re = re.compile(r'.*t=(?P<t>.*)')
    name_match = name_re.match(job.name)
    if name_match:
        return float(name_match.group('t'))
    else:
        return settings.IDEAL_JOB_TIME


class CopasiModel_BasiCO(object):
    """Class representing a Copasi model using BasiCO library"""
    def __init__(self, filename, binary=settings.COPASI_LOCAL_BINARY, binary_dir=None, job=None):
        log.debug('in __init__ method of CopasiModel_BasiCO class')
        if binary_dir == None:
            binary_dir, binary_path = os.path.split(settings.COPASI_LOCAL_BINARY)

        #loading the copasi model file using BasiCO
        log.debug('Model File: %s' %filename)
        self.model = load_model(filename)
        self.scan_settings = get_scan_settings()
        self.scan_items = get_scan_items()
        self.listOfReports = get_reports()
        self.metabolites = get_species()
        log.debug('List of species: ')
        log.debug(self.metabolites)
        self.timeTask = get_task_settings(T.TIME_COURSE)

        self.binary = binary
        self.binary_dir = binary_dir
        self.name = filename
        (head, tail) = os.path.split(filename)
        self.path = head
        self.job=job

    def __unicode__(self):
        return self.name
    def __string__(self):
        return self.name

    def write(self, filename):
        """ writing a new model to the specified filename """
        return save_model(filename)

    def is_valid(self, job_type):
        """Check if the model has been correctly set up for a particular condor-copasi task"""
        #temporarily setting this to test parallel scan task
        if job_type == 'SO':
            #Check that a single object has been set for the sensitivities task:
            if self.get_sensitivities_object() == '':
                return 'A single object has not been set for the sensitivities task'
            #And check that at least one parameter has been set
            if len(self.get_optimization_parameters()) == 0:
                return 'No parameters have been set for the optimization task'
            return True

        elif job_type == 'PS':
            firstScan = self.scan_items[0]
            item = firstScan['item']
            type = firstScan['type']
            no_of_steps = firstScan['num_steps']

            if not item:
                return 'At least one scan must have been set'

            if not (type == 'scan' or type == 'repeat'):
                return 'The first item in the scan task must be either a Parameter Scan or a repeat'

            if type == 'scan' and no_of_steps < 1:
                return 'The first-level Parameter Scan must have at least one interval. If only one repeat is required, consider replacing the Parameter Scan with a Repeat'

            if not get_report_dict('Scan Parameters, Time, Concentrations, Volumes, and Global Quantity Values'):
                return 'A report must be set for the scan task'

            return True

        elif job_type == 'SS':
            method_name = self.timeTask['method']['name']
            if method_name == 'Deterministic (LSODA)':
                return 'Time course task must have a valid Stochastic or Hybrid algorithm set'
            else:
                return True

        elif job_type == 'OR' or job_type == 'OD':
            if len(self.get_optimization_parameters()) == 0:
                return 'No parameters have been set for the optimization task'
            if self._get_optimization_object() == '':
                return 'No objective expression has been set for the optimization task'
            return True

        elif job_type == 'PR' or job_type == 'PL':
            if len(self.get_parameter_estimation_parameters()) == 0:
                return 'No parameters have been set for the sensitivites task'
            return True

        else:
            return True

    def _copasiExecute(self, filename, tempdir, timeout=-1, save=False):
        """Private function to run Copasi locally in a temporary folder."""
        import process
        if not save:
            returncode, stdout, stderr = process.run([self.binary, '--nologo',  '--home', tempdir, filename], cwd=tempdir, timeout=timeout)
        else:
            returncode, stdout, stderr = process.run([self.binary, '--nologo',  '--home', tempdir, '--save', filename, filename], cwd=tempdir, timeout=timeout)
        return returncode, stdout, stderr

    def _getVersionMajor(self):
        """ to copy from original function """

    def _getVersionMinor(self):
        """ to copy from original function """

    def _getVersionDevel(self):
        """ to copy from original function """

    def _getTask(self,task_type, model=None):
        """ There should be a function to retrieve listOfTasks """

    def _clear_tasks(self):
        """Go through the task list, and set all tasks as not scheduled to run"""
        all_tasks = T.all_task_names()

        for task in all_tasks:
            task_settings = get_task_settings(task)
            task_settings['scheduled'] = False
            set_task_settings(task, task_settings)

    def _get_compartment_name(self, key):
        """Go through the list of compartments and return the name of the compartment with a given key"""

    def get_name(self):
        """ Retrieve the model name """
        model_name = overview(self.model).split("\n",1)[0][16:]
        return model_name

    def extract_value(self,loop):
        """ Extracting values in the specific column out of specified data frame """
        items = []
        for value in loop:
            items.append(value)

        return items

    def get_sensitivities_object(self, friendly=True):
        """Returns the single object set for the sensitvities task"""
        sensTask = get_sensitivity_settings()
        value_string = sensTask['effect']

        return value_string

    def _get_optimization_object(self):
        """Returns the objective expression for the optimization task"""
        return get_opt_settings()['expression']

    def get_optimization_parameters(self, friendly=True):
        """Returns a list of the parameter names to be included in the sensitvitiy optimization task. Will optionally process names to make them more user friendly"""

        opt_parameters = get_opt_parameters()

        #extracting parameter names
        names = self.extract_value(opt_parameters.index)

        #arranging parameters in the form of dictionary
        dict = opt_parameters.to_dict()

        #arranging parameter values in separate dictionaries
        lower = dict['lower']
        upper = dict['upper']
        start = dict['start']

        #packing values in list as tuples of name, lower, upper, start
        parameters = []
        for name in names:
            parameters.append((name, lower[name], upper[name], start[name]))

        return parameters

    def get_parameter_estimation_parameters(self, friendly=True):
        """Returns a list of the parameter names to be included in the parameter estimation task. Will optionally process names to make them more user friendly"""
        fit_parameters = get_fit_parameters()
        names = self.extract_value(fit_parameters.index)

        dict = fit_parameters.to_dict()

        #arranging parameter values in separate dictionaries
        lower = dict['lower']
        upper = dict['upper']
        start = dict['start']

        parameters = []
        for name in names:
            parameters.append((name, lower[name], upper[name], start[name]))

        return parameters

    def get_ps_number(self):
        """Returns the number of runs set up for the parameter scan task"""

    def _create_report(self, report_type, report_key, report_name):
        """Create a report for a particular task, e.g. sensitivity optimization, with key report_key
        report_type: a string representing the job type, e.g. SO for sensitivity optimization"""

        report_names_list = self.listOfReports.index

        #removing the report if it already exists with the name report_name
        for report in report_names_list:
            if report == report_name:
                remove_report(report)
        updated_listOfReports = get_reports()

        if(report_type == 'SS'):
            model_name = self.get_name()
            objects = []
            time_object = 'Time'
            # objects.append(time_object)
            objects = self.get_variables()
            log.debug("Objects list before inserting time_object:")
            log.debug(objects)
            objects.insert(0, time_object)
            log.debug("Objects list AFTER inserting time_object:")
            log.debug(objects)

            #to avoid having error of "report already exist", create report only if it does not exist
            if get_report_dict(report_name) == None:
                log.debug("Report does not already exist. So creating it now.")
                add_report(key=report_key,
                           name=report_name,
                           task=T.TIME_COURSE,
                           table= objects,
                           comment= 'A table of time, variable species particle numbers, variable compartment volumes, and variable global quantity values.'
                           )

        elif(report_type == 'OR'):
            # table_content =
            if get_report_dict(report_name) == None:
                log.debug('Report does not exist. Creating one.')
                add_report(
                            name=report_name,
                            task=T.OPTIMIZATION,
                            table=['CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Best Parameters',
                                   'CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Best Value',
                                   'CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Timer=CPU Time',
                                   'CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Function Evaluations'
                                   ]
                          )
        elif report_type == 'PR':
            if get_report_dict(report_name) == None:
                log.debug('Report does not exist. Creating one.')
                add_report(
                            name=report_name,
                            task=T.PARAMETER_ESTIMATION,
                            table=['CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Reference=Best Parameters',
                                   'CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Reference=Best Value',
                                   'CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Timer=CPU Time',
                                   'CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Reference=Function Evaluations'
                                   ],
                            comment='Condor Copasi automatically generated report.'
                          )
        elif(report_type == 'SO'):
            if get_report_dict(report_name) == None:
                print('Report does not exist. Creating one.')
                body = ['String=#----\n',
                        'String=Evals \= ',
                        'CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Function Evaluations',
                        'String=\nTime \= ',
                        'CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Timer=CPU Time',
                        'String=\n',
                        'CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Best Value'
                        ]
                footer = ['String=#----\n',
                          'String=Evals \= ',
                          'CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Function Evaluations',
                          'String=\nTime \= ',
                          'CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Timer=CPU Time',
                          'String=\n',
                          'CN=Root,Vector=TaskList[Optimization],Problem=Optimization,Reference=Best Value'
                         ]
                add_report(
                            name=report_name,
                            task=T.OPTIMIZATION,
                            comment='Report generated by Cloud-COPASI',
                            body=body,
                            footer=footer
                          )
        else:
            raise Exception('Unknown report type')

    def prepare_so_task(self, subtask_index=1):
        """Generate the files required to perform the sensitivity optimization,

        This involves creating the appropriate temporary .cps files. The .job files are generated seperately"""

        self._clear_tasks()

        optTask = get_opt_settings()
        #setting it scheduled to run and to update the model
        set_opt_settings({'scheduled': True,
                      'update_model': True
                      })

        #Set the appropriate objective function for the optimization task:
        set_objective_function(expression='<CN=Root,Vector=TaskList[Sensitivities],Problem=Sensitivities,Array=Scaled sensitivities array[.]>')

        #Create a new report for the optimization task
        report_key = None
        self._create_report('SO', report_key, 'auto_so_report')

        if "report" not in optTask:
            set_task_settings(T.OPTIMIZATION,
                              {'report': {}
                              })

        set_opt_settings({'report': {'append': True,
                                     'filename': ''}
                      })

        #assigning the report to optimization task
        assign_report('auto_so_report', task=T.OPTIMIZATION, append=True, confirm_overwrite = False)

        #get the list of strings to optimize
        optimizationStrings = []
        for parameter in self.get_optimization_parameters(friendly=False):
            optimizationStrings.append(parameter[0])

        #Build the new xml files and save them
        i = 0
        file_list = []
        for optString in optimizationStrings:
            set_opt_settings({'problem':{'Maximize':True}})
            output = 'output_%d.%d.txt' % (subtask_index, i)
            set_opt_settings({'report':{'filename':output}})

            #Update the sensitivities object
            set_sensitivity_settings({'cause': optString})

            target = os.path.join(self.path, 'auto_copasi_%d.%d.cps' %(subtask_index, i))

            self.write(target)
            file_list.append(target)

            set_opt_settings({'problem':{'Maximize':False}})
            output = 'output_%d.%d.txt' % (subtask_index, i+1)
            set_opt_settings({'report':{'filename':output}})

            target = os.path.join(self.path, 'auto_copasi_%d.%d.cps' % (subtask_index, i+1))
            self.write(target)
            file_list.append(target)
            i = i + 2

        return file_list

    def prepare_so_condor_job(self, pool_type, pool_address, subtask_index=1, rank='0', extraArgs=''):
        """Prepare the neccessary .job file to submit to condor for the sensitivity optimization task"""
        #Build the appropriate .job files for the sensitivity optimization task, write them to disk, and make a note of their locations
        condor_jobs = []

        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = 'output_%d.$(Process).txt' % subtask_index

        n = len(self.get_optimization_parameters()) * 2

        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'

        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file,
                                                                                   otherFiles='',
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = n,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )

        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename


    def get_so_results(self, save=False):
        """Collate the output files from a successful sensitivity optimization run. Return a list of the results"""
        #Read through output files
        parameters=self.get_optimization_parameters(friendly=True)
        parameterRange = range(len(parameters))

        results = []

        for i in parameterRange:
            result = {
                'name': parameters[i][0],
                'max_result': '?',
                'max_evals' : '?',
                'max_cpu' : '?',
                'min_result' : '?',
                'min_evals' : '?',
                'min_cpu' : '?',
            }
            #Read min and max files
            for max in [0, 1]:
                iterator = 0

                try:
                    file = open(os.path.join(self.path, 'output_1.%d.txt' % (2*i + max)),'r')
                    output=[None for r in range(4)]
                    for f in file.readlines():
                        value = f.rstrip('\n') #Read the file line by line.
                        #Line 0: seperator. Line 1: Evals. Line 2: Time. Line 3: result
                        index=parameterRange.index(i)
                        output[iterator] = value
                        iterator = (iterator + 1)%4
                    file.close()
                    evals = output[1].split(' ')[2]
                    cpu_time = output[2].split(' ')[2]
                    sens_result = output[3]

                    if max == 0:
                        max_str = 'max'
                    else:
                        max_str = 'min'
                    result[max_str + '_result'] = sens_result
                    result[max_str + '_cpu'] = cpu_time
                    result[max_str + '_evals'] = evals

                except:
                    raise

            results.append(result)

        #Finally, if save==True, write these results to file results.txt
        if save:
            if not os.path.isfile(os.path.join(self.path, 'results.txt')):
                results_file = open(os.path.join(self.path, 'results.txt'), 'w')
                header_line = 'Parameter name\tMin result\tMax result\tMin CPU time\tMin Evals\tMax CPU time\tMax Evals\n'
                results_file.write(header_line)
                for result in results:
                    result_line = result['name'] + '\t' + result['min_result'] + '\t' + result['max_result'] + '\t' + result['min_cpu'] + '\t' + result['min_evals'] + '\t' + result['max_cpu'] + '\t' + result['max_evals'] + '\n'
                    results_file.write(result_line)
                results_file.close()
        return results

    def prepare_ss_task(self, runs, repeats_per_job, subtask_index=1):
        """Prepares the temp copasi files needed to run n stochastic simulation runs

        """
        #Create a new report for the ss task
        #report_key is not needed in basico because we cannot change the reference/key in basico. Use direct assignment of report to the relevant tasks
        log.debug("+++++++++++ BasiCO prepare_ss_task runnnig")
        report_key = 'condor_copasi_stochastic_simulation_report'
        self._create_report('SS', report_key, 'auto_ss_report')

        # #if report is not already present
        if "report" not in self.timeTask:
            set_task_settings(T.TIME_COURSE,
                              {'report': {}}
                             )
        #Setting TIME_COURSE task report settings
        set_task_settings(T.TIME_COURSE,
                          {'report': {'append': True,
                                      'filename': ''
                                     }
                          }
                         )

        no_of_jobs = int(math.ceil(float(runs) / repeats_per_job))
        #now getting SCAN task settings
        scanTask = get_task_settings(T.SCAN)

        #Setting scan task to run and update the model and have one subtask
        set_task_settings(T.SCAN,
                          {'scheduled': True,
                           'update_model': True,
                           'report':{'append': True},
                           'problem':{'Subtask': 1}
                          }
                         )
        #Initially setting scan item. num_steps attribute to 0
        set_scan_items([{'num_steps':0,
                         'type': 'repeat',
                        }])

        runs_left = runs # Decrease this value as we generate the jobs
        model_files = []

        for i in range(no_of_jobs):
            #Calculate the number of runs per job. This will either be repeats_per_job, or if this is the last job, runs_left
            no_of_steps = min(repeats_per_job, runs_left)
            set_scan_items([{'num_steps': no_of_steps,
                             'type': 'repeat',
                            }])

            runs_left -= no_of_steps

            target = 'output_%d.%d.txt' % (subtask_index, i)
            print("target: %s" %target)

            #assigning a report (already created before) to SCAN task
            assign_report('auto_ss_report', task=T.SCAN, filename=target, append=True)
            assign_report('auto_ss_report', task=T.TIME_COURSE, append=True)

            #Uncomment the following line only for debugging locally and comment out the line after.
            # filename = os.path.join(os.getcwd(), 'auto_copasi_%d.%d.cps' % (subtask_index, i))
            filename = os.path.join(self.path, 'auto_copasi_%d.%d.cps' % (subtask_index, i))
            self.write(filename)
            model_files.append(filename)
            runs_file = open(filename + '.runs.txt', 'w')
            runs_file.write('Repeats per job:\n')
            runs_file.write(str(no_of_steps))
            runs_file.close()

        return model_files

    def prepare_ss_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index=1, rank='0', extraArgs=''):
        """Prepare the neccessary .job file to submit to condor for the relevant task"""
        log.debug("+++++++++++ BasiCO prepare_ss_condor_job runnnig")
        #Build the appropriate .job files for the sensitivity optimization task, write them to disk, and make a note of their locations
        condor_jobs = []

        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = 'output_%d.$(Process).txt' % subtask_index

        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'


        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file,
                                                                                   otherFiles='',
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )

        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename

    def prepare_ss_process_job(self, pool_type, pool_address, jobs, script_path, rank='0'):
        """Collate the results from the stochastic simulation task"""
        ############
        #The rest of the processing is moved to condor, by the file ss_results_process.py
        ############

        #Prepare the condor job file

        input_file_string = ''
        args_string = ''
        for job in jobs:
            input_file_string += job.job_output + ', '
            args_string += job.job_output + ' '
        input_file_string = input_file_string.rstrip(', ')
        args_string = args_string.rstrip(' ')
        output = 'results.txt'

        job_template = Template(condor_spec.condor_string_header + condor_spec.results_process_spec_string)

        job_string = job_template.substitute(pool_type=pool_type,
                                             pool_address=pool_address,
                                             script=script_path,
                                             args=args_string,
                                             input_files=input_file_string,
                                             output='results',
                                             output_files = output,
                                             rank=rank)
        job_filename = 'results.job'
        job_file = open(os.path.join(self.path, job_filename), 'w')
        job_file.write(job_string)
        job_file.close()

        return job_filename

    def get_variables(self, pretty=False):
        """Returns a list of all variable metabolites, compartments and global quantities in the model.

        By default, returns the internal string representation, e.g. CN=Root,Model=Kummer calcium model,Vector=Compartments[compartment],Vector=Metabolites[a],Reference=ParticleNumber. Running pretty=True will parse the string and return a user-friendly version of the names.
        """
        # metabolites = get_species()
        # print(self.metabolites)
        output = []
        name = []
        simulationType = []
        compartmentKey = []     #this holds compartment name

        #Extracting metabolite names
        name = self.extract_value(self.metabolites.index)

        #Extracting metabolite simulation type
        simulationType = self.extract_value(self.metabolites.type)

        #Extracting compartment names
        compartmentKey = self.extract_value(self.metabolites.compartment)

        for i in range(len(name)):
            if simulationType[i] != 'fixed':
                if pretty:
                    output.append(name[i] + ' (Particle Number)')
                else:
                    compartment_name = compartmentKey[i]
                    model_name = self.get_name()
                    output_template = Template('CN=Root,Model=${model_name},Vector=Compartments[${compartment_name}],Vector=Metabolites[${name}],Reference=ParticleNumber')
                    output_string = output_template.substitute(model_name=model_name, compartment_name=compartment_name, name=name[i])
                    output.append(output_string)

        #Finally, get non-fixed global quantities
        values = get_parameters()
        #Hack - If no values have been set in the model, use the empty list to avoid a NoneType error
        if values.empty:
        # if values == None:
            values = []

        #extracting parameter names
        parameter_names = self.extract_value(values.index)
        #extracting parameter simulation type
        paramSimulationType = self.extract_value(values.type)

        for i in range(len(parameter_names)):
            name = parameter_names[i]
            simulationType = paramSimulationType[i]

            if simulationType != 'fixed':
                if pretty:
                    output.append(name + ' (Value)')
                else:
                    model_name = self.get_name()
                    output_template = Template('CN=Root,Model=${model_name},Vector=Values[${name}],Reference=Value')
                    output_string = output_template.substitute(model_name=model_name, name=name)
                    output.append(output_string)


        return output

    def prepare_ps_jobs(self, subtask_index, time_per_step=None):
        """Prepare the parallel scan task

        Efficiently splitting multiple nested scans is a hard problem, and currently beyond the scope of this project.
        As such, we simplify the problem by only splitting along the first scan task. It is the user's prerogative to ensure the scan task is set up in a way that enables the scan task to be efficiently split.
        Because of a limitation with the Copasi scan task -- that there must be at least two parameters for each scan, i.e. min and max, we set the requirement that the first scan must have at least one interval (corresponding to two parameter values), and that when splitting, each new scan must also have a minimum of at least one interval.
        """

        def get_range(min, max, intervals, log):
            """Get the range of parameters for a scan."""
            if not log:
                min = float(min)
                max = float(max)
                difference = max-min
                step_size = difference/intervals
                output = [min + i*step_size for i in range(intervals+1)]
                return output
            else:
                from math import log10 as log
                log_min = log(min)
                log_max = log(max)
                log_difference = log_max - log_min
                step_size = log_difference/intervals
                output = [pow(10, log_min + i*step_size) for i in range(intervals+1)]
                return output


        #scanning the parameters of first scan tasks
        firstScan = self.scan_items[0]
        no_of_steps = int(firstScan['num_steps'])
        task_type = firstScan['type']
        max_CP = firstScan['max']
        min_CP = firstScan['min']
        log = firstScan['log']
        values = firstScan['values']
        use_values = firstScan['use_values']
        item = firstScan['item']

        assert no_of_steps > 0
        if task_type == 'scan':
            max_value = float(max_CP)
            min_value = float(min_CP)

            no_of_steps += 1 #Parameter scans actually consider no of intervals, which is one less than the number of steps, or actual parameter values. We will work with the number of discrete parameter values, and will decrement this value when saving new files

            if time_per_step:
                time_per_step = time_per_step/2

        #We want to split the scan task up into subtasks of time ~= 10 mins (600 seconds)
        #time_per_job = no_of_steps * time_per_step => no_of_steps = time_per_job/time_per_step

        time_per_job = settings.IDEAL_JOB_TIME * 60

        if time_per_step:
            #Calculate the number of steps for each job. If this has been calculated as more than the total number of steps originally specified, use this value instead
            no_of_steps_per_job = min(int(round(float(time_per_job) / time_per_step)), no_of_steps)
        else:
            no_of_steps_per_job = 1

        #Because of a limitation of Copasi, each parameter must have at least one interval, or two steps per job - corresponding to the max and min parameters
        #Force this limitation:
        if task_type == 'scan':
            if no_of_steps_per_job < 2:
                no_of_steps_per_job = 2

        no_of_jobs = int(math.ceil(float(no_of_steps) / no_of_steps_per_job))

        model_files = [] #Store the relative file names of the model files created here

        #Set the model to update
        set_scan_settings(update_model = True)
        #First, deal with the easy case -- where the top-level item is a repeat.

        if task_type == 'repeat':
            step_count = 0
            for i in range(no_of_jobs):
                if no_of_steps_per_job + step_count > no_of_steps:
                    steps = no_of_steps - step_count
                else:
                    steps = no_of_steps_per_job
                step_count += steps

                if steps > 0:
                    self.scan_items[0]['num_steps'] = steps
                    set_scan_items(self.scan_items)

                    output_file = 'output_%d.%d.txt' % (subtask_index, i)
                    assign_report('Scan Parameters, Time, Concentrations, Volumes, and Global Quantity Values',
                              task=T.SCAN,
                              filename= output_file,
                              append= True
                             )

                    filename = 'auto_copasi_%d.%d.cps' % (subtask_index, i)
                    self.write(os.path.join(self.path, filename))
                    model_files.append(filename)


        #Then, deal with the case where we actually scan a parameter
        #Example: parameter range = [1,2,3,4,5,6,7,8,9,10] - min 1, max 10, 9 intervals => 10 steps
        #Split into 3 jobs of ideal length 3, min length 2
        #We want [1,2,3],[4,5,6],[7,8,9,10]
        elif task_type == 'scan':
            scan_range = get_range(min_value, max_value, no_of_steps-1, log)
            job_scans = []
            for i in range(no_of_jobs):
                #Go through the complete list of parameters, and split into jobs of size no_of_steps_per_job
                job_scans.append(scan_range[i*no_of_steps_per_job:(i+1)*no_of_steps_per_job]) #No need to worry about the final index being outside the list range - python doesn't mind

            #If the last job is only of length 1, merge it with the previous job
            assert no_of_jobs == len(job_scans)
            if len(job_scans[no_of_jobs-1]) ==1:
                job_scans[no_of_jobs-2] = job_scans[no_of_jobs-2] + job_scans[no_of_jobs-1]
                del job_scans[no_of_jobs-1]
                no_of_jobs -= 1

            #Write the Copasi XML files
            for i in range(no_of_jobs):
                job_scan_range = job_scans[i]
                job_min_value = job_scan_range[0]
                job_max_value = job_scan_range[-1]
                job_no_of_intervals = len(job_scan_range)-1


                # parameters['min'].attrib['value'] = str(job_min_value)
                self.scan_items[0]['min'] = job_min_value
                self.scan_items[0]['max'] = job_max_value
                self.scan_items[0]['num_steps'] = job_no_of_intervals

                # print(self.scan_items)
                set_scan_items(self.scan_items)

                #Set the report output
                output_file = 'output_%d.%d.txt' % (subtask_index, i)

                assign_report('Scan Parameters, Time, Concentrations, Volumes, and Global Quantity Values',
                              task=T.SCAN,
                              filename= output_file,
                              append= True
                             )

                filename = 'auto_copasi_%d.%d.cps' % (subtask_index, i)
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

        return model_files

    def prepare_ps_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index=1, rank='0', extraArgs=''):
        """ps condor jobs"""

    def process_ps_results(self, results_files):
        output_file = open(os.path.join(self.path, 'results.txt'), 'w')

        #Copy the contents of the first file to results.txt
        for line in open(os.path.join(self.path, results_files[0]), 'r'):
            output_file.write(line)

        #And for all other files, copy everything but the last line
        for result_file in results_files[1:]:
            firstLine = True
            for line in open(os.path.join(self.path, result_file), 'r'):
                if not firstLine:
                    output_file.write(line)
                firstLine = False

        output_file.close()

        return

    def prepare_or_jobs(self, repeats, repeats_per_job, subtask_index):
        """Prepare jobs for the optimization repeat task"""
        self._clear_tasks()

        optTask = get_opt_settings()
        #Even though we're not interested in the output at the moment, we'll set a report for the optimization task, or Copasi will complain!
        #Create a new report for the or task
        report_key = ''
        self._create_report('OR', report_key, 'auto_or_report')

        if "report" not in optTask:
            set_task_settings(T.OPTIMIZATION,
                              {'report': {}
                              }
                             )

        set_task_settings(T.OPTIMIZATION,
                          {'report': {'append': True,
                                      'filename': ''
                                     }
                          }
                         )

        no_of_jobs = int(math.ceil(float(repeats) / repeats_per_job))
        #Clear tasks and set the scan task as scheduled
        self._clear_tasks()

        scanTask = get_task_settings(T.SCAN)
        print("\nScan Task Settings: ")
        print(scanTask)

        if "report" not in scanTask:
            set_task_settings(T.SCAN,
                              {'report': {}
                              }
                             )

        set_task_settings(T.SCAN,
                          {'scheduled': True,
                           'update_model': True,
                           'report':{ 'append': True,
                                      'filename': ''
                                    },
                           'problem': { 'Subtask': 4,
                                        'Output in subtask': True,
                                      }
                          }
                         )

        #setting scan item. num_steps to 0
        set_scan_items([{'num_steps':0,
                         'type': 'repeat',
                        }])

        repeat_count = 0
        model_files = []

        for i in range(no_of_jobs):
            if repeats_per_job + repeat_count > repeats:
                    no_of_repeats = repeats - repeat_count
            else:
                no_of_repeats = repeats_per_job
                repeat_count += no_of_repeats

            set_scan_items([{'num_steps': no_of_repeats,
                             'type': 'repeat',
                            }])

            target = 'output_%d.%d.txt' % (subtask_index, i)

            assign_report('auto_or_report', task=T.SCAN, filename=target, append=True, confirm_overwrite = False)
            assign_report('auto_or_report', task=T.OPTIMIZATION, append=True, confirm_overwrite = False)

            # filename = os.path.join(os.getcwd(), 'auto_copasi_%d.%d.cps' % (subtask_index, i))
            filename = os.path.join(self.path, 'auto_copasi_%d.%d.cps' % (subtask_index, i))
            self.write(filename)

            model_files.append(filename)

        return model_files

    def prepare_or_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index=1, rank='0', extraArgs=''):
        """ or condor job"""
        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = 'output_%d.$(Process).txt' % subtask_index

        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'


        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file,
                                                                                   otherFiles='',
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )

        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename

    def process_or_results(self, filenames):
        """Process the results of the OR task by copying them all into one file, named raw_results.txt.
        As we copy, extract the best value, and write the details to results.txt"""

        maximize = get_opt_settings()['problem']['Maximize']

        output_file = open(os.path.join(self.path, 'raw_results.txt'), 'w')


        #Match a string of the format (    0.0995749    0.101685    0.108192    0.091224    )    0.091224    0
        #Contains parameter values, the best optimization value, the cpu time, and some other values.
        output_string = r'\(\s(?P<params>.+)\s\)\s+(?P<best_value>\S+)\s+(?P<cpu_time>\S+)\.*'
        output_re = re.compile(output_string)

        best_value = None
        best_line = None

        #Copy the contents of the first file to results.txt
        for line in open(os.path.join(self.path, filenames[0]), 'r'):
            output_file.write(line)
            if line != '\n':
                if output_re.match(line):
                    value = float(output_re.match(line).groupdict()['best_value'])

                    if best_value != None and maximize:
                        if value > best_value:
                            best_value = value
                            best_line = line
                    elif best_value != None and not maximize:
                        if value < best_value:
                            best_value = value
                            best_line = line
                    elif best_value == None:
                        best_value = value
                        best_line = line
            else:
                pass

        #And for all other files, copy everything but the last line
        for filename in filenames[1:]:
            firstLine = True
            for line in open(os.path.join(self.path,filename), 'r'):
                if not firstLine:
                    output_file.write(line)
                    if line != '\n':
                        if output_re.match(line):
                            value = float(output_re.match(line).groupdict()['best_value'])
                        if maximize:
                                if value > best_value:
                                    best_value = value
                                    best_line = line
                        elif not maximize:
                                if value < best_value:
                                    best_value = value
                                    best_line = line
                    else:
                        pass
                firstLine = False


        output_file.close()

        #Write the best value to results.txt
        output_file = open(os.path.join(self.path, 'results.txt'), 'w')

        output_file.write('Best value\t')

        #added by HB
        parameter_list = self.get_optimization_parameters()


        for parameter in parameter_list:
        #for parameter in self.get_optimization_parameters():
            #output_file.write(parameter[0].encode('utf8'))
            #above line is commented by HB as follows
            output_file.write(parameter[0])

            output_file.write('\t')
        output_file.write('\n')

        best_line_dict = output_re.match(best_line).groupdict()

        output_file.write(best_line_dict['best_value'])
        output_file.write('\t')

        for parameter in best_line_dict['params'].split('\t'):
            output_file.write(parameter)
            output_file.write('\t')
        output_file.close()

    def get_or_best_value(self):
        """Read the best value and best parameters from results.txt"""
        best_values = open(os.path.join(self.path, 'results.txt'),'r').readlines()

        headers = best_values[0].rstrip('\n').rstrip('\t').split('\t')
        values = best_values[1].rstrip('\n').rstrip('\t').split('\t')

        output = []

        for i in range(len(headers)):
            output.append((headers[i], values[i]))


        return output

    def prepare_pr_jobs(self, repeats, repeats_per_job, subtask_index, custom_report=False):
        """Prepare jobs for the parameter estimation repeat task"""

        #First, clear all tasks
        self._clear_tasks()

        fitTask = get_task_settings(T.PARAMETER_ESTIMATION)
        fitTask['update_model'] = False

        #Even though we're not interested in the output at the moment, we have to set a report for the parameter fitting task, or Copasi will complain!
        #Only do this if custom_report is false
        if not custom_report:
            #Create a new report for the or task
            report_key = None
            self._create_report('PR', report_key, 'auto_pr_report')

        if custom_report:
            #no need to assing a reference key. have to check what to do here further.
            pass

        #If no report has yet been set, report == None. Therefore, create new report
        if "report" not in fitTask:
            set_task_settings(T.PARAMETER_ESTIMATION,
                                  {'report': {}
                                  }
                                 )

        set_task_settings(T.PARAMETER_ESTIMATION,
                              {'report': {'append': True,
                                          'filename': ''
                                         }
                              }
                             )

        no_of_jobs = int(math.ceil(float(repeats) / repeats_per_job))

        #job Preparation
        self._clear_tasks()
        scanTask = get_task_settings(T.SCAN)

        if "report" not in scanTask:
            set_task_settings(T.SCAN,
                              {'report': {}
                              }
                             )

        set_task_settings(T.SCAN,
                          {'scheduled': True,
                           'update_model': True,
                           'report':{ 'append': True,
                                      'filename': ''
                                    },
                           'problem': { 'Subtask': 5,
                                        'Output in subtask': True,
                                      },
                          }
                         )

        set_scan_items([{'num_steps':0,
                         'type': 'repeat',
                        }])

        print("\nNew Scan Task Settings: ")
        print(get_task_settings(T.SCAN))

        #Prepare the Copasi files
        repeat_count = 0
        model_files = []

        for i in range(no_of_jobs):
            if repeats_per_job + repeat_count > repeats:
                no_of_repeats = repeats - repeat_count
            else:
                no_of_repeats = repeats_per_job
            repeat_count += no_of_repeats

            set_scan_items([{'num_steps': no_of_repeats,
                             'type': 'repeat',
                            }])

            target = 'output_%d.%d.txt' % (subtask_index, i)

            assign_report('auto_pr_report', task=T.SCAN, filename=target, append=True, confirm_overwrite = False)
            assign_report('auto_pr_report', task=T.PARAMETER_ESTIMATION, append=True, confirm_overwrite = False)

            # filename = os.path.join(os.getcwd(), 'auto_copasi_%d.%d.cps' % (subtask_index, i))
            filename = os.path.join(self.path, 'auto_copasi_%d.%d.cps' % (subtask_index, i))
            self.write(filename)
            # save_model(filename)

            model_files.append(filename)

        return model_files

    def prepare_pr_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index, data_files, rank='0', extraArgs=''):
        """Prepare the condor jobs for the parallel scan task"""
        ############
        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = 'output_%d.$(Process).txt' % subtask_index

        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'

        input_files_string = ', '
        for data_file in data_files:
            input_files_string += (data_file + ', ')
        input_files_string = input_files_string.rstrip(', ')

        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file,
                                                                                   otherFiles=input_files_string,
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )

        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename

    def process_pr_results(self, results_files, custom_report):
        """Process the results of the PR task by copying them all into one file, named raw_results.txt.
        As we copy, extract the best value, and write the details to results.txt"""

        output_file = open(os.path.join(self.path, 'raw_results.txt'), 'w')
        # output_file = open(os.path.join(os.getcwd(), 'raw_results.txt'), 'w')

        #Keep track of the last read line before a newline; this will be the best value from an optimization run
        last_line = ''
        #Match a string of the format (    0.0995749    0.101685    0.108192    0.091224    )    0.091224    0   100
        #Contains parameter values, the best optimization value, the cpu time, and some other values, e.g. particle numbers that Copasi likes to add. These could be removed, but they seem useful.
        output_string = r'.*\(\s(?P<params>.+)\s\)\s+(?P<best_value>\S+)\s+(?P<cpu_time>\S+)\s+(?P<function_evals>\S+)\.*'
        output_re = re.compile(output_string)

        best_value = None
        best_line = None

        #Copy the contents of the first file to results.txt
        for line in open(os.path.join(self.path, results_files[0]), 'r'):
        # for line in open(os.path.join(os.getcwd(), results_files[0]), 'r'):
            output_file.write(line)
            try:
                if line != '\n':
                    if output_re.match(line):
                        current_value = float(output_re.match(line).groupdict()['best_value'])
                        if best_value != None:
                            if current_value < best_value:
                                best_value = current_value
                                best_line = line
                        elif best_value == None:
                            best_value = current_value
                            best_line = line
                else:
                    pass
            except Exception as e:
                if custom_report:
                    pass
                else:
                    raise e

        for filename in results_files[1:]:
            firstLine = True
            for line in open(os.path.join(self.path, filename), 'r'):
            # for line in open(os.path.join(os.getcwd(), filename), 'r'):
                if not firstLine:
                    output_file.write(line)
                    try:
                        if line != '\n':
                            if output_re.match(line):
                                current_value = float(output_re.match(line).groupdict()['best_value'])
                                if current_value < best_value:
                                    best_value = current_value
                                    best_line = line
                        else:
                            pass
                    except Exception as e:
                        if custom_report:
                            pass
                        else:
                            raise e
                firstLine = False

        output_file.close()

        #Write the best value to results.txt
        output_file = open(os.path.join(self.path, 'results.txt'), 'w')
        # output_file = open(os.path.join(os.getcwd(), 'results.txt'), 'w')

        output_file.write('Best value\tCPU time\tFunction evals\t')

        #added by HB
        parameter_list = self.get_parameter_estimation_parameters()
        # parameter_list = get_parameter_estimation_parameters()

        for parameter in parameter_list:
            #for parameter in self.get_parameter_estimation_parameters():

            #output_file.write(parameter[0].encode('utf8'))
            #above line is commented by HB as follows
            output_file.write(parameter[0])

            output_file.write('\t')
        output_file.write('\n')

        best_line_dict = output_re.match(best_line).groupdict()

        output_file.write(best_line_dict['best_value'])
        output_file.write('\t')
        output_file.write(best_line_dict['cpu_time'])
        output_file.write('\t')
        output_file.write(best_line_dict['function_evals'])
        output_file.write('\t')

        for parameter in best_line_dict['params'].split('\t'):
            output_file.write(parameter)
            output_file.write('\t')

        output_file.close()
        if best_value != None:
            return True
        else:
            return False

    def get_pr_best_value(self):
        """Read the best value and best parameters from results.txt"""
        best_values = open(os.path.join(self.path, 'results.txt'),'r').readlines()
        # best_values = open(os.path.join(os.getcwd(), 'results.txt'),'r').readlines()

        headers = best_values[0].rstrip('\n').rstrip('\t').split('\t')
        values = best_values[1].rstrip('\n').rstrip('\t').split('\t')

        output = []

        for i in range(len(headers)):
            output.append((headers[i], values[i]))


        return output

    def create_pr_best_value_model(self, subtask_index, custom_report=False):
        """Create a .CPS model containing the best parameter values found by the PR task, and save it to filename"""

        self._clear_tasks()

        task_settings = get_task_settings(T.PARAMETER_ESTIMATION)
        log.debug(task_settings)

        if not custom_report:
            #Create a new report for the or task
            report_key = None
            self._create_report('PR', report_key, 'auto_pr_report')
            # _create_report('PR', report_key, 'auto_pr_report')

        if custom_report:
            #have to check what to do here.
            pass

        if "report" not in task_settings:
            set_task_settings(T.PARAMETER_ESTIMATION,
                                  {'report': {}
                                  }
                                 )

        if not custom_report:
            assign_report('auto_pr_report', task=T.PARAMETER_ESTIMATION, append=True, confirm_overwrite = False)

        task_settings['scheduled'] = True
        task_settings['update_model'] = True
        task_settings['report'] = {'append': True,
                                   'filename': 'copasi_temp_output.txt'
                                  }
        task_settings['problem'] = {'Randomize Start Values': False}

        #Step 2 - go through the parameter fitting task, and update the parameter start values
        best_parameter_values = self.get_pr_best_value()
        log.debug("Best parameter values: ")
        log.debug(best_parameter_values)

        #checking if optimizaiton item list is present
        if len(get_fit_parameters()) != 0:
            log.debug("Optimization item list is not empty.")
            fit_parameters = get_fit_parameters()       #extracting fit parameters
            start = fit_parameters.to_dict()['start']   #extracting start column values
            set_fit_param = True
        else:
            log.debug("Optimization item list empty.")
            set_fit_param = False

        #In results.txt, Index 0 = best value, 1 = CPU time, 2 = Function Evals, 3...n+3 = parameter values
        #Therefore, start at 3
        parameter_index = 3

        #looping through values in start column and updating it with the best values extracted from results.txt previously
        if set_fit_param:
            for element, value in start.items():
                old_value = value
                new_value = best_parameter_values[parameter_index][1]
                fit_parameters['start'] = fit_parameters['start'].replace([old_value], new_value)
                parameter_index += 1

            # updating new fit parameters
            set_fit_parameters(fit_parameters)

        #Step 3 - get the method, and set to current solution statistics
        task_settings.pop('method')
        task_settings['method'] = {'name': 'Current Solution Statistics',
                              'type': 'CurrentSolutionStatistics'
                              }
        print("new_settings: ")
        print(task_settings)
        set_task_settings(T.PARAMETER_ESTIMATION,
                          task_settings
                         )

        filename = 'auto_copasi_%d.0.cps' % subtask_index
        self.write(os.path.join(self.path, filename))

        return filename

    def prepare_pr_optimal_model_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index, data_files, rank='0', extraArgs=''):
        """Prepare the condor jobs for the parallel scan task"""
        ############
        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = ''



        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'

        input_files_string = ', '
        for data_file in data_files:
            input_files_string += (data_file + ', ')
        input_files_string = input_files_string.rstrip(', ')

        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file,
                                                                                   otherFiles=input_files_string,
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )

        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename

    def prepare_rw_jobs(self, repeats):
        """Prepare the jobs for the new raw mode.

        We assume that the model file is already set up for raw mode, i.e. at least one task marked as executable, reports set etc.
        Therefore, all we need to do is, for each repeat, append the report name with an appropriate suffix so the names are unique"""

        #The tasks we need to go through to append the report output
        taskList = [
            'Steady-State',
            'Time-Course',
            'Scan',
            'Metabolic Control Analysis',
            'Optimization',
            'Parameter Estimation',
            'Elementary Flux Modes',
            'Lyapunov Exponents',
            'Time Scale Separation Analysis',
            'Sensitivities',
            'Moieties',
            'Cross Section',         #newly added tasks
            'Linear Noise Approximation',
            'Time-Course Sensitivities'
            ]

        task_report_targets = {} #Store the report output targets
        #Create a new COPASI file for each repeat
        #Keep a note of the output files we're creating
        model_files = []
        output_files = []
        for i in range(repeats):
            #For each task, if the report output is set, append it with '_i'
            for taskName in taskList:
                try:
                    task = get_task_settings(taskName)
                    if i==0:
                        task_report_targets[taskName] = task['report']['filename']

                    task['report']['filename'] = str(i) + '_' + task_report_targets[taskName]
                    set_task_settings(taskName, task)

                    if i==0:
                        if task['scheduled'] == True:
                            output_files.append(task_report_targets[taskName])
                except:
                    pass

            filename = 'auto_copasi_1.%d.cps' %i
            target = os.path.join(self.path, filename)
            model_files.append(filename)

            self.write(target)

        return model_files, output_files

    def prepare_rw_condor_job(self, pool_type, address, repeats, raw_mode_args, data_files, output_files, rank='0'):
        """Prepare the condor jobs for the raw mode task"""

        #Prepare a customized condor job string
        #Somewhat confusingly, the original string was called raw_condor_string
        #We'll call this one raw_mode_string_with_args

        #We want to substitute '$filename' to ${copasiFile}
        args_string = Template(raw_mode_args).substitute(filename = '${copasiFile}', new_filename='run_${copasiFile}')

        raw_mode_string_with_args = Template(condor_spec.raw_mode_string).safe_substitute(args=args_string)

        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'

        #Build up a string containing a comma-seperated list of data files
        input_files_string = ', '
        output_files_string = ' ,'

        for data_file in data_files:
            input_files_string += data_file + ', '
        #And the same for the output files
        for output_file in output_files:
            output_files_string += '$(Process)_' + output_file + ', '
        input_files_string = input_files_string.rstrip(', ')
        output_files_string = output_files_string.rstrip(', ')
        ############
        #Build the appropriate .job file for the raw task
        copasi_file = 'auto_copasi_1.$(Process).cps'

        condor_job_string = Template(raw_mode_string_with_args).substitute(pool_type=pool_type,
                                                                           pool_address=address,
                                                                           binary_dir=binary_dir,
                                                                           transfer_executable=transfer_executable,
                                                                           copasiFile=copasi_file,
                                                                           otherFiles=input_files_string,
                                                                           outputFile=output_files_string,
                                                                           n=repeats,
                                                                           extraArgs='',
                                                                           rank=rank,
                                                                           )

        condor_job_filename = 'auto_condor_1.job'
        condor_file = open(os.path.join(self.path, condor_job_filename), 'w')
        condor_file.write(condor_job_string)
        condor_file.close()


        return condor_job_filename


    def prepare_sp_jobs(self, no_of_jobs, skip_load_balancing=False, custom_report=False):
        """Prepare jobs for the sigma point method"""

    def prepare_sp_condor_jobs(self, jobs, rank='0'):
        """Prepare the condor jobs for the parallel scan task"""

    def process_sp_results(self, jobs, custom_report=False):
        """Calculates the mean, covariance, and coefficients of variation for the parameters from the results of the parameter estimation tasks.  Prints these results to three files.  All equations numbers reference "Optimal experimental design with the sigma point method" (2009) by Schenkendorf, et. al."""

    def get_sp_mean(self):
        """Read the mean values from mean.txt"""

    def prepare_pl_files(self, subtask_index):
        """ Generating separate model files for each parameter of interest for PL task """
        #First, clear all tasks
        self._clear_tasks()
        original_fit_parameters = get_fit_parameters()

        param_list=[]
        model_files = []
        param_names_list = []
        file_param_assign = {}
        for i in range(len(original_fit_parameters)):
        # for i in range(1):
            current_param=[]        #current_param[name, lower, upper, cn]
            param_name = original_fit_parameters.index[i]   #name
            slog.debug("param_name: {}".format(param_name))         #added for debugging
            lower = original_fit_parameters.iloc[i, 0]      #lower
            upper = original_fit_parameters.iloc[i, 1]      #Upper
            POI = original_fit_parameters.iloc[i, 4]        #parameter of interest    #CN

            current_param.append(param_name)
            current_param.append(lower)
            current_param.append(upper)
            current_param.append(POI)

            param_list.append(current_param)
            #adding scan task with the current parameter
            set_scan_items([{'cn':POI,
                            'min': lower,
                            'max':upper,
                            'num_steps': 10}])

            set_task_settings(T.SCAN,
                          {'scheduled': True,
                          'update_model': True,})

            # adding report
            # report_name = "Profile_Likelihood-" + param_name.rsplit('.')[1]
            report_name = "Profile_Likelihood"
            # output_file_name = "Output-PL-" + param_name.rsplit('.')[1] + ".txt"
            output_file_name = "output_%d.%d.txt" % (subtask_index, i)

            ############### checking if report exists
            listOfReports = get_reports().index

            # to avoid duplicating reports, delete those which alread exist with the name "Profile-Likelihood"
            for report in listOfReports:
                if report == report_name:
                    remove_report(report)

            add_report(
                       name=report_name,
                       task=T.SCAN,
                       table=[
                              str(POI),
                              'CN=Root,Vector=TaskList[Parameter Estimation],Problem=Parameter Estimation,Reference=Best Value'
                              ]
                        )

            assign_report(name=report_name,
                          task= T.SCAN,
                          filename=output_file_name,
                          append=True)

            #removing the POI from the current list of fit parameters
            new_fit_params = original_fit_parameters.drop(param_name)
            set_fit_parameters(new_fit_params)

            slog.debug("param_name: {}".format(param_name))
            # param_name_actual = param_name.rsplit('.')[1]
            # slog.debug("param_name_actual: {}".format(param_name_actual))
            new_model_name = "auto_copasi_%d.%d.cps" % (subtask_index, i)
            filename = os.path.join(self.path, new_model_name)
            # save_model(new_model_name)
            self.write(filename)
            model_files.append(filename)
            # file_param_assign[new_model_name] = param_name_actual
            file_param_assign[new_model_name] = param_name
            file = open(os.path.join(self.path, "File-Parameter-Assignment.txt"), "w")
            for key, value in file_param_assign.items():
                file.write("%s : PoI = %s\n" % (key, value))
            file.close()
            # param_names_list.append(param_name_actual)

        return (model_files, file_param_assign)

    def prepare_pl_condor_job(self, pool_type, pool_address, number_of_jobs, subtask_index, data_files, rank='0',  extraArgs=''):
        condor_jobs = []

        # copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        copasi_file = 'auto_copasi_%d.$(Process).cps' % subtask_index
        output_file = 'output_%d.$(Process).txt' % subtask_index

        if pool_type == 'ec2':
            binary_dir = '/usr/local/bin'
            transfer_executable = 'NO'
        else:
            binary_dir, binary = os.path.split(settings.COPASI_LOCAL_BINARY)
            transfer_executable = 'YES'

        input_files_string = ', '
        for data_file in data_files:
            input_files_string += (data_file + ', ')
        input_files_string = input_files_string.rstrip(', ')

        condor_job_string = Template(condor_spec.raw_condor_job_string).substitute(copasiFile=copasi_file,
                                                                                   otherFiles=input_files_string,
                                                                                   rank=rank,
                                                                                   binary_dir = binary_dir,
                                                                                   transfer_executable = transfer_executable,
                                                                                   pool_type = pool_type,
                                                                                   pool_address = pool_address,
                                                                                   subtask=str(subtask_index),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )

        condor_job_filename = 'auto_condor_%d.job'%subtask_index
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename

    def process_original_pl_model(self):
        original_fit_parameters = get_fit_parameters()

        solution = run_parameter_estimation(method='Current Solution Statistics', calculate_statistics = True)
        obj_value = get_fit_statistic()['obj']

        param_to_plot_list = []

        for i in range(len(solution)):
            sol_list = []
            param_name = solution.index[i].rsplit('.')[1]
            sol = original_fit_parameters.iloc[i, 2]   #sol
            sol_list.append(param_name)
            sol_list.append(sol)
            sol_list.append(obj_value)

            param_to_plot_list.append(sol_list)

        # slog.debug("param_to_plot_list: {}".format(param_to_plot_list))


        return param_to_plot_list
