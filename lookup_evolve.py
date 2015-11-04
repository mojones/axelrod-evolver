"""Lookup Evolve.

Usage:
    lookup_evolve.py [-h] [-p PLIES] [-s STARTING_PLIES] [-g GENERATIONS] [-k STARTING_POPULATION] [-u MUTATION_RATE] [-b BOTTLENECK] [-i PROCESSORS] [-o OUTPUT_FILE]

Options:
    -h --help               show this
    -p PLIES                specify the number of recent plays in the lookup table [default: 2]
    -s STARTING_PLIES       specify the number of opponent starting plays in the lookup table [default: 2]
    -g GENERATIONS          how many generations to run the program for [default: 100]
    -k STARTING_POPULATION  starting population for the simulation [default: 5]
    -u MUTATION_RATE        mutation rate i.e. probability that a given value will flip [default: 0.1]
    -b BOTTLENECK           number of individuals to keep from each generation [default: 10]
    -i PROCESSORS           number of processors to use [default: 1]
    -o OUTPUT_FILE          file to write statistics to [default: evolve.csv]


"""
from __future__ import division
from docopt import docopt
import itertools
import random
import copy
from multiprocessing import Pool

import axelrod_utils

def evolve(starting_tables, mutation_rate, generations, bottleneck, pool, plys, start_plys, starting_pop, output_file):
    """
    The function that does everything. Take a set of starting tables, and in each generation:
    - add a bunch more random tables
    - simulate recombination between each pair of tables 
    - randomly mutate the current population of tables
    - calculate the fitness function i.e. the average score per turn
    - keep the best individuals and discard the rest
    - write out summary statistics to the output file

    """

    # current_bests is a list of 2-tuples, each of which consists of a score and a lookup table
    # initially the collection of best tables are the ones supplied to start with
    current_bests = starting_tables

    for generation in range(generations):

        # because this is a long-running process we'll just keep appending to the output file
        # so we can monitor it while it's running
        with open(output_file, "a") as output:
            print("doing generation " + str(generation))

            # the tables at the start of this generation are the best ones from the
            # previous generation (i.e. the second element of each tuple) plus a bunch
            # of random ones
            tables_to_copy = [x[1] for x in current_bests] + get_random_tables(plys, start_plys, starting_pop)

            # set up new list to hold the tables that we are going to want to score
            copies = []

            # each table reproduces with each other table to produce one offspring
            for t1 in tables_to_copy:
                for t2 in tables_to_copy:

                    # for reproduction, pick a random crossover point
                    crossover = random.randrange(len(t1.items()))

                    # the values (plays) for the offspring are copied from t1 up to the crossover point, 
                    # and from t2 from the crossover point to the end
                    new_values = copy.deepcopy(t1.values()[0:crossover]) + copy.deepcopy(t2.values()[crossover:])

                    # turn those new values into a valid lookup table by copying the keys from t1 (the keys are the same for
                    # all tables, so it doesn't matter which one we pick)
                    new_table = dict(zip(copy.deepcopy(t1.keys()), new_values))
                    copies.append(new_table)

            # now copies contains a list of the new offspring tables, do mutation
            for c in copies:
                # flip each value with a probability proportional to the mutation rate
                for history, move in c.items():
                    if random.random() < mutation_rate:
                        c[history] = 'C' if move == 'D' else 'D'

            # the population of tables we want to consider includes the recombined, mutated copies, plus the originals
            population  = copies + tables_to_copy

            # map the population to get a list of (score, table) tuples
            # this list will be sorted by score, best tables first
            results = axelrod_utils.score_tables(population, pool)

            # keep the user informed
            print("generation " + str(generation))

            # the best tables from this generation become the starting tables for the next generation
            current_bests = results[0:bottleneck]

            # get all the scores for this generation
            scores = [score for score, table in results]

            # write the generation number, identifier of current best table, score of current best table, mean score, and SD of scores to the output file
            for value in [generation, axelrod_utils.id_for_table(results[0][1]), results[0][0], axelrod_utils.mean(scores), axelrod_utils.pstdev(scores)]:
                output.write(str(value) + ",")
            output.write("\n")

    return (current_bests)


def get_random_tables(plys, opponent_start_plys, number):
    """Return randomly-generated lookup tables"""

    # generate all the possible recent histories for the player and opponent
    player_histories = [''.join(x) for x in itertools.product('CD', repeat=plys)]
    opponent_histories = [''.join(x) for x in itertools.product('CD', repeat=plys)]

    # also generate all the possible opponent starting plays
    opponent_starts = [''.join(x) for x in itertools.product('CD', repeat=opponent_start_plys)]

    # the list of keys for the lookup table is just the product of these three lists
    lookup_table_keys = list(itertools.product(opponent_starts,player_histories, opponent_histories))

    # to get a pattern, we just randomly pick between C and D for each key
    patterns = [''.join([random.choice("CD") for _ in lookup_table_keys]) for i in range(number)]

    # zip together the keys and the patterns to give a table
    tables = [dict(zip(lookup_table_keys, pattern)) for pattern in patterns]

    return tables

if __name__ == '__main__':
    arguments = docopt(__doc__, version='Lookup Evolver 0.1')

    # set up the process pool 
    pool = Pool(processes=int(arguments['-i'])) 

    # vars for the genetic algorithm
    starting_pop = int(arguments['-k'])
    mutation_rate = float(arguments['-u'])
    generations = int(arguments['-g'])
    bottleneck = int(arguments['-b'])
    plys = int(arguments['-p'])
    start_plys = int(arguments['-s'])

    # generate a starting population of tables and score them
    # these will start off the first generation
    starting_tables = get_random_tables(plys, start_plys, starting_pop)
    real_starting_tables = axelrod_utils.score_tables(starting_tables, pool)

    # kick off the evolve function
    evolve(real_starting_tables, mutation_rate, generations, bottleneck, pool, plys, start_plys, starting_pop, arguments['-o'])
