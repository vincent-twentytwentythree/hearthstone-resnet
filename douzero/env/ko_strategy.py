import time
from concurrent.futures import ThreadPoolExecutor
from douzero.env.simulate_card import SimulateCard, KOResult, Action, calc_self_weight, calc_state_weight, triggerAttackHero, triggerRecoverHero
from douzero.env.ko_strategy_accurate_attack import accurate_attack
from douzero.env.recursion_attack import attackNone, attackMinion, attackLocation, attackSpell

# Constants
MAX_INVERSION_CALC_COUNT = 100
CALC_THREAD_POOL = ThreadPoolExecutor(max_workers=8)
TAUNT_EXTRA_WEIGHT = 100

# Translated Methods

def calc_clean(my_cards, rival_cards):
    assert len([card for card in rival_cards if card.type == "HERO"]) > 0
    start = time.time()
    result = KOResult()
    # print (len(my_cards))
    # print (my_cards)
    recursion_calc_clean(my_cards, rival_cards, 0, [], result)
    elapsed_time = time.time() - start
    return result

# mode: UPPER-ATTACK means all buff must work, ACCURATE-ATTACK means will minion died the buff will disappear
def recursion_calc_clean(my_cards, rival_cards, my_index, actions, result):
    if  result.heroHP <= 0: # 已经找到一个解
        return;
    rivalHero = [card for card in rival_cards if card.type == "HERO"][0]
    # if len(actions) > 5 and actions[0].my_card.cardId == "REV_290" and actions[0].rival_card.entityId == "32" \
    #     and actions[1].rival_card != None and actions[1].rival_card.cardId == "GDB_320" \
    #         and actions[2].rival_card != None and actions[2].rival_card.cardId == "GDB_320" \
    #             and actions[3].rival_card != None and actions[3].rival_card.cardId == "HERO_09" \
    #             and (actions[4].rival_card == None or actions[4].rival_card.cardId == "HERO_09") \
    #                 and actions[5].rival_card != None and actions[5].rival_card.cardId == "HERO_09":
    #                     print ("DEBUG", my_index, rivalHero.blood, rivalHero.debuff)
    #                     for koact in actions:
    #                         print (koact.my_card, koact.rival_card, koact.death_card)
    # if len(actions) > 5 and rivalHero.blood <= 10 and actions[0].my_card.cardId == "REV_290" and actions[0].rival_card.entityId == "32" \
    #     and actions[1].rival_card != None and actions[1].rival_card.cardId == "GDB_320" \
    #         and actions[2].rival_card != None and actions[2].rival_card.cardId == "GDB_320":
    #     print ("DEBUG", my_index, rivalHero.blood, rivalHero.debuff)
    #     for koact in actions:
    #         print (koact.my_card, koact.rival_card, koact.death_card)
    if my_index == len(my_cards) or not rivalHero.is_alive():
        tauntAlive = len([card for card in rival_cards if card.is_alive() and card.is_taunt == True and card.type == "MINION" \
                          and card.is_stealth == False])
        minionAttackNonTaunt = len([action for action in actions if action.my_card.type == "MINION" and action.rival_card != None and action.rival_card.is_taunt == False]) # include rival minion and hero
        if minionAttackNonTaunt > 0 and tauntAlive > 0:
            return
        else:
            # weight = calc_state_weight(my_cards, rival_cards)
            # result.set_new_result(rivalHero.blood, weight, actions, my_cards, rival_cards)
            real_result = accurate_attack(my_cards, rival_cards, actions)
            result.set_new_result(real_result.heroHP, real_result.all_weight, real_result.actions, real_result.my_cards, real_result.rival_cards)
            return

    minionAlive = [card for card in my_cards[my_index:] if card.type == "MINION" and card.isActive == True]
    rivalTauntHP = sum([card.blood for card in rival_cards if card.is_alive() and card.is_taunt])
    rivalTauntCount = len([card.blood for card in rival_cards if card.is_alive() and card.is_taunt])

    minionAttack = sum([card.atc for card in my_cards[my_index:] if card.type == "MINION" and card.isActive == True]) + \
        2 * len([card for card in my_cards[my_index:] if card.cardId == "REV_290" and card.isActive == True]) * (len(minionAlive) > 0)

    spellAttack = sum([card.atc for card in my_cards[my_index:] if card.cardId in ["NX2_019", "EX1_625t"] and card.isActive == True and card.area == "HandArea"])

    attackTauntCount = len([card.atc for card in my_cards[my_index:] if card.type == "MINION" and card.isActive == True] + \
                      [card.atc for card in my_cards[my_index:] if card.cardId in ["NX2_019", "EX1_625t"] and card.isActive == True and card.area == "HandArea"])

    minionAttackNonTaunt = len([action for action in actions if action.my_card.type == "MINION" and action.rival_card != None and action.rival_card.is_taunt == False]) # include rival minion and hero
    if (minionAttack + spellAttack < rivalTauntHP or attackTauntCount < rivalTauntCount) and minionAttackNonTaunt > 0:
        return

    sumAttack = 0
    rivalTauntHP = max(rivalTauntHP - spellAttack, 0)
    sumAttack += max(minionAttack - rivalTauntHP, 0) # 随从剩余攻击力

    for card in my_cards[my_index:]:
        if card.cardId == "NX2_019":
            sumAttack += 3 + rivalHero.debuff
        # elif card.cardId == "REV_290" and card.isActive == True:
        #     sumAttack += 2 if len(minionAlive) > 0 else 0
        # elif card.type == "MINION" and card.isActive == True:
        #     sumAttack += card.atc + rivalHero.debuff
        # elif card.type == "SPELL" or card.type == "HERO_POWER":
        #     sumAttack += card.atc + rivalHero.debuff
        elif card.type == "MINION" and card.isActive == True:
            sumAttack += rivalHero.debuff
        elif card.type == "HERO_POWER":
            sumAttack += 2 + rivalHero.debuff
        elif card.type == "SPELL" and card.atc > 0:
            sumAttack += card.atc + rivalHero.debuff
        elif card.name == "暗影投弹手" and card.isActive == False and card.area == "HandArea":
            sumAttack += card.atc + rivalHero.debuff
    # weight = calc_state_weight(my_cards, rival_cards)
    # if rivalHero.blood - sumAttack > result.heroHP or (rivalHero.blood - sumAttack == result.heroHP and weight < result.all_weight): # todo
    # if rivalHero.blood - sumAttack > result.heroHP:
    #     return;
    # print ("DEBUG", minionAttack - rivalTauntHP, rivalHero.blood - sumAttack, result.heroHP)
    if rivalHero.blood - sumAttack > result.heroHP:
        return;
    if rivalHero.blood - sumAttack == result.heroHP and sumAttack == 0:
        tauntAlive = len([card for card in rival_cards if card.is_alive() and card.is_taunt == True and card.type == "MINION" \
                          and card.is_stealth == False])
        minionAttackNonTaunt = len([action for action in actions if action.my_card.type == "MINION" and action.rival_card != None and action.rival_card.is_taunt == False]) # include rival minion and hero
        if minionAttackNonTaunt > 0 and tauntAlive > 0:
            return
        else:
            # weight = calc_state_weight(my_cards, rival_cards)
            # result.set_new_result(rivalHero.blood, weight, actions, my_cards, rival_cards)
            real_result = accurate_attack(my_cards, rival_cards, actions)
            result.set_new_result(real_result.heroHP, real_result.all_weight, real_result.actions, real_result.my_cards, real_result.rival_cards)
            return
    my_card = my_cards[my_index]
    if my_card.name == "暗影投弹手" and my_card.isActive == False and my_card.area == "HandArea":
        attackNone(my_cards, rival_cards, my_index, actions, result, my_card, None, recursion_calc_clean)
    elif my_card.cardId in ["VAC_419", "DS1_233"] and my_card.isActive == True:
        attackNone(my_cards, rival_cards, my_index, actions, result, my_card, None, recursion_calc_clean)
    else:
        if my_card.isActive == True:
            if my_card.type == "LOCATION":
                for target_card in my_cards:
                    if target_card.type == "MINION" and target_card.is_alive() and target_card.can_be_targeted_by_me() == True:
                        attackLocation(my_cards, rival_cards, my_index, actions, result, my_card, target_card, recursion_calc_clean)
        recursion_calc_clean(my_cards, rival_cards, my_index + 1, actions, result)
        if my_card.isActive == True:
            if my_card.type == "MINION":
                for rival_card in rival_cards: # TODO MYWEN debuff
                    if rival_card.is_alive() and rival_card.can_be_attacked() == True:
                        attackMinion(my_cards, rival_cards, my_index, actions, result, my_card, rival_card, recursion_calc_clean)
            elif my_card.type == "SPELL" or my_card.type == "HERO_POWER":
                for rival_card in rival_cards: # TODO MYWEN debuff
                    if rival_card.type == "MINION" and rival_card.is_alive() and rival_card.can_be_attacked() == True and rival_card.is_immunity_magic() == False:
                        if my_card.cardId in ["NX2_019", "EX1_625t"]:
                            attackSpell(my_cards, rival_cards, my_index, actions, result, my_card, rival_card, recursion_calc_clean)
                    if rival_card.type == "HERO" and rival_card.is_alive() and rival_card.can_be_attacked() == True and rival_card.is_immunity_magic() == False:
                        if my_card.cardId in ["EX1_625t"]:
                            attackSpell(my_cards, rival_cards, my_index, actions, result, my_card, rival_card, recursion_calc_clean)
                for target_card in my_cards: # TODO MYWEN debuff
                    if target_card.type == "MINION" and target_card.is_alive() and rival_card.can_be_targeted_by_me() == True and rival_card.is_immunity_magic() == False:
                        if my_card.cardId in ["NX2_019", "EX1_625t"]: # hit me hero 
                            attackSpell(my_cards, rival_cards, my_index, actions, result, my_card, target_card, recursion_calc_clean)