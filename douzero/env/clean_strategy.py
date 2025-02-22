import time
from concurrent.futures import ThreadPoolExecutor
from douzero.env.simulate_card import SimulateCard, Result, Action, calc_self_weight, calc_state_weight, triggerAttackHero, triggerRecoverHero
from douzero.env.recursion_attack import attackMinion, attackLocation, attackSpell
from douzero.env.clean_strategy_accurate_attack import accurate_attack

# Constants
MAX_INVERSION_CALC_COUNT = 100
CALC_THREAD_POOL = ThreadPoolExecutor(max_workers=8)
TAUNT_EXTRA_WEIGHT = 100

# Translated Methods
def calc_clean(my_cards, rival_cards):
    start = time.time()
    result = Result()
    recursion_calc_clean(my_cards, rival_cards, 0, [], result)
    elapsed_time = time.time() - start
    return result

def recursion_calc_clean(my_cards, rival_cards, my_index, actions, result):
    totalAlive = len([card for card in rival_cards if card.is_alive() and card.type == "MINION"])
    if my_index == len(my_cards) or totalAlive == 0:
        tauntAlive = len([card for card in rival_cards if card.is_alive() and card.is_taunt == True and card.type == "MINION" and \
                          card.is_stealth == False])
        minionAttackNonTaunt = len([action for action in actions if action.my_card.type == "MINION" and action.rival_card.is_taunt == False])
        if minionAttackNonTaunt > 0 and tauntAlive > 0:
            return
        else:
            # rivalHero = [card for card in rival_cards if card.type == "HERO"][0]
            # weight = calc_state_weight(my_cards, rival_cards)
            # result.set_new_result(rivalHero.blood, weight, actions, my_cards, rival_cards)
            real_result = accurate_attack(my_cards, rival_cards, actions)
            result.set_new_result(real_result.heroHP, real_result.all_weight, real_result.actions, real_result.my_cards, real_result.rival_cards)
            return

    minionAlive = [card for card in my_cards[my_index:] if card.type == "MINION" and card.isActive == True]
    rivalTauntHP = sum([card.blood for card in rival_cards if card.is_alive() and card.is_taunt])
    minionAttack = sum([card.atc for card in my_cards[my_index:] if card.type == "MINION" and card.isActive == True]) + \
        sum([card.atc for card in my_cards[my_index:] if card.cardId in ["NX2_019", "EX1_625t"] and card.isActive == True]) + \
        2 * len([card for card in my_cards[my_index:] if card.cardId == "REV_290" and card.isActive == True]) * (len(minionAlive) > 0)
    
    weight = calc_state_weight(my_cards, rival_cards)
    if minionAttack < rivalTauntHP and weight < result.all_weight: # todo
        return;

    my_card = my_cards[my_index]

    recursion_calc_clean(my_cards, rival_cards, my_index + 1, actions, result)

    if my_card.isActive == True:
        if my_card.type == "MINION":
            for rival_card in rival_cards: # TODO MYWEN debuff
                if rival_card.is_alive() and rival_card.can_be_attacked() == True and rival_card.type != "HERO":
                    attackMinion(my_cards, rival_cards, my_index, actions, result, my_card, rival_card, recursion_calc_clean)
        elif my_card.type == "LOCATION":
            for target_card in my_cards:
                if target_card.type == "MINION" and target_card.is_alive() and target_card.can_be_targeted_by_me() == True:
                    attackLocation(my_cards, rival_cards, my_index, actions, result, my_card, target_card, recursion_calc_clean)
        elif my_card.type == "SPELL" or my_card.type == "HERO_POWER":
            for rival_card in rival_cards: # TODO MYWEN debuff
                if rival_card.type == "MINION" and rival_card.is_alive() and rival_card.can_be_attacked() == True and rival_card.is_immunity_magic() == False  and rival_card.type != "HERO":
                    attackSpell(my_cards, rival_cards, my_index, actions, result, my_card, rival_card, recursion_calc_clean)

    