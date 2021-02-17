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

import random
import numpy as np
from typing import *
from enum import Enum
from dataclasses import dataclass
from open_turb_arch.evaluation.analysis import *

__all__ = ['DesignVariable', 'ContinuousDesignVariable', 'IntDesignVariableType', 'IntegerDesignVariable',
           'OutputMetric', 'ObjectiveDirection', 'Objective', 'ConstraintDirection', 'Constraint',
           'DesignVector', 'EncodedValue', 'DecodedValue', 'DecodedDesignVector', 'OperatingMetricsMap',
           'AnalysisProblem', 'OperatingCondition', 'DesignCondition', 'EvaluateCondition']


EncodedValue = Union[float, int]
DecodedValue = Union[float, Any]
DesignVector = List[EncodedValue]
DecodedDesignVector = List[DecodedValue]
OperatingMetricsMap = Dict[OperatingCondition, OperatingMetrics]


@dataclass
class DesignVariable:
    name: str

    def encode(self, value: DecodedValue) -> EncodedValue:
        raise NotImplementedError

    def decode(self, value: EncodedValue) -> DecodedValue:
        raise NotImplementedError

    @property
    def is_fixed(self) -> bool:
        raise NotImplementedError

    def get_fixed_value(self) -> DecodedValue:
        raise NotImplementedError

    def get_imputed_value(self) -> EncodedValue:
        raise NotImplementedError

    def get_random_value(self) -> DecodedValue:
        raise NotImplementedError

    def iter_values(self, n_cont: int = 5) -> Generator[DecodedValue, None, None]:
        raise NotImplementedError


@dataclass
class ContinuousDesignVariable(DesignVariable):
    bounds: Tuple[float, float]
    fixed_value: float = None

    def encode(self, value: DecodedValue) -> EncodedValue:
        return value

    def decode(self, value: EncodedValue) -> DecodedValue:
        return value

    @property
    def is_fixed(self):
        return self.fixed_value is not None

    def get_fixed_value(self) -> DecodedValue:
        return self.fixed_value

    def get_imputed_value(self) -> EncodedValue:
        return (self.bounds[0]+self.bounds[1])/2.

    def get_random_value(self) -> DecodedValue:
        return random.random()*(self.bounds[1]-self.bounds[0])+self.bounds[0]

    def iter_values(self, n_cont: int = 5) -> Generator[DecodedValue, None, None]:
        if n_cont <= 1:
            yield (self.bounds[0]+self.bounds[1])/2.
        else:
            values = np.linspace(self.bounds[0], self.bounds[1], n_cont)
            yield from values


class IntDesignVariableType(Enum):
    DISCRETE = 1
    CATEGORICAL = 2


@dataclass
class IntegerDesignVariable(DesignVariable):
    type: IntDesignVariableType
    values: list
    fixed_value: Any = None  # The fixed VALUE (should be in the values list!)

    def encode(self, value: DecodedValue) -> EncodedValue:
        try:
            return self.values.index(value)
        except ValueError:
            raise ValueError('Value %r not in values (des var %s): %r' % (value, self.values, self.name))

    def decode(self, value: EncodedValue) -> DecodedValue:
        try:
            if value < 0:
                raise IndexError
            return self.values[value]
        except IndexError:
            raise IndexError('Index %r out of range for value %r (des var %s)' % (value, self.values, self.name))

    @property
    def is_fixed(self):
        return self.fixed_value is not None

    def get_fixed_value(self) -> DecodedValue:
        if self.fixed_value not in self.values:
            raise ValueError('Fixed value (%r) not in available values (%s): %r' %
                             (self.fixed_value, self.name, self.values))
        return self.fixed_value

    def get_imputed_value(self) -> EncodedValue:
        return 0

    def get_random_value(self) -> DecodedValue:
        return random.choice(self.values)

    def iter_values(self, n_cont: int = 5) -> Generator[DecodedValue, None, None]:
        yield from self.values


@dataclass
class OutputMetric:
    name: str


class ObjectiveDirection(Enum):
    MINIMIZE = -1
    MAXIMIZE = 1


@dataclass
class Objective(OutputMetric):
    dir: ObjectiveDirection


class ConstraintDirection(Enum):
    LOWER_EQUAL_THAN = -1
    GREATER_EQUAL_THAN = 1


@dataclass
class Constraint(OutputMetric):
    dir: ConstraintDirection
    limit_value: float
