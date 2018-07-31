# Copyright (c) 2016 The UUV Simulator Authors.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import yaml
import re
from uuv_cost_function import CostFunction
from .utils import init_logger, parse_smac_input, SIMULATION_LOGGER


class OptConfiguration(object):
    CONFIG = None


    def __init__(self, input_data):
        if isinstance(input_data, str):
            assert os.path.isfile(input_data)

            self.opt_config_filename = input_data
            with open(self.opt_config_filename, 'r') as opt_config_file:
                self._opt_config = yaml.load(opt_config_file)
        elif isinstance(input_data, dict):
            self._opt_config = input_data

        assert 'cost_fcn' in self._opt_config, 'Cost function configuration available'
        
        if 'parameters' in self._opt_config:
            self.parameters = self._opt_config['parameters']
        else:
            self.parameters = None

        if 'max_num_processes' not in self._opt_config:
            self.max_num_processes = 2
        else:
            self.max_num_processes = self._opt_config['max_num_processes']

        assert self.max_num_processes > 0, \
            'Maximum number of simulation processes must be greater than zero'

        SIMULATION_LOGGER.info('Max. number of processes=%d' % self.max_num_processes)

        if 'log_filename' not in self._opt_config:
            self._log_filename = None
        else:
            self._log_filename = self._opt_config['log_filename']

        init_logger(self._log_filename)

        task = self._opt_config['task']

        if isinstance(task, list):
            SIMULATION_LOGGER.info('Multiple tasks found:')
            for t in task:
                SIMULATION_LOGGER.info('\t - %s' % t)

            self.tasks = task
        else:
            SIMULATION_LOGGER.info('Retrieving filename for task function=' + task)
            self.tasks = [task]

        atoi = lambda a: int(a) if a.isdigit() else a
        natural_keys = lambda text: [atoi(c) for c in re.split('(\d+)', text)]

        self.tasks.sort(key=natural_keys)
        SIMULATION_LOGGER.info('Task files=')
        for task in self.tasks:
            SIMULATION_LOGGER.info('\t - ' + task)

        self.results_dir = self._opt_config['output_dir']
        SIMULATION_LOGGER.info(
            'Retrieving output directory for partial results=' + self.results_dir)

        self.record_all = False

        if 'store_all_results' in self._opt_config:
            self.record_all = self._opt_config['store_all_results']

        SIMULATION_LOGGER.info('Record all partial results? ' + str(self.record_all))

        if 'store_kpis_only' in self._opt_config:
            self.store_kpis_only = self._opt_config['store_kpis_only']
        else:
            self.store_kpis_only = True

        self.evaluation_time_offset = 0

        if 'evaluation_time_offset' in self._opt_config:
            self.evaluation_time_offset = self._opt_config['evaluation_time_offset']

        assert self.evaluation_time_offset >= 0

        self.constraints = None
        self.cost_fcn = None

        self.params = None

        if 'cost_fcn' in self._opt_config:
            SIMULATION_LOGGER.info('Initializing cost function')
            self.cost_fcn = CostFunction()
            if isinstance(self._opt_config['cost_fcn'], dict):                
                cf = self._opt_config['cost_fcn']
                SIMULATION_LOGGER.info('Cost function imported from list')
            elif isinstance(self._opt_config['cost_fcn'], str):
                assert os.path.isfile(self._opt_config['cost_fcn']), 'Cost function file is invalid'
                assert '.yml' in self._opt_config['cost_fcn'] or '.yaml' in self._opt_config['cost_fcn']

                with open(self._opt_config['cost_fcn']) as cf_file:
                    cf = yaml.load(cf_file)

                SIMULATION_LOGGER.info(cf)

                SIMULATION_LOGGER.info('Cost function loaded from file, filename=' + self._opt_config['cost_fcn'])
            else:
                SIMULATION_LOGGER.error('Invalid input cost function')
                print(self._opt_config['cost_fcn'])
                raise Exception('Invalid input cost function')

            self.cost_fcn.from_dict(cf)

        if 'constraints' in self._opt_config:
            self.constraints = self._opt_config['constraints']
            if isinstance(self.constraints, list):                
                self.cost_fcn.add_constraints(self._opt_config['constraints'])
                SIMULATION_LOGGER.info('Constraints imported from list')
            elif isinstance(self._opt_config['constraints'], str):                
                assert os.path.isfile(self._opt_config['constraints']), 'Constraint file is invalid'
                assert '.yml' in self._opt_config['constraints'] or '.yaml' in self._opt_config['constraints']
    
                with open(self._opt_config['constraints']) as c_file:
                    constraints = yaml.load(c_file)

                self.cost_fcn.add_constraints(constraints)
                SIMULATION_LOGGER.info('Constraints loaded from file, filename=' + self._opt_config['constraints'])
            else:
                SIMULATION_LOGGER.error('Invalid input constraints list')
                raise Exception('Invalid input constraints list')
                

    @staticmethod
    def get_instance(input_data=None):
        if input_data is None:
            assert OptConfiguration.CONFIG is not None
            return OptConfiguration.CONFIG
        else:
            OptConfiguration.CONFIG = OptConfiguration(input_data)
            return OptConfiguration.CONFIG

    def parse_input(self, args):
        assert 'input_map' in self._opt_config, 'Input parameter map is not available'
        self.params = parse_smac_input(args, self._opt_config['input_map'])

    def print_params(self):
        if self.params is None:
            SIMULATION_LOGGER.info('No parameters have been loaded')
        else:
            SIMULATION_LOGGER.info('Simulation parameters=')
            for tag in self.params:
                SIMULATION_LOGGER.info('\t%s=%s' % (tag, str(self.params[tag])))

    def compute_cost_fcn(self, kpis):
        if self.cost_fcn is None:
            return None
        self.cost_fcn.set_kpis(kpis)
        return self.cost_fcn.compute()
