import time
from concurrent.futures import ThreadPoolExecutor
from douzero.env.simulate_card import SimulateCard, Result, Action, calc_self_weight, calc_state_weight, triggerAttackHero, triggerRecoverHero
from douzero.env.ko_strategy_accurate_attack import accurate_attack
from itertools import permutations
from douzero.env.accurate_attack import checkValid, attackNone, attackMinion, attackLocation, attackSpell

# Constants
MAX_INVERSION_CALC_COUNT = 100
CALC_THREAD_POOL = ThreadPoolExecutor(max_workers=8)
TAUNT_EXTRA_WEIGHT = 100

# Translated Methods

def accurate_attack(current_my_cards, current_rival_cards, current_actions):
    assert len([card for card in current_rival_cards if card.type == "HERO"]) > 0

    actionTypeToActions = {}
    current_my_cards_in_hand = [cardDetails.entityId for cardDetails in current_my_cards if cardDetails.area == "HandArea"]
    locationBuffHandCard = False
    for action in current_actions:
        my_card = action.my_card
        rival_card = action.rival_card
        entityId = rival_card.entityId if rival_card != None else None
        if my_card.type == "LOCATION" and entityId in current_my_cards_in_hand and rival_card.name == "暗影投弹手":
            locationBuffHandCard = True
        actionType = ""
        if my_card.type == "HERO_POWER":
            actionType += "SPELL"
        else:
            actionType += my_card.type
        
        if rival_card == None:
            pass
        elif rival_card.type == "MINION":
            actionType += "_ATC_"
            actionType += "MINION" + ("TAUNT" if rival_card.is_taunt else "")
        else:
            actionType += "_ATC_"
            actionType += rival_card.type

        if actionType not in actionTypeToActions:
            actionTypeToActions[actionType] = {}
            actionTypeToActions[actionType][entityId] = []
        elif entityId not in actionTypeToActions[actionType]:
            actionTypeToActions[actionType][entityId] = []
        
        actionTypeToActions[actionType][entityId].extend([action])

    SW_446_Count = len([cardDetails for cardDetails in current_my_cards if cardDetails.cardId == "SW_446"]) # 虚触侍从
    SW_446_Count += len([cardDetails for cardDetails in current_rival_cards if cardDetails.cardId == "SW_446"]) # 虚触侍从
    result = Result()
    for permutation in permutations(actionTypeToActions):
        if checkValid(permutation, locationBuffHandCard) == False:
            continue
        my_cards = [SimulateCard(card.cardDetails) for card in current_my_cards]
        rival_cards = [SimulateCard(card.cardDetails) for card in current_rival_cards]
        entityIdToCards = {card.entityId: card for card in my_cards + rival_cards}
        rival_hero = [card for card in rival_cards if card.type == "HERO"][0]
        rival_hero.debuff = SW_446_Count
        actions = []
        for action in [action for actionType in permutation \
                    for entitiId in actionTypeToActions[actionType].keys() \
                        for action in actionTypeToActions[actionType][entitiId]]:
            my_card = entityIdToCards[action.my_card.entityId] if action.my_card != None else None
            rival_card = entityIdToCards[action.rival_card.entityId] if action.rival_card != None else None
            totalAlive = len([card for card in rival_cards if card.is_alive() and card.type == "MINION"])
            if totalAlive <= 0:
                break
            if rival_card != None and rival_card.type == "HERO":
                break
            if my_card.type == "MINION":
                attackMinion(my_cards, rival_cards, actions, my_card, rival_card)
            elif my_card.type == "LOCATION":
                attackLocation(my_cards, rival_cards, actions, my_card, rival_card)
            elif my_card.type == "SPELL" or my_card.type == "HERO_POWER":
                attackSpell(my_cards, rival_cards, actions, my_card, rival_card)

        tauntAlive = len([card for card in rival_cards if card.is_alive() and card.is_taunt == True and card.type == "MINION" \
                          and card.is_stealth == False])
        minionAttackNonTaunt = len([action for action in actions if action.my_card.type == "MINION" and action.rival_card.is_taunt == False]) # include rival minion and hero
        if minionAttackNonTaunt > 0 and tauntAlive > 0:
            continue
        weight = calc_state_weight(my_cards, rival_cards)
        result.set_new_result(rival_hero.blood, weight, actions, my_cards, rival_cards)

    return result