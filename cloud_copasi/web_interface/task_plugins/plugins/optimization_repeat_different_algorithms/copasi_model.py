#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from cloud_copasi.copasi.model import CopasiModel
from cloud_copasi.copasi import model
from cloud_copasi import settings
from lxml import etree
import os, time, math
from cloud_copasi.condor import condor_spec
from string import Template
import re

xmlns = model.xmlns

class ODCopasiModel(CopasiModel):

    def prepare_od_jobs(self, algorithms):
        """Prepare the jobs for the optimization with different algorithms task

        algorithms is a list of dicts containing the algorithm name, and another dict matching parameter names to values"""
        self._clear_tasks()
        optTask = self._getTask('optimization')
        optTask.attrib['scheduled'] = 'true'
        optTask.attrib['updateModel'] = 'true'

        #Create a new report for the or task
        report_key = 'condor_copasi_optimization_report'
        self._create_report('OR', report_key, 'auto_or_report')

        #And set the new report for the or task
        report = optTask.find(xmlns + 'Report')

        #If no report has yet been set, report == None. Therefore, create new report
        if report == None:
            report = etree.Element(xmlns + 'Report')
            optTask.insert(0,report)

        report.set('reference', report_key)
        report.set('append', '1')

        method = optTask.find(xmlns + 'Method')

        output_counter = 0

        output_files = []

        model_files = []

        for algorithm in algorithms:
            if algorithm['prefix'] == 'current_solution_statistics':
                method.clear()
                method.attrib['name'] = 'Current Solution Statistics'
                method.attrib['type'] = 'CurrentSolutionStatistics'



                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1


            if algorithm['prefix'] == 'genetic_algorithm':
                method.clear()
                method.attrib['name'] = 'Genetic Algorithm'
                method.attrib['type'] = 'GeneticAlgorithm'

                #Add sub parameters
                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Number of Generations'
                p1.attrib['type'] = 'unsignedInteger'
                p1.attrib['value'] = algorithm['params']['no_of_generations']

                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Population Size'
                p2.attrib['type'] = 'unsignedInteger'
                p2.attrib['value'] = algorithm['params']['population_size']

                p3 = etree.SubElement(method, xmlns+'Parameter')
                p3.attrib['name'] = 'Random Number Generator'
                p3.attrib['type'] = 'unsignedInteger'
                p3.attrib['value'] = algorithm['params']['random_number_generator']

                p4 = etree.SubElement(method, xmlns+'Parameter')
                p4.attrib['name'] = 'Seed'
                p4.attrib['type'] = 'unsignedInteger'
                p4.attrib['value'] = algorithm['params']['seed']

                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1

            if algorithm['prefix'] == 'genetic_algorithm_sr':
                method.clear()
                method.attrib['name'] = 'Genetic Algorithm SR'
                method.attrib['type'] = 'GeneticAlgorithmSR'

                #Add sub parameters
                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Number of Generations'
                p1.attrib['type'] = 'unsignedInteger'
                p1.attrib['value'] = algorithm['params']['no_of_generations']

                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Population Size'
                p2.attrib['type'] = 'unsignedInteger'
                p2.attrib['value'] = algorithm['params']['population_size']

                p3 = etree.SubElement(method, xmlns+'Parameter')
                p3.attrib['name'] = 'Random Number Generator'
                p3.attrib['type'] = 'unsignedInteger'
                p3.attrib['value'] = algorithm['params']['random_number_generator']

                p4 = etree.SubElement(method, xmlns+'Parameter')
                p4.attrib['name'] = 'Seed'
                p4.attrib['type'] = 'unsignedInteger'
                p4.attrib['value'] = algorithm['params']['seed']

                p5 = etree.SubElement(method, xmlns+'Parameter')
                p5.attrib['name'] = 'Pf'
                p5.attrib['type'] = 'float'
                p5.attrib['value'] = algorithm['params']['pf']

                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1

            if algorithm['prefix'] == 'hooke_and_jeeves':
                method.clear()
                method.attrib['name'] = 'Hooke & Jeeves'
                method.attrib['type'] = 'HookeJeeves'

                #Add sub parameters
                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Iteration Limit'
                p1.attrib['type'] = 'unsignedInteger'
                p1.attrib['value'] = algorithm['params']['iteration_limit']

                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Tolerance'
                p2.attrib['type'] = 'float'
                p2.attrib['value'] = algorithm['params']['tolerance']

                p3 = etree.SubElement(method, xmlns+'Parameter')
                p3.attrib['name'] = 'Rho'
                p3.attrib['type'] = 'float'
                p3.attrib['value'] = algorithm['params']['rho']

                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1

            if algorithm['prefix'] == 'levenberg_marquardt':
                method.clear()
                method.attrib['name'] = 'Levenberg - Marquardt'
                method.attrib['type'] = 'LevenbergMarquardt'

                #Add sub parameters
                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Iteration Limit'
                p1.attrib['type'] = 'unsignedInteger'
                p1.attrib['value'] = algorithm['params']['iteration_limit']

                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Tolerance'
                p2.attrib['type'] = 'float'
                p2.attrib['value'] = algorithm['params']['tolerance']


                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1

            if algorithm['prefix'] == 'evolutionary_programming':
                method.clear()
                method.attrib['name'] = 'Evolutionary Programming'
                method.attrib['type'] = 'EvolutionaryProgram'

                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Number of Generations'
                p1.attrib['type'] = 'unsignedInteger'
                p1.attrib['value'] = algorithm['params']['no_of_generations']

                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Population Size'
                p2.attrib['type'] = 'unsignedInteger'
                p2.attrib['value'] = algorithm['params']['population_size']

                p3 = etree.SubElement(method, xmlns+'Parameter')
                p3.attrib['name'] = 'Random Number Generator'
                p3.attrib['type'] = 'unsignedInteger'
                p3.attrib['value'] = algorithm['params']['random_number_generator']

                p4 = etree.SubElement(method, xmlns+'Parameter')
                p4.attrib['name'] = 'Seed'
                p4.attrib['type'] = 'unsignedInteger'
                p4.attrib['value'] = algorithm['params']['seed']


                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1

            if algorithm['prefix'] == 'random_search':
                method.clear()
                method.attrib['name'] = 'Random Search'
                method.attrib['type'] = 'RandomSearch'

                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Number of Iterations'
                p1.attrib['type'] = 'unsignedInteger'
                p1.attrib['value'] = algorithm['params']['no_of_iterations']


                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Random Number Generator'
                p2.attrib['type'] = 'unsignedInteger'
                p2.attrib['value'] = algorithm['params']['random_number_generator']

                p3 = etree.SubElement(method, xmlns+'Parameter')
                p3.attrib['name'] = 'Seed'
                p3.attrib['type'] = 'unsignedInteger'
                p3.attrib['value'] = algorithm['params']['seed']

                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1


            if algorithm['prefix'] == 'nelder_mead':
                method.clear()
                method.attrib['name'] = 'Nelder - Mead'
                method.attrib['type'] = 'NelderMead'

                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Iteration Limit'
                p1.attrib['type'] = 'unsignedInteger'
                p1.attrib['value'] = algorithm['params']['iteration_limit']


                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Tolerance'
                p2.attrib['type'] = 'unsignedFloat'
                p2.attrib['value'] = algorithm['params']['tolerance']

                p3 = etree.SubElement(method, xmlns+'Parameter')
                p3.attrib['name'] = 'Scale'
                p3.attrib['type'] = 'unsignedFloat'
                p3.attrib['value'] = algorithm['params']['scale']


                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1

            if algorithm['prefix'] == 'particle_swarm':
                method.clear()
                method.attrib['name'] = 'Particle Swarm'
                method.attrib['type'] = 'ParticleSwarm'

                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Iteration Limit'
                p1.attrib['type'] = 'unsignedInteger'
                p1.attrib['value'] = algorithm['params']['iteration_limit']


                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Swarm Size'
                p2.attrib['type'] = 'unsignedInteger'
                p2.attrib['value'] = algorithm['params']['swarm_size']

                p3 = etree.SubElement(method, xmlns+'Parameter')
                p3.attrib['name'] = 'Std. Deviation'
                p3.attrib['type'] = 'unsignedFloat'
                p3.attrib['value'] = algorithm['params']['std_deviation']

                p4 = etree.SubElement(method, xmlns+'Parameter')
                p4.attrib['name'] = 'Random Number Generator'
                p4.attrib['type'] = 'unsignedInteger'
                p4.attrib['value'] = algorithm['params']['random_number_generator']

                p5 = etree.SubElement(method, xmlns+'Parameter')
                p5.attrib['name'] = 'Seed'
                p5.attrib['type'] = 'unsignedInteger'
                p5.attrib['value'] = algorithm['params']['seed']


                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1


            if algorithm['prefix'] == 'praxis':
                method.clear()
                method.attrib['name'] = 'Praxis'
                method.attrib['type'] = 'Praxis'

                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Tolerance'
                p1.attrib['type'] = 'float'
                p1.attrib['value'] = algorithm['params']['tolerance']

                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1

            if algorithm['prefix'] == 'truncated_newton':
                method.clear()
                method.attrib['name'] = 'Truncated Newton'
                method.attrib['type'] = 'TruncatedNewton'

                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1

            if algorithm['prefix'] == 'simulated_annealing':
                method.clear()
                method.attrib['name'] = 'Simulated Annealing'
                method.attrib['type'] = 'SimulatedAnnealing'


                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Start Temperature'
                p1.attrib['type'] = 'unsignedFloat'
                p1.attrib['value'] = algorithm['params']['start_temperature']


                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Cooling Factor'
                p2.attrib['type'] = 'unsignedFloat'
                p2.attrib['value'] = algorithm['params']['cooling_factor']

                p3 = etree.SubElement(method, xmlns+'Parameter')
                p3.attrib['name'] = 'Tolerance'
                p3.attrib['type'] = 'unsignedFloat'
                p3.attrib['value'] = algorithm['params']['tolerance']

                p4 = etree.SubElement(method, xmlns+'Parameter')
                p4.attrib['name'] = 'Random Number Generator'
                p4.attrib['type'] = 'unsignedInteger'
                p4.attrib['value'] = algorithm['params']['random_number_generator']

                p5 = etree.SubElement(method, xmlns+'Parameter')
                p5.attrib['name'] = 'Seed'
                p5.attrib['type'] = 'unsignedInteger'
                p5.attrib['value'] = algorithm['params']['seed']

                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1


            if algorithm['prefix'] == 'evolution_strategy':
                method.clear()
                method.attrib['name'] = 'Evolution Strategy (SRES)'
                method.attrib['type'] = 'EvolutionaryStrategySR'

                #Add sub parameters
                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Number of Generations'
                p1.attrib['type'] = 'unsignedInteger'
                p1.attrib['value'] = algorithm['params']['no_of_generations']

                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Population Size'
                p2.attrib['type'] = 'unsignedInteger'
                p2.attrib['value'] = algorithm['params']['population_size']

                p3 = etree.SubElement(method, xmlns+'Parameter')
                p3.attrib['name'] = 'Random Number Generator'
                p3.attrib['type'] = 'unsignedInteger'
                p3.attrib['value'] = algorithm['params']['random_number_generator']

                p4 = etree.SubElement(method, xmlns+'Parameter')
                p4.attrib['name'] = 'Seed'
                p4.attrib['type'] = 'unsignedInteger'
                p4.attrib['value'] = algorithm['params']['seed']

                p5 = etree.SubElement(method, xmlns+'Parameter')
                p5.attrib['name'] = 'Pf'
                p5.attrib['type'] = 'float'
                p5.attrib['value'] = algorithm['params']['pf']

                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
                model_files.append(filename)

                output_counter += 1

            if algorithm['prefix'] == 'steepest_descent':
                method.clear()
                method.attrib['name'] = 'Steepest Descent'
                method.attrib['type'] = 'SteepestDescent'


                p1 = etree.SubElement(method, xmlns+'Parameter')
                p1.attrib['name'] = 'Iteration Limit'
                p1.attrib['type'] = 'unsignedInteger'
                p1.attrib['value'] = algorithm['params']['iteration_limit']


                p2 = etree.SubElement(method, xmlns+'Parameter')
                p2.attrib['name'] = 'Tolerance'
                p2.attrib['type'] = 'float'
                p2.attrib['value'] = algorithm['params']['tolerance']

                output_filename = 'output_1.%d.txt'%output_counter
                report.attrib['target'] = output_filename
                output_files.append(output_filename)
                filename = 'auto_copasi_1.%d.cps' % output_counter
                self.write(os.path.join(self.path, filename))
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
        #Check if we're minimizing or maximizing!
        optTask = self._getTask('optimization')
        problem =  optTask.find(xmlns + 'Problem')
        for parameter in problem:
            if parameter.attrib['name']=='Maximize':
                max_param = parameter.attrib['value']
        if max_param == '0':
            maximize = False
        else:
            maximize = True

        #Match a string of the format (    0.0995749    0.101685    0.108192    0.091224    )    0.091224    0
        #Contains parameter values, the best optimization value, the cpu time, and some other values.
        output_string = r'\(\s(?P<params>.+)\s\)\s+(?P<best_value>\S+)\s+(?P<cpu_time>\S+)\s+(?P<function_evals>\S+)\.*'
        output_re = re.compile(output_string)

        best_values = [] # In this list, store a tuple containing the best value, and the file containing it
        none_values = [] #And here we keep a note of any algorithms for which no result was found
        best_value = None

        #Read through each output file, and extract the last set of params
        #Keep track of the file with the best result

        for algorithm_index in range(len(algorithm_list)):
            output_file = output_files[algorithm_index]
            for line in open(os.path.join(self.path, output_file), 'r'):
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

#             if best_value == None:
#                 best_value = best_value_for_file
#                 best_values.append((best_value, algorithm_index))
#             elif maximize and best_value_for_file >= best_value:
#                 best_value = best_value_for_file
#                 best_values.append((best_value, algorithm_index))
#             elif not maximize and best_value_for_file <= best_value:
#                 best_value = best_value_for_file
#                 best_values.append((best_value, algorithm_index))

        #We now know what the best value is, so can remove anything from the list best_values that is less than or greater than this, depending on whether we're maximizing
        #Copy the items we want to keep to output

        sorted_list = sorted(best_values, key=lambda val:val[0], reverse=maximize)

#         for value, algorithm_index in sorted_list:
#             if value == best_value:
#                 output.append((value, algorithm_index))

        #Now write the algorithm name, best value and parameter values to a file

        if write:
            output_file = open(os.path.join(self.path, 'results.txt'), 'w')

            output_file.write('Algorithm name\tBest value\tCPU time\tFunction evals\t')
            for name, lowerBound, upperBound, startValue  in self.get_optimization_parameters():
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
            output.append(line.rstrip('\n').rstrip('\t').split('\t')[0:4])#Only return the first 4 columns, not param values
        return output
