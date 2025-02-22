from concurrent.futures import ThreadPoolExecutor
from douzero.env.simulate_card import SimulateCard, KOResult, Action, calc_self_weight, calc_state_weight, triggerAttackHero, triggerRecoverHero

def attackNone(my_cards, rival_cards, my_index, actions, result, my_card, rival_card, recursion_calc_clean):
    assert my_card.type in ["SPELL", "MINION"]
    assert my_card.cardId in ["VAC_419", "DS1_233", "GVG_009"] or my_card.name in ["暗影投弹手"]
    assert rival_card == None
    rival_card = [card for card in rival_cards if card.type == "HERO"][0]
    rival_divine_shield = rival_card.is_divine_shield

    index = len(actions)

    if rival_divine_shield:
        rival_card.is_divine_shield = False
    elif my_card.is_poisonous and rival_card.type == "MINION":
        rival_card.blood = -rival_card.blood
    else:
        if my_card.type == "SPELL":
            rival_card.blood -= my_card.atc
        elif my_card.name == "暗影投弹手":
            rival_card.blood -= 3

    death_card = None if rival_card.is_alive() else rival_card
    actions.append(Action(death_card, my_card, None, rival_card.debuff))  # Replace `lambda` with the actual action

    recursion_calc_clean(my_cards, rival_cards, my_index + 1, actions, result)

    # Revert changes after recursion
    if rival_divine_shield:
        rival_card.is_divine_shield = True
    elif my_card.is_poisonous and rival_card.type == "MINION":
        rival_card.blood = -rival_card.blood
    else:
        if my_card.type == "SPELL":
            rival_card.blood += my_card.atc
        elif my_card.name == "暗影投弹手":
            rival_card.blood += 3

    actions.pop(index)

def attackMinion(my_cards, rival_cards, my_index, actions, result, my_card, rival_card, recursion_calc_clean):
    assert my_card.type == "MINION"
    assert rival_card.type == "MINION" or rival_card.type == "HERO"
    my_divine_shield = my_card.is_divine_shield
    rival_divine_shield = rival_card.is_divine_shield

    index = len(actions)

    if my_card.is_immune_while_attacking or my_card.is_immune:
        pass
    elif my_divine_shield:
        if rival_card.atc > 0:
            my_card.is_divine_shield = False
    elif rival_card.is_poisonous:
        my_card.blood = -my_card.blood
    else:
        my_card.blood -= rival_card.atc

    if rival_divine_shield:
        rival_card.is_divine_shield = False
    elif my_card.is_poisonous and rival_card.type == "MINION":
        rival_card.blood = -rival_card.blood
    else:
        rival_card.blood -= my_card.atc

    my_card_alive = my_card.is_alive()
    rival_card_alive = rival_card.is_alive()
    rivalHero = [card for card in rival_cards if card.type == "HERO"][0]
    # if not my_card_alive and my_card.cardId == "SW_446":
    #     rivalHero.debuff -= 1
    # if not rival_card_alive and rival_card.cardId == "SW_446":
    #     rivalHero.debuff -= 1

    if rival_card.is_vampire == True:
        rivalHero.bloodPlus(rival_card.atc)

    triggerAttackHeroByVAC512 = True if rival_card.cardId == "VAC_512" and rival_card.entityId in [card.entityId for card in rival_cards] else False
    triggerAttackHeroByNX2_019 = False
    rival_hero_divine_shield = rivalHero.is_divine_shield
    triggerAttackHero(my_card, rivalHero, triggerAttackHeroByVAC512, triggerAttackHeroByNX2_019, rival_hero_divine_shield)
    death_card = None if rival_card.is_alive() else rival_card
    actions.append(Action(death_card, my_card, rival_card, rivalHero.debuff))  # Replace `lambda` with the actual action

    recursion_calc_clean(my_cards, rival_cards, my_index + 1, actions, result)

    triggerRecoverHero(my_card, rivalHero, triggerAttackHeroByVAC512, triggerAttackHeroByNX2_019, rival_hero_divine_shield)

    if rival_card.is_vampire == True:
        rivalHero.bloodPlus(-rival_card.atc)

    # Revert changes after recursion
    if my_card.is_immune_while_attacking or my_card.is_immune:
        pass
    elif my_divine_shield:
        my_card.is_divine_shield = True
    elif rival_card.is_poisonous:
        my_card.blood = -my_card.blood
    else:
        my_card.blood += rival_card.atc

    if rival_divine_shield:
        rival_card.is_divine_shield = True
    elif my_card.is_poisonous and rival_card.type == "MINION":
        rival_card.blood = -rival_card.blood
    else:
        rival_card.blood += my_card.atc

    # if not my_card_alive and my_card.cardId == "SW_446":
    #     rivalHero.debuff += 1
    # if not rival_card_alive and rival_card.cardId == "SW_446":
    #     rivalHero.debuff += 1

    actions.pop(index)

def attackLocation(my_cards, rival_cards, my_index, actions, result, my_card, minion_card, recursion_calc_clean):
    assert my_card.type == "LOCATION"
    assert minion_card.type == "MINION"
    index = len(actions)

    my_card.blood -= 1
    minion_card.blood += 1
    minion_card.atc += 2

    actions.append(Action(None, my_card, minion_card, 0))  # Replace `lambda` with the actual action

    recursion_calc_clean(my_cards, rival_cards, my_index + 1, actions, result)

    my_card.blood += 1
    minion_card.blood -= 1
    minion_card.atc -= 2

    actions.pop(index)

def attackSpell(my_cards, rival_cards, my_index, actions, result, my_card, rival_card, recursion_calc_clean):
    assert my_card.type == "SPELL" or my_card.type == "HERO_POWER"
    assert rival_card.type == "MINION" or rival_card.type == "HERO"
    rival_divine_shield = rival_card.is_divine_shield

    index = len(actions)

    my_card.blood -= 1
    if rival_divine_shield:
        rival_card.is_divine_shield = False
    else:
        rival_card.blood -= my_card.atc
    rival_card_alive = rival_card.is_alive()
    rivalHeroCard = [card for card in rival_cards if card.type == "HERO"][0]
    # if not rival_card_alive and rival_card.cardId == "SW_446":
    #     rivalHeroCard.debuff -= 1

    triggerAttackHeroByVAC512 = True if rival_card.cardId == "VAC_512" and rival_card.entityId in [card.entityId for card in rival_cards] else False
    triggerAttackHeroByNX2_019 = True if my_card.cardId == "NX2_019" else False

    rival_hero_divine_shield = rivalHeroCard.is_divine_shield

    triggerAttackHero(my_card, rivalHeroCard, triggerAttackHeroByVAC512, triggerAttackHeroByNX2_019, rival_hero_divine_shield)

    death_card = None if rival_card.is_alive() else rival_card
    actions.append(Action(death_card, my_card, rival_card, rivalHeroCard.debuff))  # Replace `lambda` with the actual action

    recursion_calc_clean(my_cards, rival_cards, my_index + 1, actions, result)

    # trigger Hero
    triggerRecoverHero(my_card, rivalHeroCard, triggerAttackHeroByVAC512, triggerAttackHeroByNX2_019, rival_hero_divine_shield)
    # if not rival_card_alive and rival_card.cardId == "SW_446":
    #     rivalHeroCard.debuff += 1

    # Revert changes after recursion
    my_card.blood += 1
    if rival_divine_shield:
        rival_card.is_divine_shield = True
    else:
        rival_card.blood += my_card.atc

    actions.pop(index)