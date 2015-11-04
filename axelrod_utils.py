from __future__ import division
import axelrod


def mean(data):
    """Return the sample arithmetic mean of data."""
    n = len(data)
    if n < 1:
        raise ValueError('mean requires at least one data point')
    return sum(data) / n  # in Python 2 use sum(data)/float(n)


def _ss(data):
    """Return sum of square deviations of sequence data."""
    c = mean(data)
    ss = sum((x - c)**2 for x in data)
    return ss


def pstdev(data):
    """Calculates the population standard deviation."""
    n = len(data)
    if n < 2:
        raise ValueError('variance requires at least two data points')
    ss = _ss(data)
    pvar = ss / n  # the population variance
    return pvar**0.5


def score_single(me, other, iterations=200):
    """
    Return the average score per turn for a player in a single match against
    an opponent.
     """
    g = axelrod.Game()
    for _ in range(iterations):
        me.play(other)
    return sum([g.score(pair)[0] for pair in zip(me.history, other.history)]) / iterations


def score_for(my_strategy_factory, iterations=200):
    """
    Given a function that will return a strategy, calculate the average score per turn
    against all ordinary strategies. If the opponent is classified as stochastic, then 
    run 100 repetitions and take the average to get a good estimate. 
    """
    scores_for_all_opponents = []
    for opponent in axelrod.ordinary_strategies:
        if opponent.classifier['stochastic']:
            repetitions = 100
        else:
            repetitions = 1
        scores_for_this_opponent = []
        for _ in range(repetitions):
            me = my_strategy_factory()
            other = opponent()
            # make sure that both players know what length the match will be 
            me.set_tournament_attributes(length=iterations)
            other.set_tournament_attributes(length=iterations)
            scores_for_this_opponent.append(score_single(me, other, iterations))

        average_score_vs_opponent = sum(scores_for_this_opponent) / len(scores_for_this_opponent)
        scores_for_all_opponents.append(average_score_vs_opponent)
    overall_average_score = sum(scores_for_all_opponents) / len(scores_for_all_opponents)
    return(overall_average_score)


def id_for_table(table):
    """Return a string representing the values of a lookup table dict"""
    return ''.join([v for k, v in sorted(table.items())])


def do_table(table):
    """
    Take a lookup table dict, construct a lambda factory for it, and return
    a tuple of the score and the table itself
    """
    fac = lambda: axelrod.LookerUp(lookup_table=table)
    return(score_for(fac), table)


def score_tables(tables, pool):
    """Use a multiprocessing Pool to take a bunch of tables and score them"""
    return sorted(pool.map(do_table, tables), reverse=True)


