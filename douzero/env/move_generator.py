from douzero.env.utils import MIN_SINGLE_CARDS, MIN_PAIRS, MIN_TRIPLES, select
import collections
from itertools import combinations

class MovesGener(object):
    """
    This is for generating the possible combinations
    """
    def __init__(self, cards_list, Cardset):
        self.cards_list = [] + cards_list
        self.CardSet = Cardset

    # generate all possible moves from given cards
    def gen_moves(self):
        all_combinations = []
        for r in range(0, len(self.cards_list) + 1):
            actions_list = [list(tup) for tup in combinations(self.cards_list, r)]
            all_combinations.extend(actions_list)
            all_combinations.extend([action + [31] for action in actions_list]) # 心灵尖刺
        return all_combinations
