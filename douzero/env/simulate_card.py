import copy

HERO_EXTRA_WEIGHT = 1_000_000
TAUNT_EXTRA_WEIGHT = HERO_EXTRA_WEIGHT << 1
DIVINE_SHIELD_WEIGHT = 0.3
HERO_BLOOD_WEIGHT = 20

class SimulateCard:
    # Constants


    def __init__(
        self,
        cardDetails,
    ):
        self.cardDetails = cardDetails
        self.atc_weight = 1.2
        self.card_weight = cardDetails.get("card_weight", 1.0)
        self.isActive = cardDetails.get("isActive", False)
        self.debuff = cardDetails.get("debuff", 0)
        self.atc = cardDetails["attack"]
        self._blood = cardDetails["hp"]
        self.type = cardDetails["type"]
        self.cardId = cardDetails["cardId"]
        self.entityId = cardDetails["entityId"]
        if "area" not in cardDetails:
            print (cardDetails)
        self.area = cardDetails["area"]
        self.name = cardDetails["name"]

        self.is_divine_shield = cardDetails["card"].get("isDivineShield", False)
        self.is_immune_while_attacking = cardDetails["card"].get("isImmuneWhileAttacking", False)
        self.is_immune = cardDetails["card"].get("isImmune", False)
        self.is_poisonous = cardDetails["card"].get("isPoisonous", False)
        self.is_taunt = cardDetails["card"].get("isTaunt", False)
        self.is_vampire = cardDetails["card"].get("isLifesteal", False)
        self.is_elusive = cardDetails["card"].get("isElusive", False)
        self.is_cant_be_targeted_by_spells = cardDetails["card"].get("isCantBeTargetedBySpells", False)
        self.is_stealth = cardDetails["card"].get("isStealth", False)
        self.is_dormant_awaken_condition_enchant = cardDetails["card"].get("isDormantAwakenConditionEnchant", False)
        self.is_untouchable = cardDetails["card"].get("isUntouchable", False)
        self.is_exhausted = cardDetails["card"].get("isExhausted", False)
        self.is_cant_attack = cardDetails["card"].get("isCantAttack", False)
        self.is_frozen = cardDetails["card"].get("isFrozen", False)
        self.is_cant_be_targeted_by_hero_powers = cardDetails["card"].get("isCantBeTargetedByHeroPowers", False)

        # Derived weights
        self.calc_blood_weight = self.blood * self.card_weight
        self.calc_weight = (
            self.atc_weight * max(0, self.atc) * self.card_weight
        )

    def can_be_targeted_by_rival_spells(self):
        return not (self.is_elusive or self.is_cant_be_targeted_by_spells or not self.can_be_targeted_by_rival())

    def can_be_targeted_by_my_spells(self):
        return not (self.is_elusive or self.is_cant_be_targeted_by_spells or not self.can_be_targeted_by_me())

    def can_be_targeted_by_rival_hero_powers(self):
        return self.can_be_targeted_by_rival_spells()

    def can_be_targeted_by_my_hero_powers(self):
        return self.can_be_targeted_by_my_spells()

    def can_be_targeted_by_rival(self):
        return not (self.is_stealth or self.is_immune or self.is_dormant_awaken_condition_enchant or self.is_untouchable)

    def can_be_targeted_by_me(self):
        return not (self.is_immune or self.is_dormant_awaken_condition_enchant or self.is_untouchable)

    def can_be_attacked(self):
        return (self.type in ["MINION", "HERO"]) and self.can_be_targeted_by_rival()

    def can_attack(self, ignore_exhausted=False):
        return (self.type in ["MINION", "HERO"] and
                not ((self.is_exhausted and not ignore_exhausted) or 
                     self.is_cant_attack or self.is_frozen or 
                     self.is_dormant_awaken_condition_enchant or self.atc <= 0))

    def is_immunity_magic(self):
        return (self.is_cant_be_targeted_by_spells and self.is_cant_be_targeted_by_hero_powers) or self.is_elusive

    def __deepcopy__(self, memo):
        # Create a new instance of the class
        new_obj = SimulateCard(self.cardDetails)
        new_obj._blood = self._blood
        new_obj.atc = self.atc
        new_obj.debuff = self.debuff

        # Add the new object to the memo dictionary to handle recursion
        memo[id(self)] = new_obj
        return new_obj

    @property
    def blood(self):
        return self._blood

    @blood.setter
    def blood(self, value):
        if self.is_immune:
            # print (self.type, self._blood, value)
            return
        if value < self._blood:
            value -= self.debuff # 受到攻击
            self._blood = value
            self.calc_blood_weight = value * self.card_weight
        if value > self._blood:
            value += self.debuff # 撤回攻击
            self._blood = value
            self.calc_blood_weight = value * self.card_weight
    
    def bloodPlus(self, value):
        self._blood += value

    def is_alive(self):
        return self.blood > 0

    def calc_self_weight(self):
        if self.blood <= 0:
            return 0.0
        if self.type == "MINION":
            return (
                self.calc_weight
                + self.calc_blood_weight
                + (
                    self.atc * DIVINE_SHIELD_WEIGHT
                    if self.is_divine_shield
                    else 0.0
                )
            )
        elif self.type == "LOCATION":
            return 1
        elif self.type == "SPELL":
            if self.cardId == "EX1_625t":
                return 1
            else :
                return 0
        elif self.type == "HERO":
            return (
                self.calc_blood_weight * HERO_BLOOD_WEIGHT
                + (
                    HERO_BLOOD_WEIGHT * DIVINE_SHIELD_WEIGHT
                    if self.is_divine_shield
                    else 0.0
                )
            )
        else :
            return 0.0
    def __str__(self):
        return f"SimulateCard(type={self.type},cardId={self.cardId},entityId={self.entityId},card_weight={self.card_weight},isActive={self.isActive},atc={self.cardDetails['attack']},blood={self.cardDetails['hp']},debuff={self.debuff}, after attack: atc={self.atc},blood={self.blood})"

    def __repr__(self):
        return self.__str__()

