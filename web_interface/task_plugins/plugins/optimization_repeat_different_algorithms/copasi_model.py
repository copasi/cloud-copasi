#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
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
from cloud_copasi.condor import condor_spec
from string import Template
import re

class ODCopasiModel_BasiCO(CopasiModel_BasiCO):
    """ Implementation using BasiCO library"""

    def prepare_od_jobs(self, algorithms):
        """Prepare the jobs for the optimization with different algorithms task

        algorithms is a list of dicts containing the algorithm name, and another dict matching parameter names to values"""
        self._clear_tasks()
        optTask = get_opt_settings()
        set_opt_settings({'scheduled': True,
                      'update_model': True
                    })

        #Create a new report for the or task
        report_key = ''
        self._create_report('OR', report_key, 'auto_or_report')

        if "report" not in optTask:
            set_opt_settings({'report': {}
                        })

        assign_report('auto_or_report', task=T.OPTIMIZATION, append=True, confirm_overwrite = False)

        #extracting method information from the optimization tasks
        #method = optTask['method']

        output_counter = 0
        output_files = []
        model_files = []

        for algorithm in algorithms:
            if algorithm['prefix'] == 'current_solution_statistics':
                set_opt_settings({'method':{'name':'Current Solution Statistics'}})

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'genetic_algorithm':
                set_opt_settings({'method':{'name':'Genetic Algorithm',
                                            'Number of Generations': algorithm['params']['no_of_generations'],
                                            'Population Size': algorithm['params']['population_size'],
                                            'Random Number Generator': algorithm['params']['random_number_generator'],
                                            'Seed': algorithm['params']['seed']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'genetic_algorithm_sr':
                set_opt_settings({'method':{'name':'Genetic Algorithm SR',
                                            'Number of Generations': algorithm['params']['no_of_generations'],
                                            'Population Size': algorithm['params']['population_size'],
                                            'Random Number Generator': algorithm['params']['random_number_generator'],
                                            'Seed': algorithm['params']['seed'],
                                            'Pf': algorithm['params']['pf']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'hooke_and_jeeves':
                set_opt_settings({'method':{'name':'Hooke & Jeeves',
                                            'Iteration Limit': algorithm['params']['iteration_limit'],
                                            'Tolerance': algorithm['params']['tolerance'],
                                            'Rho': algorithm['params']['rho']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'levenberg_marquardt':
                set_opt_settings({'method':{'name':'Levenberg - Marquardt',
                                            'Iteration Limit': algorithm['params']['iteration_limit'],
                                            'Tolerance': algorithm['params']['tolerance']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'evolutionary_programming':
                set_opt_settings({'method':{'name':'Evolutionary Programming',
                                            'Number of Generations': algorithm['params']['no_of_generations'],
                                            'Population Size': algorithm['params']['population_size'],
                                            'Random Number Generator': algorithm['params']['random_number_generator'],
                                            'Seed': algorithm['params']['seed']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'random_search':
                set_opt_settings({'method':{'name':'Random Search',
                                            'Number of Iterations': algorithm['params']['no_of_iterations'],
                                            'Random Number Generator': algorithm['params']['random_number_generator'],
                                            'Random Number Generator': algorithm['params']['random_number_generator'],
                                            'Seed': algorithm['params']['seed']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'nelder_mead':
                set_opt_settings({'method':{'name':'Nelder - Mead',
                                            'Iteration Limit': algorithm['params']['iteration_limit'],
                                            'Tolerance': algorithm['params']['tolerance'],
                                            'Scale': algorithm['params']['scale']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'particle_swarm':
                set_opt_settings({'method':{'name':'Particle Swarm',
                                            'Iteration Limit': algorithm['params']['iteration_limit'],
                                            'Swarm Size': algorithm['params']['swarm_size'],
                                            'Std. Deviation': algorithm['params']['std_deviation'],
                                            'Random Number Generator': algorithm['params']['random_number_generator'],
                                            'Seed': algorithm['params']['seed']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'praxis':
                set_opt_settings({'method':{'name':'Praxis',
                                            'Tolerance': algorithm['params']['tolerance']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'truncated_newton':
                set_opt_settings({'method':{'name':'Truncated Newton'}})

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'simulated_annealing':
                set_opt_settings({'method':{'name':'Simulated Annealing',
                                            'Start Temperature': algorithm['params']['start_temperature'],
                                            'Cooling Factor': algorithm['params']['cooling_factor'],
                                            'Tolerance': algorithm['params']['tolerance'],
                                            'Random Number Generator': algorithm['params']['random_number_generator'],
                                            'Seed': algorithm['params']['seed']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'evolution_strategy':
                set_opt_settings({'method':{'name':'Evolution Strategy (SRES)',
                                            'Number of Generations': algorithm['params']['no_of_generations'],
                                            'Population Size': algorithm['params']['population_size'],
                                            'Random Number Generator': algorithm['params']['random_number_generator'],
                                            'Seed': algorithm['params']['seed'],
                                            'Pf': algorithm['params']['pf']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)
                self.write(filename)

                model_files.append(filename)
                output_counter += 1

            if algorithm['prefix'] == 'steepest_descent':
                set_opt_settings({'method':{'name':'Steepest Descent',
                                            'Iteration Limit': algorithm['params']['iteration_limit'],
                                            'Tolerance': algorithm['params']['tolerance']
                                            }
                                })

                output_filename = 'output_1.%d.txt'%output_counter
                set_opt_settings({'report':{'filename':output_filename}})
                output_files.append(output_filename)

                #for writing a file on localhost for testing. Remove on server
                # filename = os.path.join(os.getcwd(), 'auto_copasi_1.%d.cps' % output_counter)
                # save_model(filename)

                #for writing a file on server. Uncomment on server
                filename = os.path.join(self.path, 'auto_copasi_1.%d.cps' % output_counter)


                self.write(filename)

                model_files.append(filename)
                output_counter += 1

        return model_files, output_files

    def prepare_od_condor_jobs(self, pool_type, pool_address, number_of_jobs, rank='0', extraArgs=''):
        copasi_file = 'auto_copasi_1.$(Process).cps'
        output_file = 'output_1.$(Process).txt'

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
                                                                                   subtask=str(1),
                                                                                   n = number_of_jobs,
                                                                                   outputFile = output_file,
                                                                                   extraArgs='',
                                                                                   )

        condor_job_filename = 'auto_condor_1.job'
        condor_job_full_filename = os.path.join(self.path, condor_job_filename)
        condor_file = open(condor_job_full_filename, 'w')
        condor_file.write(condor_job_string)
        condor_file.close()

        return condor_job_filename

    def process_od_results(self, algorithm_list, output_files, write=True, return_list=False):
        """Read through the various output files, and find the best result. Return this, along with information about the chosen algorithm"""

        maximize = get_opt_settings()['problem']['Maximize']

        output_string = r'\(\s(?P<params>.+)\s\)\s+(?P<best_value>\S+)\s+(?P<cpu_time>\S+)\s+(?P<function_evals>\S+)\.*'
        output_re = re.compile(output_string)

        best_values = [] # In this list, store a tuple containing the best value, and the file containing it
        none_values = [] #And here we keep a note of any algorithms for which no result was found
        best_value = None

        for algorithm_index in range(len(algorithm_list)):
            output_file = output_files[algorithm_index]
            for line in open(os.path.join(self.path, output_file), 'r'):
            # for line in open(os.path.join(os.getcwd(), output_file), 'r'):
                match = output_re.match(line)
                best_value_for_file = None
                if match:
                    current_best_value = float(match.groupdict()['best_value'])
                    if best_value_for_file == None:
                        best_value_for_file = current_best_value

                    elif maximize and current_best_value >= best_value:
                        best_value_for_file = current_best_value

                    elif not maximize and current_best_value <= best_value:
                        best_value_for_file = current_best_value

            if best_value_for_file != None:
                best_values.append((best_value_for_file, algorithm_index))
            else:
                none_values.append((best_value_for_file, algorithm_index))

        #We now know what the best value is, so can remove anything from the list best_values that is less than or greater than this, depending on whether we're maximizing
        #Copy the items we want to keep to output

        sorted_list = sorted(best_values, key=lambda val:val[0], reverse=maximize)

        #Now write the algorithm name, best value and parameter values to a file
        if write:
            output_file = open(os.path.join(self.path, 'results.txt'), 'w')
            # output_file = open(os.path.join(os.getcwd(), 'results.txt'), 'w')

            output_file.write('Algorithm name\tBest value\tCPU time\tFunction evals\t')
            for name, lowerBound, upperBound, startValue  in self.get_optimization_parameters():
            #for local testing
            # for name, lowerBound, upperBound, startValue  in get_optimization_parameters():
                output_file.write(name + '\t')
            output_file.write('\n')

            for value, algorithm_index in sorted_list:
                #Filename is of the format algorithm_name_out.txt
                #Write the algorithm name
                output_file.write(algorithm_list[algorithm_index])
                output_file.write('\t')
                output_file.write(str(value) + '\t')

                #Read through the file and extract the last line
                for line in open(os.path.join(self.path, output_files[algorithm_index])):
                # for line in open(os.path.join(os.getcwd(), output_files[algorithm_index])):
                    last_line = line
                match = output_re.match(line)
                if match:
                    g = match.groupdict()
                    output_file.write(g['cpu_time'] + '\t')
                    output_file.write(g['function_evals'] + '\t')
                    for parameter in g['params'].split('\t'):
                        output_file.write(parameter + '\t')
                    output_file.write('\n')

            for value, algorithm_index in none_values:
                output_file.write('%s\t%s\t \t ' % (algorithm_list[algorithm_index], 'None'))
                output_file.write('\t '*len(self.get_optimization_parameters()))
                # output_file.write('\t '*len(get_optimization_parameters()))
                output_file.write('\n')
            output_file.close()

        if return_list:
            #Return a list containing the algorithm index of the sorted list
            full_list = sorted_list + none_values

            return [index for (value, index) in full_list]

    def get_od_results(self):
        """Open results.txt, parse the output and return it"""
        output = []
        for line in open(os.path.join(self.path, 'results.txt')):
        # for line in open(os.path.join(os.getcwd(), 'results.txt')):
            output.append(line.rstrip('\n').rstrip('\t').split('\t')[0:4])#Only return the first 4 columns, not param values
        return output
