#!/usr/bin/python
# -*- coding: utf-8 -*-

import math
import os
import itertools
import numpy as np
import time
from collections import namedtuple
from ortools.linear_solver import pywraplp

Point = namedtuple("Point", ['x', 'y'])
Facility = namedtuple("Facility", ['index', 'setup_cost', 'capacity', 'location'])
Customer = namedtuple("Customer", ['index', 'demand', 'location'])

def length(point1, point2):
    return math.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)

def solve_it(input_data):
    # Modify this code to run your optimization algorithm

    # parse the input
    lines = input_data.split('\n')

    parts = lines[0].split()
    facility_count = int(parts[0])
    customer_count = int(parts[1])
    
    facilities = []
    for i in range(1, facility_count + 1):
        parts = lines[i].split()
        facilities.append(Facility(i - 1, float(parts[0]), int(parts[1]), Point(float(parts[2]), float(parts[3])) ))

    customers = []
    for i in range(facility_count + 1, facility_count + 1 + customer_count):
        parts = lines[i].split()
        customers.append(Customer(i - 1 - facility_count, int(parts[0]), Point(float(parts[1]), float(parts[2]))))

    # distance_matrix[i][j] is the distance between the i-th customer and the j-th facility.
    distance_matrix = [[((customer.location.x - facility.location.x) ** 2 + (customer.location.y - facility.location.y) ** 2) ** 0.5 \
                        for facility in facilities]  for customer in customers]


    # read initial solution generated by Guided Local Search.
    with open("cpp_output.txt", 'r') as assignment_init_file:
        assignment_init = assignment_init_file.read()
    assignment_init = assignment_init.split('\n')
    objective_init = float(assignment_init[0].split()[0])
    assignment_init = assignment_init[1].split()
    assignment_init = [int(index_str) for index_str in assignment_init]


    best_objective = objective_init
    best_assignment = assignment_init
    best_non_empty_facilities_set = set([assign for assign in best_assignment])
    best_non_empty_facilities = [facility for facility in best_non_empty_facilities_set]
    best_empty_facilities = [facility for facility in range(len(facilities)) if facility not in best_non_empty_facilities_set]
    best_facility_open = [0] * len(facilities)
    for index in best_assignment:
        best_facility_open[index] = 1
    best_output = None
    #-------------------------------------------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------------------------------------------


    # number of open facilities in the sub-problem
    n_non_empty_sub_facilities = 3

    # number of closed facilities in the sub-problem
    n_empty_sub_facilities = 10

    # number of facilities in the sub-problem
    n_sub_facilities = n_non_empty_sub_facilities + n_empty_sub_facilities

    round_limit = 10000000


    for round in range(round_limit):

        has_improvement = False

        while True:
        # for sub_facilities in itertools.combinations(range(len(facilities)), n_sub_facilities):

            start_time = time.time()

            # Randomly sample n_non_empty_sub_facilities facilities from open facilities
            sub_facilities_a = np.random.choice(best_non_empty_facilities, n_non_empty_sub_facilities, replace=False)

            # Randomly sample n_non_empty_sub_facilities facilities from closed facilities
            sub_facilities_b = np.random.choice(best_empty_facilities, n_empty_sub_facilities, replace=False)

            # merge the above two groups of facilities
            sub_facilities = np.append(sub_facilities_a, sub_facilities_b)

            sub_facilities_set = set(sub_facilities)

            # Select all customers that are served by the above facilities.
            sub_customers = [i for i in range(len(customers)) if best_assignment[i] in sub_facilities_set]

            objective_old = 0.0

            for customer in sub_customers:
                objective_old += distance_matrix[customer][best_assignment[customer]]

            for facility in sub_facilities:
                objective_old += best_facility_open[facility] * facilities[facility].setup_cost


            solver = pywraplp.Solver('SolveIntegerProblem', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)

            sub_assignment = [[solver.IntVar(0.0, 1.0, 'a' + str(i) + ',' + str(j)) for j in range(len(sub_facilities))]  for i in range(len(sub_customers))]

            sub_facility_open = [solver.IntVar(0.0, 1.0, 'f' + str(j)) for j in range(len(sub_facilities))]

            # Constraint: each customer must be assigned to exactly one facility.
            for i in range(len(sub_customers)):
                solver.Add(sum([sub_assignment[i][j] for j in range(len(sub_facilities))]) == 1)

            # Constraint: a customer must be assigned to an open facility.
            for i in range(len(sub_customers)):
                for j in range(len(sub_facilities)):
                    solver.Add(sub_assignment[i][j] <= sub_facility_open[j])

            # Constraint: the capacity of each facility must not be exceeded.
            for j in range(len(sub_facilities)):
                solver.Add(sum([sub_assignment[i][j] * customers[sub_customers[i]].demand \
                    for i in range(len(sub_customers))]) <= facilities[sub_facilities[j]].capacity)


            objective = solver.Objective()

            # Objective: sum all the distance.
            for i in range(len(sub_customers)):
                for j in range(len(sub_facilities)):
                    objective.SetCoefficient(sub_assignment[i][j], distance_matrix[sub_customers[i]][sub_facilities[j]])

            # Objective: sum all the setup cost.
            for j in range(len(sub_facilities)):
                objective.SetCoefficient(sub_facility_open[j], facilities[sub_facilities[j]].setup_cost)

            objective.SetMinimization()



            """Solve the problem and print the solution."""
            SEC = 1000
            MIN = 60 * SEC
            solver.SetTimeLimit(1 * MIN)
            result_status = solver.Solve()

            end_time = time.time()

            if result_status != solver.OPTIMAL and result_status != solver.FEASIBLE:
                
                print('[Round %9d/%9d] [N-Sub-Facilities %4d] [Best Objective %f] [Old Objective %f] [New Objective N/A] [Time %f]' % \
                    (round + 1, round_limit, n_sub_facilities, best_objective, objective_old, end_time - start_time))
                continue


            objective_new = solver.Objective().Value()
            assignment_new = []

            for i in range(len(sub_customers)):
                for j in range(len(sub_facilities)):
                    if sub_assignment[i][j].solution_value() == 1:
                        assignment_new.append(sub_facilities[j])
                        break

            print('[Round %9d/%9d] [N-Sub-Facilities %4d] [Best Objective %f] [Old Objective %f] [New Objective %f] [Time %f] %s' % \
                    (round + 1, round_limit, n_sub_facilities, best_objective, objective_old, objective_new, end_time - start_time, \
                    'best model found' if objective_old >= objective_new + 1 else ''))

            if objective_old >= objective_new + 1:
                best_objective -= objective_old - objective_new
                for i, j in enumerate(assignment_new):
                    best_assignment[sub_customers[i]] = j

                best_non_empty_facilities_set = set([assign for assign in best_assignment])
                best_non_empty_facilities = [facility for facility in best_non_empty_facilities_set]
                best_empty_facilities = [facility for facility in range(len(facilities)) if facility not in best_non_empty_facilities_set]

                best_facility_open = [0] * len(facilities)
                for index in best_assignment:
                    best_facility_open[index] = 1
                
                best_output = str(best_objective) + ' ' + '0' + '\n' + ' '.join([str(assign) for assign in best_assignment])
                with open("mip-output.txt", 'w') as best_mip_output_file:
                    best_mip_output_file.write(best_output)

                has_improvement = True

        if not has_improvement:
            n_sub_facilities += 1

    return best_output

import sys

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        file_location = sys.argv[1].strip()
        with open(file_location, 'r') as input_data_file:
            input_data = input_data_file.read()
        print(solve_it(input_data))
    else:
        print('This test requires an input file.  Please select one from the data directory. (i.e. python solver.py ./data/fl_16_2)')