import threading
from copy import deepcopy
import logging

log = logging.getLogger(__name__)

EXEC_ACTION = False  # Replace with your actual flag

class Result:
    def __init__(self, heroHP=2 ** 20, all_weight=float('-inf')):
        self.heroHP = heroHP
        self.all_weight = all_weight  # Equivalent to Int.MIN_VALUE.toDouble() in Kotlin
        self.actions = []
        self.my_cards = None
        self.rival_cards = None
        self.times = 0

    def set_new_result(self, heroHP, new_weight, new_actions, my_cards, rival_cards):
        self.times += 1
        died_list = [action.death_card.entityId for action in new_actions if action.death_card != None]
        if len([action for action in new_actions if action.my_card.cardId == "NX2_019" and action.rival_card.entityId not in died_list]):
            return;
        if new_weight > self.all_weight:
            self.heroHP = heroHP
            self.all_weight = new_weight
            self.actions = deepcopy(new_actions)
            if my_cards is not None:
                self.my_cards = deepcopy(my_cards)
            if rival_cards is not None:
                self.rival_cards = deepcopy(rival_cards)

    def is_valid(result):
        return result.actions != []
    
    def __str__(self):
        return f"Result(all_weight={self.all_weight}, actions={self.actions}, my_card={self.my_card}, rival_card={self.rival_card})"

    def __repr__(self):
        return self.__str__()

class KOResult:
    def __init__(self, heroHP=2 ** 20, all_weight=float('-inf')):
        self.heroHP = heroHP  # Equivalent to Int.MIN_VALUE.toDouble() in Kotlin
        self.all_weight = all_weight
        self.actions = []
        self.my_cards = None
        self.rival_cards = None
        self.times = 0

    def set_new_result(self, heroHP, new_weight, new_actions, my_cards, rival_cards):
        self.times += 1
        died_list = [action.death_card.entityId for action in new_actions if action.death_card != None]
        if len([action for action in new_actions if action.my_card.cardId == "NX2_019" and action.rival_card.entityId not in died_list]):
            return;
        if heroHP < self.heroHP or (heroHP == self.heroHP and new_weight > self.all_weight):
            self.heroHP = heroHP
            self.all_weight = new_weight
            self.actions = deepcopy(new_actions)
            if my_cards is not None:
                self.my_cards = deepcopy(my_cards)
            if rival_cards is not None:
                self.rival_cards = deepcopy(rival_cards)

    def is_valid(result):
        return result.actions != []
    
    def __str__(self):
        return f"Result(all_weight={self.all_weight}, heroHP={self.heroHP}, actions={self.actions}, my_card={self.my_card}, rival_card={self.rival_card})"

    def __repr__(self):
        return self.__str__()

