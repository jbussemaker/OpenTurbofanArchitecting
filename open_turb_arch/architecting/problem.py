"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright: (c) 2020, Deutsches Zentrum fuer Luft- und Raumfahrt e.V.
Contact: jasper.bussemaker@dlr.de
"""

import os
import copy
import pickle
import datetime
import numpy as np
from typing import *
from open_turb_arch.architecting.metric import *
from open_turb_arch.architecting.opt_defs import *
from open_turb_arch.evaluation.analysis.builder import *
from open_turb_arch.evaluation.architecture.architecture import *
from open_turb_arch.architecting.turbojet_architecture import get_turbojet_architecture

__all__ = ['ArchitectingProblem']


class ArchitectingProblem:
    """
    The main turbofan architecting problem class: creates an optimization problem from a set of architecting choices
    and metrics (as objectives, constraints, or generic metric). Also contains the logic for creating an architecture
    description from a design variable, and running the evaluation framework to actually evaluate an architecture.

    Use `save_results_folder` to store evaluation results (design vector, architecture, results, etc) using pickling.
    Each result is assigned an ID (file names are results_YYYYMMDD_HHMMSS_ID.pkl), which can be requested using
    `get_last_eval_id()`.

    If you need to pickle results containing the ArchitectingProblem, call `.finalize()` before!
    """

    def __init__(self, analysis_problem: AnalysisProblem, choices: List[ArchitectingChoice],
                 objectives: List[ArchitectingMetric], constraints: List[ArchitectingMetric] = None,
                 metrics: List[ArchitectingMetric] = None, max_iter=30, save_results_folder=None,
                 save_results_combined=None):

        self._an_problem = analysis_problem
        self.print_results = False
        self.verbose = False
        self._max_iter = max_iter

        self._choices = sorted(choices, key=lambda choice: choice.get_construction_order())
        self._objectives = objectives
        self._constraints = constraints or []
        self._metrics = metrics or []

        self._opt_des_vars: List[List[DesignVariable]] = None
        self._opt_obj: List[List[Objective]] = None
        self._opt_con: List[List[Constraint]] = None
        self._opt_met: List[List[OutputMetric]] = None

        self._check_definitions()

        self._results_cache = {}
        self._eval_id_cache = {}
        self._last_eval_id = None
        self.save_results_folder = save_results_folder
        self.save_results_combined = save_results_combined
        self._last_is_active = None

    @property
    def analysis_problem(self) -> AnalysisProblem:
        return self._an_problem

    @property
    def choices(self) -> List[ArchitectingChoice]:
        return list(self._choices)

    @property
    def objectives(self) -> List[ArchitectingMetric]:
        return list(self._objectives)

    @property
    def constraints(self) -> List[ArchitectingMetric]:
        return list(self._constraints)

    @property
    def metrics(self) -> List[ArchitectingMetric]:
        return list(self._metrics)

    @property
    def opt_des_vars(self) -> List[DesignVariable]:
        if self._opt_des_vars is None:
            self._opt_des_vars = [choice.get_design_variables() for choice in self.choices]
        return [des_var for des_vars in self._opt_des_vars for des_var in des_vars]

    @property
    def free_opt_des_vars(self) -> List[DesignVariable]:
        return [des_var for des_var in self.opt_des_vars if not des_var.is_fixed]

    @property
    def opt_objectives(self) -> List[Objective]:
        if self._opt_obj is None:
            self._opt_obj = [metric.get_opt_objectives(self.choices) for metric in self.objectives]
        return [obj for objs in self._opt_obj for obj in objs]

    @property
    def opt_constraints(self) -> List[Constraint]:
        if self._opt_con is None:
            opt_con = [metric.get_opt_constraints(self.choices) for metric in self.constraints]
            opt_con += [con for con in [choice.get_constraints() for choice in self.choices] if con is not None]
            self._opt_con = opt_con
        return [con for cons in self._opt_con for con in cons]

    @property
    def opt_metrics(self) -> List[OutputMetric]:
        if self._opt_met is None:
            self._opt_met = [metric.get_opt_metrics(self.choices) for metric in self.metrics]
        return [met for metrics in self._opt_met for met in metrics]

    def _check_definitions(self):
        if len(self.free_opt_des_vars) == 0:
            raise RuntimeError('No free design variables to design with!')

        if len(self.opt_objectives) == 0:
            raise RuntimeError('No objectives to design for!')

    def get_platypus_problem(self):
        from open_turb_arch.architecting.platypus import PlatypusArchitectingProblem
        return PlatypusArchitectingProblem(self)

    def get_pymoo_problem(self, parallel_pool=None):
        from open_turb_arch.architecting.pymoo import PymooArchitectingProblem
        return PymooArchitectingProblem(self, parallel_pool=parallel_pool)

    def get_openmdao_component(self):
        from open_turb_arch.architecting.openmdao import ArchitectingProblemComponent
        return ArchitectingProblemComponent(self)

    def get_random_design_vector(self) -> DesignVector:
        return [dv.encode(dv.get_random_value()) for dv in self.free_opt_des_vars]

    def iter_design_vectors(self, n_cont: int = 5) -> Generator[DesignVector, None, None]:

        def _iter_next_dv(dvs: List[DesignVariable]):
            if len(dvs) == 0:
                yield []
                return

            for value in dvs[0].iter_values(n_cont=n_cont):
                encoded = [dvs[0].encode(value)]
                for values in _iter_next_dv(dvs[1:]):
                    yield encoded+values

        yield from _iter_next_dv(self.free_opt_des_vars)

    def evaluate(self, design_vector: DesignVector) -> Tuple[DesignVector, List[float], List[float], List[float]]:

        # Generate architecture
        architecture, imputed_design_vector = self.generate_architecture(design_vector)

        # Return cached evaluation results
        dv_cache = tuple(imputed_design_vector)
        if dv_cache in self._results_cache:
            self._last_eval_id = self._eval_id_cache[dv_cache]
            return copy.copy(self._results_cache[dv_cache])

        # Evaluate architecture
        try:
            results = self.evaluate_architecture(architecture)
            obj_values, con_values, met_values = self.extract_metrics(architecture, imputed_design_vector, results)
        except:
            obj_values = np.zeros((len(self.opt_objectives),))*np.nan
            con_values = np.zeros((len(self.opt_constraints),))*np.nan
            met_values = np.zeros((len(self.opt_metrics),))*np.nan

        cache = self._results_cache, self._eval_id_cache
        self._results_cache = self._eval_id_cache = None  # To prevent pickling the results cache
        eval_id = self._save_results(
            problem=self,
            design_vector=design_vector,
            imputed_design_vector=imputed_design_vector,
            architecture=architecture,
            obj_values=obj_values,
            con_values=con_values,
            met_values=met_values,
        )
        self._results_cache, self._eval_id_cache = cache

        self._results_cache[dv_cache] = imputed_design_vector, obj_values, con_values, met_values
        self._eval_id_cache[dv_cache] = self._last_eval_id = eval_id
        return copy.copy(self._results_cache[dv_cache])

    def _save_results(self, **kwargs) -> Optional[int]:
        if self.save_results_folder is None:
            return

        try:
            contents = str(kwargs)
        except RecursionError:
            kwargs['architecture'] = 'RECURSION_ERROR'
            try:
                contents = str(kwargs)
            except RecursionError:
                contents = 'RECURSION_ERROR'

        os.makedirs(self.save_results_folder, exist_ok=True)
        eval_id = np.random.randint(1e8, 1e9-1)
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.save_results_folder, 'results_%s_%d.txt' % (ts, eval_id))
        with open(path, 'a') as f:
            f.write(contents)

        if self.save_results_combined:
            path_combo = os.path.join(self.save_results_folder, 'results_combined.txt')
            with open(path_combo, 'a') as f:
                f.write(contents+'\n\n')

        # path = os.path.join(self.save_results_folder, 'results_%s_%d.pkl' % (ts, eval_id))
        # with open(path, 'wb') as fp:
        #     pickle.dump(kwargs, fp)

        # if self.save_results_combined:
        #     path_combo = os.path.join(self.save_results_folder, 'results_combined.pkl')
        #     with open(path_combo, 'wb') as fp:
        #         pickle.dump(kwargs, fp)

        return eval_id

    def get_last_eval_id(self):
        return self._last_eval_id

    def generate_architecture(self, design_vector: DesignVector) -> Tuple[TurbofanArchitecture, DesignVector]:
        imputed_full_design_vector, decoded_design_vector = self.get_full_design_vector(design_vector)

        architecture = self._get_default_architecture()
        i_dv = 0
        is_active = np.ones((len(imputed_full_design_vector),), dtype=bool)
        for i, choice in enumerate(self.choices):
            n_dv = len(self._opt_des_vars[i])
            is_active_or_overwrite = choice.modify_architecture(architecture, self.analysis_problem, decoded_design_vector[i_dv:i_dv+n_dv])

            # Impute (i.e. set to default value) inactive design variables
            for j, is_act_or_overwrite in enumerate(is_active_or_overwrite):
                if is_act_or_overwrite is False:  # Not active --> impute the value
                    imputed_full_design_vector[i_dv+j] = self._opt_des_vars[i][j].get_imputed_value()
                    is_active[i_dv+j] = False
                elif is_act_or_overwrite is not True:  # Explicit overwritten value provided
                    imputed_full_design_vector[i_dv+j] = self._opt_des_vars[i][j].encode(is_act_or_overwrite)
                    is_active[i_dv+j] = False

            i_dv += n_dv

        imputed_free_design_vector = self.get_free_design_vector(imputed_full_design_vector)
        self._last_is_active = np.array(self.get_free_design_vector(is_active))
        return architecture, imputed_free_design_vector

    def get_last_is_active(self) -> np.ndarray:
        return self._last_is_active

    def get_full_design_vector(self, free_design_vector: DesignVector) -> Tuple[DesignVector, DecodedDesignVector]:
        full_design_vector, decoded_design_vector = [], []
        i_free = 0
        for i, des_var in enumerate(self.opt_des_vars):
            if des_var.is_fixed:
                fixed_value = des_var.get_fixed_value()
                decoded_design_vector.append(fixed_value)
                full_design_vector.append(des_var.encode(fixed_value))
            else:

                if i_free >= len(free_design_vector):
                    raise IndexError('Inconsistent design vector at index %d' % i_free)

                dv_value = free_design_vector[i_free]
                full_design_vector.append(dv_value)
                decoded_design_vector.append(des_var.decode(dv_value))

                i_free += 1

        return full_design_vector, decoded_design_vector

    def get_free_design_vector(self, design_vector: DesignVector) -> DesignVector:
        opt_des_vars = self.opt_des_vars
        return [value for i, value in enumerate(design_vector) if not opt_des_vars[i].is_fixed]

    @staticmethod
    def _get_default_architecture() -> TurbofanArchitecture:
        return get_turbojet_architecture()

    def evaluate_architecture(self, architecture: TurbofanArchitecture) -> OperatingMetricsMap:

        # Build the pyCycle/OpenMDAO analysis chain
        builder = CycleBuilder(architecture, self.analysis_problem, max_iter=self._max_iter)
        openmdao_problem = builder.get_problem()

        # Run the problem
        builder.run(openmdao_problem, print_solver=self.verbose)
        if self.print_results:
            builder.print_results(openmdao_problem)
        builder.view_n2(openmdao_problem, show_browser=False)
        return builder.get_metrics(openmdao_problem)

    def extract_metrics(self, architecture: TurbofanArchitecture, imputed_design_vector: DesignVector,
                        results: OperatingMetricsMap) -> Tuple[List[float], List[float], List[float]]:

        objective_values = []
        for metric in self.objectives:
            try:
                objective_values += list(metric.extract_obj(self.analysis_problem, results, architecture))
            except:
                objective_values.append(np.nan)

        constraint_values = []
        for metric in self.constraints:
            try:
                constraint_values += list(metric.extract_con(self.analysis_problem, results, architecture))
            except:
                constraint_values.append(np.nan)

        _, full_decoded_design_vector = self.get_full_design_vector(imputed_design_vector)
        i_dv = 0
        for i, choice in enumerate(self.choices):
            n_dv = len(self._opt_des_vars[i])
            choice_dv = full_decoded_design_vector[i_dv:i_dv+n_dv]
            choice_con_values = choice.evaluate_constraints(architecture, choice_dv, self.analysis_problem, results)
            if choice_con_values is not None:
                constraint_values += list(choice_con_values)
            i_dv += n_dv

        metric_values = []
        for metric in self.metrics:
            try:
                metric_values += list(metric.extract_met(self.analysis_problem, results, architecture))
            except:
                metric_values.append(np.nan)

        return objective_values, constraint_values, metric_values

    def finalize(self):
        """Prepares the problem so that it can be safely pickled to store the results"""
        self._results_cache = {}
        self._eval_id_cache = {}