class Action:
    def __init__(self, death_card, my_card, rival_card, debuff):
        self.death_card = deepcopy(death_card)
        self.my_card = deepcopy(my_card)
        self.rival_card = deepcopy(rival_card)
        self.debuff = debuff

    def __str__(self):
        return f"Result(my_card={self.my_card}, rival_card={self.rival_card}, death_card={self.death_card})"

    def __repr__(self):
        return self.__str__()


def calc_state_weight(my_cards, rival_cards):
    """
    Calculate the state weight for the given cards.
    
    :param my_cards: List of SimulateCard objects representing the player's cards.
    :param rival_cards: List of SimulateCard objects representing the rival's cards.
    :param inversion: Boolean indicating if the calculation is inverted.
    :return: A double representing the calculated weight.
    """
    my_weight = calc_self_weight(my_cards)
    rival_weight = calc_self_weight(rival_cards)
    return my_weight[0] - rival_weight[0] - (TAUNT_EXTRA_WEIGHT if rival_weight[1] > 0 else 0)

def calc_self_weight(simulate_cards):
    """
    Calculate the weight and count of taunt cards for the given simulated cards.
    
    :param simulate_cards: List of SimulateCard objects.
    :param inversion: Boolean indicating if the calculation is inverted.
    :return: A tuple (weight, taunt_count) where:
             - weight: Total weight calculated from the cards.
             - taunt_count: Count of taunt cards that can be attacked and are alive.
    """
    taunt_count = 0
    weight = 0.0

    for simulate_card in simulate_cards:
        weight += simulate_card.calc_self_weight()
        if (
            simulate_card.is_taunt
            and simulate_card.is_alive()
        ):
            taunt_count += 1

    return weight, taunt_count

def triggerAttackHero(my_card, rivalHeroCard, triggerAttackHeroByVAC512, triggerAttackHeroByNX2_019, rival_hero_divine_shield):
    if triggerAttackHeroByVAC512 == True and triggerAttackHeroByNX2_019 == False:
        if rival_hero_divine_shield == True:
            rivalHeroCard.is_divine_shield = False
        else :
            rivalHeroCard.blood -= my_card.atc

    elif triggerAttackHeroByVAC512 == False and triggerAttackHeroByNX2_019 == True:
        if rival_hero_divine_shield == True:
            rivalHeroCard.is_divine_shield = False
        else :
            rivalHeroCard.blood -= 3

    elif triggerAttackHeroByVAC512 == True and triggerAttackHeroByNX2_019 == True:
        if rival_hero_divine_shield == True:
            rivalHeroCard.is_divine_shield = False
            rivalHeroCard.blood -= 3
        else :
            rivalHeroCard.blood -= my_card.atc
            rivalHeroCard.blood -= 3

def triggerRecoverHero(my_card, rivalHeroCard, triggerAttackHeroByVAC512, triggerAttackHeroByNX2_019, rival_hero_divine_shield):
    if triggerAttackHeroByVAC512 == True and triggerAttackHeroByNX2_019 == False:
        if rival_hero_divine_shield == True:
            rivalHeroCard.is_divine_shield = True
        else :
            rivalHeroCard.blood += my_card.atc

    elif triggerAttackHeroByVAC512 == False and triggerAttackHeroByNX2_019 == True:
        if rival_hero_divine_shield == True:
            rivalHeroCard.is_divine_shield = True
        else :
            rivalHeroCard.blood += 3

    elif triggerAttackHeroByVAC512 == True and triggerAttackHeroByNX2_019 == True:
        if rival_hero_divine_shield == True:
            rivalHeroCard.is_divine_shield = True
            rivalHeroCard.blood += 3
        else :
            rivalHeroCard.blood += my_card.atc
            rivalHeroCard.blood += 3