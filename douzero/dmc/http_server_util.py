import os
from copy import deepcopy
import torch

import re

import json
from itertools import combinations

from .file_writer import FileWriter
from .models import Model
from .utils import log, getDevice
from ..env.env import get_obs
from ..env.game import InfoSet, Deck
from ..env import move_selector_by_real_id as ms
from douzero.env.simulate_card import calc_self_weight

from ..env.game import CardTypeToIndex, CardSet, FullCardSet, RealCard2EnvCard, EnvCard2RealCard, HearthStone, HearthStoneById, GameEnv

from collections import Counter

from douzero.env.simulate_card import SimulateCard, Result, KOResult
from douzero.env import ko_strategy, clean_strategy

MaxIndex = len(CardSet)
gameEnv = GameEnv(None, None)
class MovesGener(object):
    """
    This is for generating the possible combinations
    """
    def __init__(self, hero_play, cards_list, Cardset):
        self.hero_play = hero_play
        self.cards_list = [] + cards_list
        self.CardSet = Cardset

    # generate all possible moves from given cards
    def gen_moves(self):
        all_combinations = []
        for r in range(0, len(self.cards_list) + 1):
            actions_list = [list(tup) for tup in combinations(self.cards_list, r)]
            all_combinations.extend(actions_list)
            if self.hero_play == False:
                all_combinations.extend([action + [{"cardId": "EX1_625t", "cost": 2}] for action in actions_list]) # 心灵尖刺
        return all_combinations

def getModel(flags):
    if not flags.actor_device_cpu or flags.training_device != 'cpu':
        if not torch.cuda.is_available() and not torch.mps.is_available():
            raise AssertionError("CUDA not available. If you have GPUs, please specify the ID after `--gpu_devices`. Otherwise, please train with CPU with `python3 train.py --actor_device_cpu --training_device cpu`")
    plogger = FileWriter(
        xpid=flags.xpid,
        xp_args=flags.__dict__,
        rootdir=flags.savedir,
    )

    # Learner model for training
    learner_model = Model(device=flags.training_device)

    # Load models if any
    for k in ['landlord', 'second_hand']:
        checkpointpath = os.path.expandvars(
            os.path.expanduser('%s/%s/%s' % (flags.savedir, flags.xpid, k+'_model.tar')))
        if flags.load_model and os.path.exists(checkpointpath):
            device = getDevice(deviceName=flags.training_device)
            checkpoint_states = torch.load(
                checkpointpath, map_location=(device)
            )
            learner_model.get_model(k).load_state_dict(checkpoint_states["model_state_dict"][k])
            stats = checkpoint_states["stats"]
            log.info(f"Resuming preempted job, current stats:\n{stats}")

    return learner_model

def get_legal_card_play_actions(hero_play,
                                crystal, player_hand_cards,
                                companion_on_battlefield_details,
                                costDebuff,
                                companion_died,
                                attack_rival_hero,
                                attack_me_hero,
                                player_deck_cards,
                                ):
    mg = MovesGener(hero_play, player_hand_cards, FullCardSet)

    all_moves = mg.gen_moves()

    moves = ms.filter_hearth_stone(all_moves, crystal, HearthStoneById,
                                companion_on_battlefield_details,
                                costDebuff,
                                companion_died,
                                attack_rival_hero,
                                attack_me_hero,
                                player_deck_cards,
                                player_hand_cards,
                                )
    move_ids = [[card["cardId"] for card in move] for move in moves]
    return [move for move in move_ids if len(move) == 0 or move[0] != "GAME_005" or len([mv for mv in move_ids if mv == move[1:]]) == 0]
    
def get_infoset(position,
                hero_play,
                crystal,
                player_hand_cards,
                player_deck_cards,
                played_actions,
                companion_on_battlefield_details,
                costDebuff,
                companion_died,
                rival_attack_on_battlefield,
                attack_rival_hero,
                attack_me_hero,
                ):
    
    info_set = InfoSet(position)
    player_hand_cards_cardId = [card["cardId"] for card in player_hand_cards]
    played_actions_cardId = [[card["cardId"] for card in action] for action in played_actions]
    companion_died_cardId = [card["cardId"] for card in companion_died]
    info_set.all_legal_actions = get_legal_card_play_actions(hero_play,
                                                             crystal,
                                                            player_hand_cards,
                                                            companion_on_battlefield_details,
                                                            costDebuff,
                                                            companion_died_cardId,
                                                            attack_rival_hero,
                                                            attack_me_hero,
                                                            player_deck_cards,
                                                         )
    
    info_set.legal_actions = [action for action in info_set.all_legal_actions if len(action) == 0 or max([RealCard2EnvCard[card] for card in action]) < MaxIndex]

    info_set.full_player_hand_cards = player_hand_cards_cardId
    info_set.player_hand_cards = [card for card in info_set.full_player_hand_cards if RealCard2EnvCard[card] < MaxIndex]
    info_set.player_deck_cards = player_deck_cards
    info_set.last_move = played_actions_cardId[-1] if len(played_actions_cardId) > 0 else []

    info_set.rival_attack_on_battlefield = rival_attack_on_battlefield
        
    info_set.companion_on_battlefield = [card["cardId"] for card in companion_on_battlefield_details]

    info_set.played_actions = played_actions_cardId

    info_set.minion_attack_next_round = []
    info_set.advice = []
    info_set.player_deck_cards = player_deck_cards
    info_set.attack_rival_hero = attack_rival_hero

    for action in info_set.legal_actions:
        action = updateAction(action, player_deck_cards)
        info_set.minion_attack_next_round.append(getCombineScore(action, companion_on_battlefield_details, player_deck_cards))
        info_set.advice.append(min(9, ms.calculateAttack(action=action,
                                                         companion_on_battlefield_details=companion_on_battlefield_details,
                                                         HearthStoneById=HearthStoneById,
                                                        ) // 3)) # todo
    return info_set

def updateAction(action, player_deck_cards):
    if "CFM_637" in player_deck_cards: # 海盗帕奇斯
        pirateCards = [ idx for idx, card in enumerate(action) if "races" in HearthStoneById[card] and "PIRATE" in HearthStoneById[card]["races"] ]
        if len(pirateCards) > 0:
            action = action[:pirateCards[0]+1] + ["CFM_637"] + action[pirateCards[0]+1:]
    return action

def getCombineScore(action, companion_on_battlefield_details, player_deck_cards):
    # CFM_637
    extraScore = 0
    extraScore += 2 if "CFM_637" in action and "CFM_637" in player_deck_cards else 0
    if "REV_290" in action and sum([card["attack"] for card in companion_on_battlefield_details]) > 0:
        extraScore += 6
    elif "REV_290" in action:
        extraScore += 3
    if "SCH_514" in action:
        extraScore += 2
    return int(ms.calculateAttack(action, companion_on_battlefield_details,
                              HearthStoneById=HearthStoneById) * 1.2 + ms.calculateAttackNextRound(getCompanionOnDetails(action, companion_on_battlefield_details)[0]) * 1.2 \
    + ms.calculateHPNextRound(getCompanionOnDetails(action, companion_on_battlefield_details)[0]) + extraScore)

def convertInfoset(infoset):
    infoset.player_deck_cards = [RealCard2EnvCard[card] for card in infoset.player_deck_cards]
    infoset.player_hand_cards = [RealCard2EnvCard[card] for card in infoset.player_hand_cards]
    infoset.companion_on_battlefield = [RealCard2EnvCard[card] for card in infoset.companion_on_battlefield if RealCard2EnvCard[card] < MaxIndex]
    
    infoset.legal_actions = [[RealCard2EnvCard[card] for card in action] for action in infoset.legal_actions]
    infoset.last_move = [RealCard2EnvCard[card] for card in infoset.last_move if RealCard2EnvCard[card] < MaxIndex]
    infoset.played_actions = [[RealCard2EnvCard[card] for card in action if RealCard2EnvCard[card] < MaxIndex] for action in infoset.played_actions]
    return infoset

def checkKO(info_set, companion_on_battlefield_details, rival_on_battlefield_details, rival_hero, player_hand_cards,
                       secret_size,
                       coreCards,
                       ):
    # TODO 嘲讽吸血

    if rival_hero["isActive"] == False:
        return -1, []

    all_legal_actions = deepcopy(info_set.all_legal_actions)
    all_legal_actions.reverse()
    finished_actions = []
    finalPreActionDetails = []
    finalResult = KOResult()
    finalIndex = -1
    finalBattleAttack = 0
    for index, action in enumerate(all_legal_actions):
        find = False
        for f_action in finished_actions:
            if contains_all(action, f_action):
                find = True
                break;
        if find:
            continue
        # if "WON_062" not in action or "SW_446" not in action or "CORE_WON_065" not in action: # debug
        #     continue
        # print ("DEBUG", action)
        # 没有用的卡
        if "SCH_514" in action or "YOD_032" in action or "SW_444" in action: # 亡者复生 狂暴邪翼蝠 暮光欺诈者
            continue
        # NX2_019_count = len([card for card in action if card == "NX2_019"]) # 精神灼烧
        # minion_count = len([card for card in action if HearthStoneById[card]["type"] == "MINION" and card != "TOY_381" and card != "GVG_009" and
        #                     card != "SW_446"]) # 纸艺天使 暗影投弹手
        # if NX2_019_count == 0 and minion_count > 0:
        #     continue

        SW_446_Count = len([cardDetails for cardDetails in companion_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从
        SW_446_Count += len([card for card in action if card == "SW_446"]) # 虚触侍从
        SW_446_Count += len([cardDetails for cardDetails in rival_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从

        # pre_action = [card for card in action if card == "GAME_005"] + \
        #     [card for card in action if HearthStoneById[card]["type"] == "MINION"] + \
        #     [card for card in action if card == "VAC_419" or card == "DS1_233"]

        pre_action = [card for card in action if card == "GAME_005"] + \
            [card for card in action if HearthStoneById[card]["type"] == "MINION" and HearthStoneById[card]["name"] != "暗影投弹手"]
        pre_actionDetails = convertActionToDetails([card for card in pre_action], deepcopy(player_hand_cards), companion_on_battlefield_details)
        actionInDetails = convertActionToDetails([card for card in action if card not in pre_action], deepcopy(player_hand_cards), companion_on_battlefield_details)

        # directAttack, is_divine_shield = ms.calculateDirectAttack(rival_hero, action, companion_on_battlefield_details, rival_on_battlefield_details)
        
        # print (directAttack, is_divine_shield)
        rival_hero_tmp = deepcopy(rival_hero)
        # rival_hero_tmp["hp"] -= directAttack
        rival_hero_tmp["debuff"] = SW_446_Count
        # rival_hero_tmp["card"]["isDivineShield"] = is_divine_shield

        my_cards, rival_cards = generateSimulateCard(actionInDetails, companion_on_battlefield_details + [card for card in pre_actionDetails if card["type"] == "MINION"], 
                                                    rival_on_battlefield_details, coreCards=coreCards,
                                                        rivalHero=rival_hero_tmp)
        # for card in my_cards:
        #     print (card.cardId, card.atc)
        koResult = ko_strategy.calc_clean(my_cards, rival_cards)

        if ms.calculateKO(action, companion_on_battlefield_details, rival_on_battlefield_details, rival_hero, secret_size,
                            HearthStoneById,
                            ):
            if koResult.heroHP > 0:
                for t_action in koResult.actions:
                    print (t_action)
                print (f"times: {koResult.times}, rivalHP: {koResult.heroHP}, reduceHP: {rival_hero['hp'] - koResult.heroHP} ")

                for attack in koResult.actions:
                    companion = attack.my_card.cardDetails
                    rival = attack.rival_card.cardDetails
                    if rival != None:
                        print (f"{companion['cardId']} - {rival['cardId']} ({companion['entityId']} - {rival['entityId']}) ({HearthStoneById[companion['cardId']]['name']} - {HearthStoneById[rival['cardId']]['name']})")
                    else:
                        print (f"{companion['cardId']} - ({companion['entityId']} - ) ({HearthStoneById[companion['entityId']]['name']} - )")
            assert koResult.heroHP <= 0
        if koResult.heroHP <= 0 and (secret_size == 0 or HearthStoneById[rival_hero["cardId"]]["cardClass"] not in ["HUNTER", "MAGE"]):
            # for card in my_cards:
            #     print (card)
            # for koact in koResult.actions:
            #     print (koact.my_card, koact.rival_card, koact.death_card)
            print (f"checkKO times: {koResult.times}, rivalHP: {koResult.heroHP}, reduce: {rival_hero['hp'] - koResult.heroHP}, all_weight: {koResult.all_weight}")
            return index, \
                orderForceAction(pre_actionDetails, rival_on_battlefield_details, rival_hero, [{"companion": t_action.my_card.cardDetails, \
                                                                                                "rival": t_action.rival_card.cardDetails if t_action.rival_card != None else None, } \
                                                                            for t_action in koResult.actions])
        deadCard = [attack.death_card.entityId for attack in koResult.actions if attack.death_card != None]
        SW_446_Count -= len([attack.death_card.entityId for attack in koResult.actions if attack.death_card != None and attack.death_card.cardId == "SW_446"])

        buff = {}
        for attack in koResult.actions:
            if attack.my_card.type == "LOCATION":
                if attack.rival_card.entityId in buff:
                    buff[attack.rival_card.entityId] += 2
                else:
                    buff[attack.rival_card.entityId] = 2
        
        battleAttack = sum([card.atc + SW_446_Count + buff.get(card.entityId,0) for card in my_cards if card.type == "MINION" and card.entityId not in deadCard and card.atc > 0])
        if koResult.heroHP < finalResult.heroHP or (koResult.heroHP == finalResult.heroHP and koResult.all_weight > finalResult.all_weight):
            finalPreActionDetails = pre_actionDetails
            finalResult = koResult
            finalIndex = len(all_legal_actions) -1 - index # reversed
            finalBattleAttack = battleAttack + 2 + SW_446_Count
        finished_actions.extend([action])
    if (rival_hero["hp"] - finalResult.heroHP) >= 10 or (finalResult.heroHP <= finalBattleAttack and finalResult.heroHP <= 10) or finalResult.heroHP <= 5:
        # for card in my_cards:
        #     print (card)
        # for koact in finalResult.actions:
        #     print (koact.my_card, koact.rival_card, koact.death_card)
        print (f"checkKO times: {finalResult.times}, rivalHP: {finalResult.heroHP}, reduce: {rival_hero['hp'] - finalResult.heroHP}, battleAttack: {finalBattleAttack}, all_weight: {koResult.all_weight}")
        return finalIndex, \
            orderForceAction(finalPreActionDetails, rival_on_battlefield_details, rival_hero, [{"companion": action.my_card.cardDetails, \
                                                                                                "rival": action.rival_card.cardDetails if action.rival_card != None else None, } for action in finalResult.actions])

    return -1, []

def contains_all(small, large):
    return not (Counter(small) - Counter(large))

def getMockActionIndex(info_set, companion_on_battlefield_details, player_deck_cards, player_hand_cards,
                       ):
    scoreMax = 0
    actionMaxIndex = 0
    player_hand_cards_cardId = [card["cardId"] for card in player_hand_cards]
    for index, action in enumerate(info_set.all_legal_actions):
        action = updateAction(action, player_deck_cards)
        score = getCombineScore(action=action, companion_on_battlefield_details=companion_on_battlefield_details, player_deck_cards=player_deck_cards)
        if "CFM_637" in player_deck_cards or "DRG_056" in player_hand_cards_cardId:
            score += annotationManually(action, player_hand_cards_cardId)
        if (score > scoreMax and "GAME_005" not in action): # 不带硬币
            scoreMax = score
            actionMaxIndex = index
    return actionMaxIndex

def convertActionToDetails(action, player_hand_cards, companion_on_battlefield_details = []): # MYWEN TODO 搜索KO，放随从 血量+1 攻击力+1
    buff = getCompanionOnDetails(action, companion_on_battlefield_details)[1] # TODO HP by ID is not right
    actionInDetails = []
    for idx, card in enumerate(action):
        if card == "EX1_625t":
            actionInDetails.extend([
                {"cardId": "EX1_625t", "attack": 2, "hp": 1, "entityId": "", "card": {}, "round": -1, "isActive": True, "type": "HERO_POWER", "area": "HandArea"}
                ])
        else:
            if card == "CFM_637" and len([card for card in player_hand_cards if card["cardId"] == "CFM_637"]) == 0:
                actionInDetails.extend([
                    {"cardId": "CFM_637", "attack": buff[idx]["attack"], "hp": buff[idx]["hp"], "entityId": "", "card": {}, "round": -1, "isActive": False, "type": "MINION",  "area": "PlayArea"}
                    ])
            else:
                for details in player_hand_cards:
                    if card == details["cardId"]:
                        player_hand_cards.remove(details)
                        # card["is_taunt"] = True if ms.checkTaunt(card, HearthStoneById) else False
                        # card["is_poisonous"] = True if "text" in HearthStoneById[card["cardId"]] and "剧毒" in HearthStoneById[card["cardId"]]["text"] else False
                        # card["is_vampire"] = True if "text" in HearthStoneById[card["cardId"]] and "吸血" in HearthStoneById[card["cardId"]]["text"] else False
                        details["hp"] = HearthStoneById[card]["health"] if "health" in HearthStoneById[card] else 1
                        details["attack"] = HearthStoneById[card]["attack"] if "attack" in HearthStoneById[card] else 1
                        if details["cardId"] == "NX2_019" or card == "EX1_625t": # TODO 法术的伤害
                            details["attack"] = 2
                        if details["cardId"] == "VAC_419":
                            details["attack"] = 4
                        if details["cardId"] == "DS1_233":
                            details["attack"] = 5
                        details["type"] = HearthStoneById[card]["type"]
                        if details["type"] == "SPELL" or details["type"] == "HERO_POWER" or details["type"] == "LOCATION":
                            details["isActive"] = True
                        else:
                            details["isActive"] = False
                        if details["type"] == "MINION":
                            details["hp"] = buff[idx]["hp"]
                            details["attack"] = buff[idx]["attack"]
                        actionInDetails.extend([details])
                        break;
    # print (action)
    # print (actionInDetails)
    assert len(action) == len(actionInDetails)
    return actionInDetails

def completeDetails(actionInDetails, coreCards):
    for card in actionInDetails:
        card["card_weight"] = coreCards.get(card["cardId"], 0) + 1.0
        card["type"] = HearthStoneById[card["cardId"]]["type"]
        card["name"] = HearthStoneById[card["cardId"]]["name"]
    return actionInDetails

def compete(actions, info_set, companion_on_battlefield_details, rival_on_battlefield_details, rival_hero, me_hero, player_deck_cards, player_hand_cards,
            secret_size,
            coreCards,
            ):
    maxCost = 0
    maxScore = 0
    maxAction = []
    player_hand_cards_cardId = [card["cardId"] for card in player_hand_cards]
    for action in actions:
        cost, _ = ms.calculateActionCost(action, HearthStoneById, info_set.companion_on_battlefield,
                                         info_set.attack_rival_hero + ms.calculateActionAttack(action, companion_on_battlefield_details, HearthStoneById),
                                          info_set.player_deck_cards,
                                        )
        action = updateAction(action, player_deck_cards)
        score = getCombineScore(action, companion_on_battlefield_details=companion_on_battlefield_details, player_deck_cards=player_deck_cards)
        if "CFM_637" in player_deck_cards or "DRG_056" in player_hand_cards_cardId:
            score += annotationManually(action, player_hand_cards_cardId)
        if score > maxScore or (score == maxScore and len(action) < len(maxAction)):
            maxCost = cost
            maxScore = score
            maxAction = action
        print ([HearthStoneById[card]["name"] for card in action], action, "cost: ", cost, "score: ", score)
    actionInDetails = convertActionToDetails(maxAction, deepcopy(player_hand_cards))
    return actionInDetails, maxCost, maxScore

def getCompanionOnDetails(action, companion_on_battlefield_details):
    companion_on_battlefield = [card["cardId"] for card in companion_on_battlefield_details]
    buff = {}
    for idx, card in enumerate(action):
        cardId = card
        type = HearthStoneById[cardId]["type"]
        if type != "MINION":
            continue
        buff[idx] = {
                "cardId": card,
                "attack": 0,
                "hp": 0,
            }
    # 海盗 attack+1
    pirate_attack_plus_count = len([card for card in companion_on_battlefield if card == "TOY_518"]) # 宝藏经销商
    for idx, card in enumerate(action):
        cardId = card
        type = HearthStoneById[cardId]["type"]

        if type != "MINION":
            continue

        attack = HearthStoneById[cardId]["attack"]
        if "races" in HearthStoneById[cardId] and "PIRATE" in HearthStoneById[cardId]["races"]:
            attack += pirate_attack_plus_count
        buff[idx]["attack"] = attack

        if cardId == "TOY_518":
            pirate_attack_plus_count += 1
        

    # 随从 hp+1
    minion_hp_plus_count = len([card for card in companion_on_battlefield if card == "CORE_WON_065"]) # 随船外科医师
    for idx, card in enumerate(action):
        cardId = card
        type = HearthStoneById[cardId]["type"]
        if "MINION" != type:
            continue
        hp = HearthStoneById[cardId]["health"]
        hp += minion_hp_plus_count
        buff[idx]["hp"] = hp
        if cardId == "CORE_WON_065":
            minion_hp_plus_count += 1

    return companion_on_battlefield_details + [buff[key] for key in buff], buff

def patch(heroPlay, player_hand_cards, rival_battle_cards, companion_battle_cards, coreCard, rivalHero):
    if len([card for card in rival_battle_cards if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION"]) == 0 and \
            (len([card for card in companion_battle_cards if card["hp"] <= 1
            and coreCard[card["cardId"]] < 1.0
            and HearthStoneById[card["cardId"]]["type"] == "MINION"
                and card["isActive"] == False]) == 0):
        cards = [card for card in player_hand_cards if card["cardId"] == "NX2_019"]
        for card in cards: # 精神灼烧
            player_hand_cards.remove(card)
    if (len([card for card in companion_battle_cards if HearthStoneById[card["cardId"]]["type"] == "MINION" and card["isActive"] == True]) < 3 \
        and len([card for card in companion_battle_cards if card["cardId"] == "CORE_WON_065"]) == 0) \
        or rivalHero["card"]["isImmune"] == True \
        or len([card for card in rival_battle_cards if ms.checkTaunt(card, HearthStoneById)]) > 0 \
        or len([card for card in rival_battle_cards if HearthStoneById[card["cardId"]]["type"] == "MINION"]) >= 3:
        cards = [card for card in player_hand_cards if card["cardId"] == "SW_446"]
        for card in cards: # 虚触侍从
            player_hand_cards.remove(card)
    if len([card for card in companion_battle_cards if HearthStoneById[card["cardId"]]["type"] == "MINION"]) >= 5 \
        and HearthStoneById[rivalHero["cardId"]]["cardClass"] in ["SHAMAN", "WARLOCK", "WARRIOR", "DEATHKNIGHT", "MAGE"]:
        cards = [card for card in player_hand_cards if HearthStoneById[card["cardId"]]["type"] == "MINION"]
        for card in cards:
            player_hand_cards.remove(card)
    if rivalHero["card"].get("isImmune", False) == True:
        cards = [card for card in player_hand_cards if card["cardId"] in ["GVG_009", "NX2_019", "VAC_419", "DS1_233", "EX1_625t"] or
                 card["name"] in ["暗影投弹手", "精神灼烧", "针灸", "心灵震爆", "心灵尖刺"]]
        for card in cards:
            player_hand_cards.remove(card)
        heroPlay = True
    return player_hand_cards, heroPlay

def onceCard(txt):
    current_turn_pattern = r".*在本回合.*"
    battle_cry_pattern = r".*战吼.*"
    die_cry_pattern = r".*亡语.*"
    return local_match(current_turn_pattern, txt) != None \
        or local_match(battle_cry_pattern, txt) != None \
        or local_match(die_cry_pattern, txt) != None

def local_match(pattern, text):
    return re.search(pattern, text, re.MULTILINE)

def getCoreCard(card_list):
    every_after_pattern = r".*后.*"
    every_when_pattern = r".*当.*"
    every_when_pattern_2 = r".*时.*"
    attack_plus_pattern =r".*伤害\+.*"
    other_have_pattern = r".*其他.*拥有.*"
    other_get_pattern = r".*其他.*获得.*"
    near_have_pattern = r".*相邻.*拥有.*"
    near_get_pattern = r".*相邻.*获得.*"
    if_have_pattern = r".*如果你.*"
    core_cards = {}
    for cardId in card_list:
        value = 0.0
        if cardId in HearthStoneById and "text" in HearthStoneById[cardId] and HearthStoneById[cardId]["type"] == "MINION":
            meta = HearthStoneById[cardId]
            if cardId == "VAC_321": # 伊辛迪奥斯
                value += 5
            elif cardId == "TSC_922": # 驻锚图腾
                value += 5
            elif cardId == "CORE_NEW1_021": # 末日预言者
                value += 20
            elif cardId in ["TOY_518", "CORE_WON_065"]: # 宝藏经销商 随船外科医师
                value += 2
            elif cardId in ["TOY_381"]: # 纸艺天使
                value += 5
            elif cardId in ["SW_446"]: # 虚触侍从
                value += 1
            elif cardId in ["CORE_EX1_012"]: # 血法
                value += 2
            elif cardId == "VAC_512": # 心灵按摩师
                value += 0.5
            elif cardId == "CORE_CS3_014": # 赤红教士
                value += 2
            elif local_match(every_after_pattern, meta["text"]) and onceCard(meta["text"]) == False and cardId != "CFM_637" and cardId != "DRG_056":
                value += 2
            elif local_match(every_when_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif local_match(every_when_pattern_2, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif local_match(other_have_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 6
            elif local_match(other_get_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 6
            elif local_match(near_have_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif local_match(near_get_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif local_match(attack_plus_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif local_match(r".*你的英雄技能的法力值.*", meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif local_match(r".*你的英雄技能会.*", meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif local_match(r".*你的英雄的攻击力.*", meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
            elif local_match(if_have_pattern, meta["text"]) and onceCard(meta["text"]) == False:
                value += 2
        core_cards[cardId] = value
        
    return core_cards

def getPowerPlus(companion_battle_cards):
    return len([card for card in companion_battle_cards if "text" in HearthStoneById[card] and "法术伤害+" in HearthStoneById[card]["text"]])

def filter(action): # todo
    support_card = [
        # SPELL
        "GDB_445",
        "CS2_024",
        "GDB_456",
        "YOG_526",
        "TOY_508",
        "TTN_454",
        "CORE_AT_064",
        "MIS_709",
        "CS2_029",
        "GDB_305",
        "CORE_EX1_129",
        "VAC_323",
        "CORE_CS2_093",
        "VAC_414",
        "ETC_069",
        "CS2_032",
        "EX1_179",
        "VAC_951",
        "CS2_022",
        "VAC_916",
        "ETC_076",
        "TTN_079",
        "GDB_439",
        # MINION
        "GDB_901",
        "TTN_087",
        "WORK_009",
        "CS3_034",
    ] + CardSet
    return [card for card in action if card["cardId"] in support_card or "text" not in HearthStoneById[card["cardId"]] or \
            "随机" in HearthStoneById[card["cardId"]]["text"] or \
            ("一个敌方随从" not in HearthStoneById[card["cardId"]]["text"] and "一个友方随从" not in HearthStoneById[card["cardId"]]["text"])]

def orderForceAction(finalPreActionDetails, rival_on_battlefield_details, rival_hero, forceAction):
    coinActions = [{"companion": action, "rival": None, } for action in finalPreActionDetails if action["cardId"] == "GAME_005"]
    preActions = [{"companion": action, "rival": None, } for action in finalPreActionDetails if action["cardId"] != "GAME_005"]
    rival_entity_ids = [card["entityId"] for card in rival_on_battlefield_details + [rival_hero]]
    forceActionAttackTaunt = []
    forceActionNoTaunt = []

    for action in forceAction:
        if action["companion"]["cardId"] == "REV_290" and action["rival"]["area"] == "PlayArea":
            preActions = [action] + preActions
        elif action["companion"]["cardId"] == "REV_290" and action["rival"]["name"] != "暗影投弹手":
            preActionsIndex = [act["companion"]["entityId"] for act in preActions]
            findIndex = preActionsIndex.index(action["rival"]["entityId"])
            preActions = preActions[:findIndex + 1] + [action] + preActions[findIndex + 1:]

    for action in forceAction: # MYWEN TODO EX1_625t and TOY_381
        if action["companion"]["cardId"] == "REV_290" and (action["rival"]["area"] == "PlayArea" or action["rival"]["name"] != "暗影投弹手"): # TODO for GVG_009
            continue
        # forceActionAttackTaunt.extend([action])
        # if action["rival"] != None and not ms.checkTaunt(action["rival"], HearthStoneById) and action["rival"]["entityId"] in rival_entity_ids: # 非嘲讽随从最后攻击
        #     forceActionNoTaunt.extend([action])
        if action["companion"]["cardId"] == "NX2_019" and action["rival"]["entityId"] not in rival_entity_ids: # 打自己随从后移
            forceActionNoTaunt.extend([action])
        else:
            forceActionAttackTaunt.extend([action])
    return coinActions + preActions + forceActionAttackTaunt + forceActionNoTaunt

def cleanTaunt(round, info_set, companion_on_battlefield_details, rival_on_battlefield_details, player_hand_cards,
                       coreCards,
                       rival_hero,
                       ):
    # if len([card for card in rival_on_battlefield_details if (ms.checkTaunt(card, HearthStoneById) or \
    #         coreCards.get(card["cardId"], 0) > 0.5 or
    #         ms.checkHealthSteal(card, HearthStoneById))
    #         ]) <= 0:
    #     return -1, []

    # rival_core_cards = [card for card in rival_on_battlefield_details if ms.checkTaunt(card, HearthStoneById) or \
    #         coreCards.get(card["cardId"], 0) > 0 or
    #         ms.checkHealthSteal(card, HearthStoneById)
    #         ]

    my_cards_tmp, rival_cards_tmp = generateSimulateCard([], companion_on_battlefield_details,
                                            rival_on_battlefield_details, 
                                            coreCards,
                                            None,
                                            )
    my_weight, my_tauntCount = calc_self_weight(my_cards_tmp)
    rival_weight, rival_tauntCount = calc_self_weight(rival_cards_tmp)
    
    # TODO ButterflyAda
    print (my_weight, rival_weight, [card["cardId"] for card in player_hand_cards], rival_tauntCount)
    highAttack = len([card for card in rival_on_battlefield_details if card["hp"] > 0 and card["attack"] / card["hp"] >=3 ])
    if my_weight < 10 and rival_weight < 10 and ("NX2_019" not in [card["cardId"] for card in player_hand_cards]) and rival_tauntCount == 0 and highAttack <= 0:
        return -1, []
    if round == 1 and highAttack <= 0:
        return -1, []

    if len([card for card in rival_cards_tmp if card.can_be_attacked() == True]) <= 0 and highAttack <= 0:
        return -1, []

    all_legal_actions = deepcopy(info_set.all_legal_actions)
    all_legal_actions.reverse()
    finished_actions = []

    finalResult = Result()
    finalIndex = -1
    finalPreActionDetails = []
    # all_legal_actions = [["EX1_625t", "NX2_019", "NX2_019"]]
    # print ("DEBUG")
    for index, action in enumerate(all_legal_actions):
        # if len(action) > 0 and action[0] == "GAME_005" and len([ac for ac in all_legal_actions if ac == action[1:]]) > 0:
        #     print("MYWEN", action)
        find = False
        for f_action in finished_actions:
            if contains_all(action, f_action):
                find = True
                break;
        if find:
            continue

        if len([card for card in action if HearthStoneById[card]["type"] == "LOCATION" or card == "NX2_019" or card == "EX1_625t" or card == "GAME_005"
                or card == "TOY_381" or card == "CORE_WON_065"]) < len(action):
            continue

        # if "CORE_WON_065" in action and "TOY_381" not in action:
        #     continue

        # if "SCH_514" in action or "YOD_032" in action or "SW_444" in action: # 亡者复生 狂暴邪翼蝠 暮光欺诈者
        #     continue

        SW_446_Count = len([cardDetails for cardDetails in companion_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从
        SW_446_Count += len([card for card in action if card == "SW_446"]) # 虚触侍从
        SW_446_Count += len([cardDetails for cardDetails in rival_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从

        rival_hero_tmp = deepcopy(rival_hero)
        rival_hero_tmp["debuff"] = SW_446_Count

        pre_action = [card for card in action if card == "GAME_005"] + \
            [card for card in action if HearthStoneById[card]["type"] == "MINION"]

        pre_actionDetails = convertActionToDetails([card for card in pre_action], deepcopy(player_hand_cards), companion_on_battlefield_details)
        actionInDetails = convertActionToDetails([card for card in action if card not in pre_action], deepcopy(player_hand_cards), companion_on_battlefield_details)
        my_cards, rival_cards = generateSimulateCard(actionInDetails, companion_on_battlefield_details, 
                                                     rival_on_battlefield_details, 
                                                     coreCards,
                                                     rival_hero_tmp,
                                                     )
        # for card in my_cards:
        #     print (card)
        # for card in rival_cards:
        #     print (card)
        result = clean_strategy.calc_clean(my_cards, rival_cards)

        if finalResult.all_weight < result.all_weight:
            finalIndex = len(all_legal_actions) -1 - index # because it reversed
            finalResult = deepcopy(result)
            finalPreActionDetails = pre_actionDetails
        finished_actions.extend([action])
    # if finalIndex != -1 and len(finalResult.actions) > 0:
    #     for action in finalResult.actions:
    #         print (action)
    print (f"cleanTaunt times: {finalResult.times}, score: {finalResult.all_weight}, rivalHP: {finalResult.heroHP}")
    return finalIndex, \
        orderForceAction(finalPreActionDetails, rival_on_battlefield_details, rival_hero, [{"companion": action.my_card.cardDetails, \
                                                                                            "rival": action.rival_card.cardDetails if action.rival_card != None else None, } for action in finalResult.actions])

def generateSimulateCard(actionInDetails, companion_on_battlefield_details, rival_on_battlefield_details, coreCards, rivalHero):
    actionInDetails = completeDetails(actionInDetails, coreCards)
    companion_on_battlefield_details_tmp = completeDetails(deepcopy(companion_on_battlefield_details), coreCards)

    rival_on_battlefield_details_tmp = deepcopy(rival_on_battlefield_details)
    if rivalHero:
        rival_on_battlefield_details_tmp.extend([rivalHero])

    rival_on_battlefield_details_tmp = completeDetails(rival_on_battlefield_details_tmp, coreCards)

    my_cards = [SimulateCard(cardDetails) for cardDetails in companion_on_battlefield_details_tmp] + \
        [SimulateCard(cardDetails) for cardDetails in actionInDetails]
    
    rival_cards = [SimulateCard(card) for card in rival_on_battlefield_details_tmp]

    playList = [ # 按照攻击力从小到大排序
        "LOCATION",
        "MINION",
        "HERO_POWER", # 心灵尖刺
        "SPELL",
        "NX2_019",
    ]
    
    playOrder = {value: index for index, value in enumerate(playList)}
    
    sorted_cards = sorted(my_cards, key=lambda card: (card.atc, card.card_weight, playOrder[card.cardId]) if card.cardId in playOrder else (card.atc, card.card_weight, playOrder[card.type]))

    return sorted_cards, rival_cards

def checkSW_444(round, crystal, player_hand_cards, companion_battle_cards, rival_battle_cards, attack_rival_hero, attack_me_hero,
                rivalHeroDetails, meHeroDetails,
                ):
    rivalTaunt = len([card for card in rival_battle_cards if ms.checkTaunt(card, HearthStoneById)])
    minionCanAttack = [card for card in companion_battle_cards if card["attack"] > 0 and card["isActive"] == True]
    player_hand_cards_cardId = [card["cardId"] for card in player_hand_cards]
    if len(minionCanAttack) > 0 and rivalTaunt == 0 and attack_rival_hero == 0 and attack_me_hero == 0 and crystal >= 2 and "SW_444" in player_hand_cards_cardId \
        and "SW_446" not in player_hand_cards_cardId:
        response = {"status": "succ", "action": [], "cost": 0, "score": 0, "crystal": crystal, \
            "coreCards": getCoreCard([card["cardId"] for card in rival_battle_cards + companion_battle_cards] + CardSet),
            "powerPlus": getPowerPlus([card["cardId"] for card in companion_battle_cards]),
            "force_actions": [
                {
                    "companion": minionCanAttack[0],
                    "rival": rivalHeroDetails
                }
            ],
            "needSurrender": False,
        }
        return True, response
    return False, {}

def checkSCH_514(crystal, player_hand_cards,
                 companion_battle_cards,
                 rival_battle_cards,
                 companion_died,
                ):
    importantMinion = [card for card in companion_died if card["cardId"] in ["TOY_518", "TOY_381", "CORE_WON_065", "SW_446"]] #宝藏经销商   纸艺天使    随船外科医师      虚触侍从
    minionSCH_514 = [card for card in player_hand_cards if card["cardId"] == "SCH_514"]
    if len(minionSCH_514) > 0 and crystal >= minionSCH_514[0]["cost"] \
        and (len(importantMinion) > 0 or len(companion_died) >= 2):
        response = {"status": "succ", "action": [], "cost": 0, "score": 0, "crystal": crystal, \
            "coreCards": getCoreCard([card["cardId"] for card in rival_battle_cards + companion_battle_cards] + CardSet),
            "powerPlus": getPowerPlus([card["cardId"] for card in companion_battle_cards]),
            "force_actions": [{"companion": card, "rival": None} for card in minionSCH_514],
            "needSurrender": False,
        }
        return True, response
    return False, {}

def getCostDebuff(position, round, rival_battle_cards):
    costDebuff = {
        "round": {
            "MINION": 0,
            "LOCATION": 0,
            "SPELL": 0,
            "HERO_POWER":0,
        },
        "once": {
            "MINION": 0,
            "LOCATION": 0,
            "SPELL": 0,
            "HERO_POWER":0,
        }
    }

    if position == "landlord":
        round -= 1

    for cardDetails in rival_battle_cards:
        cardId = cardDetails["cardId"]
        cardRound = cardDetails["playedRound"]
        name = HearthStoneById[cardId]["name"]
        if name == "异教低阶牧师" and cardRound >= round:
            costDebuff["round"]["SPELL"] += 1
        elif name == "音箱践踏者" and cardRound >= round:
            costDebuff["round"]["SPELL"] += 2
        elif name == "洛欧塞布" and cardRound >= round:
            costDebuff["round"]["SPELL"] += 5
        elif name == "冻感舞步" and cardRound >= round:
            costDebuff["round"]["MINION"] += 5
    return costDebuff

def printForceAction(round, crystal, info_set, force_actions, cost, score, rival_battle_cards):
    handCards = [HearthStoneById[card]["name"] for card in info_set.player_hand_cards]
    deckCards = [HearthStoneById[card]["name"] for card in info_set.player_deck_cards]
    companonCards = [HearthStoneById[card]["name"] for card in info_set.companion_on_battlefield]
    rivalCards = [HearthStoneById[card["cardId"]]["name"] for card in rival_battle_cards]
    print (f"round: {round}, crystal: {crystal}")
    print(f"handCards: {handCards}")
    print(f"deckCards: {deckCards}")
    print(f"companonCards: {companonCards}")
    print(f"rivalCards: {rivalCards}" )
    for attack in force_actions:
        companion = attack["companion"]
        rival = attack["rival"]
        if rival != None:
            print (f"{companion['cardId']} - {rival['cardId']} ({companion['entityId']} - {rival['entityId']}) ({HearthStoneById[companion['cardId']]['name']} - {HearthStoneById[rival['cardId']]['name']})")
        else:
            print (f"{companion['cardId']} - ({companion['entityId']} - ) ({HearthStoneById[companion['cardId']]['name']} -)")
    print(f"cost: {cost}, score: {score}")

def printAction(round, crystal, info_set, actionInDetails, cost, score, rival_battle_cards):
    handCards = [HearthStoneById[card]["name"] for card in info_set.player_hand_cards]
    deckCards = [HearthStoneById[card]["name"] for card in info_set.player_deck_cards]
    companonCards = [HearthStoneById[card]["name"] for card in info_set.companion_on_battlefield]
    rivalCards = [HearthStoneById[card["cardId"]]["name"] for card in rival_battle_cards]
    print (f"round: {round}, crystal: {crystal}")
    print(f"handCards: {handCards}")
    print(f"deckCards: {deckCards}")
    print(f"companonCards: {companonCards}")
    print(f"rivalCards: {rivalCards}" )
    for idx, card in enumerate(actionInDetails):
        print(f"action{idx}: {card['cardId']}-{card['entityId']}-{HearthStoneById[card['cardId']]['name']}")
    print(f"cost: {cost}, score: {score}")

def predict(model, requestBody, flags):
    # {
    #     "cardId": "SCH_514",
    #     "attack": 0,
    #     "hp": 0,
    #     "round": 0,
    # }
    position = requestBody.get("position")
    round = requestBody.get("round")
    hero_play = requestBody.get("hero_play", False)
    crystal = requestBody.get("crystal")

    player_hand_cards = requestBody.get('player_hand_cards', [])
    player_deck_cards = requestBody.get('player_deck_cards', [])
    played_actions = requestBody.get('played_actions', [])

    rival_battle_cards = requestBody.get('rival_battle_cards', [])
    companion_battle_cards = requestBody.get('companion_battle_cards', [])
    companion_died = requestBody.get('companion_died', [])

    rivalHeroDetails = requestBody.get('rivalHeroDetails')
    meHeroDetails = requestBody.get('meHeroDetails')

    attack_rival_hero = requestBody.get('attack_rival_hero', 0)
    attack_me_hero = requestBody.get('attack_me_hero', 0)

    secret_size = requestBody.get('secret_size')
    round = min(round, len(played_actions) + 1)
    costDebuff = getCostDebuff(position, round, rival_battle_cards)
    if len(player_deck_cards) == 0:
        _deck = Deck.copy()
        for card in player_hand_cards:
            if card["cardId"] in _deck:
                _deck.remove(card["cardId"])
        for card in [card for action in played_actions for card in action ]:
            if card["cardId"] in _deck:
                _deck.remove(card["cardId"])
            if "races" in HearthStoneById[card["cardId"]] and "PIRATE" in HearthStoneById[card["cardId"]]["races"]:
                if "CFM_637" in _deck:
                    _deck.remove("CFM_637")
        player_deck_cards = _deck
    for card in player_hand_cards:
        card["area"] = "HandArea"
        card["name"] = HearthStoneById[card["cardId"]]["name"]
    for card in companion_battle_cards:
        card["area"] = "PlayArea"
        card["name"] = HearthStoneById[card["cardId"]]["name"]
    for card in rival_battle_cards + [rivalHeroDetails]:
        card["area"] = "PlayArea"
        card["name"] = HearthStoneById[card["cardId"]]["name"]

    coreCards = getCoreCard([card["cardId"] for card in rival_battle_cards + companion_battle_cards] + CardSet)

    info_set = get_infoset(position,
                        hero_play,
                        crystal,
                        player_hand_cards,
                        player_deck_cards,
                        played_actions,
                        companion_battle_cards,
                        costDebuff,
                        companion_died,
                        sum(card["attack"] for card in rival_battle_cards),
                        attack_rival_hero,
                        attack_me_hero,
                    )
    
    # 亡者复生
    succ, response = checkSCH_514(crystal, player_hand_cards, companion_battle_cards, rival_battle_cards,
                                 companion_died,)
    if succ == True:
        printForceAction(round, crystal, info_set, response["force_actions"], 0, 0, rival_battle_cards)
        return response

    _action_idx_pk, force_actions = checkKO(info_set, companion_battle_cards, rival_battle_cards, rivalHeroDetails, player_hand_cards,
                       secret_size,
                       coreCards,
                       )
    print ("CHECK KO FINISH")

    if _action_idx_pk != -1 and len(force_actions) > 0:
        action, cost, score = compete([info_set.all_legal_actions[_action_idx_pk]], info_set, companion_battle_cards, rival_battle_cards, rivalHeroDetails, meHeroDetails, player_deck_cards,
                                    player_hand_cards,
                                    secret_size,
                                    coreCards,
                                    )
        printForceAction(round, crystal, info_set, force_actions, cost, score, rival_battle_cards)
        response = {"status": "succ", "action": [], "cost": cost, "score": score, "crystal": crystal, \
                    "coreCards": getCoreCard([card["cardId"] for card in rival_battle_cards + companion_battle_cards] + CardSet),
                    "powerPlus": getPowerPlus([card["cardId"] for card in companion_battle_cards]),
                    "force_actions": force_actions,
                    "needSurrender": False,
                    }
        return response
    
    _action_idx_pk, force_actions = cleanTaunt(round, info_set, companion_battle_cards, rival_battle_cards, player_hand_cards,
                    coreCards,
                    rivalHeroDetails,
                    )
    print ("CHECK Taunt FINISH")
    if _action_idx_pk != -1 and len(force_actions) > 0:
        action, cost, score = compete([info_set.all_legal_actions[_action_idx_pk]], info_set, companion_battle_cards, rival_battle_cards, rivalHeroDetails, meHeroDetails, player_deck_cards,
                                    player_hand_cards,
                                    secret_size,
                                    coreCards,
                                    )
        printForceAction(round, crystal, info_set, force_actions, cost, score, rival_battle_cards)
        response = {"status": "succ", "action": [], "cost": cost, "score": score, "crystal": crystal, \
                    "coreCards": getCoreCard([card["cardId"] for card in rival_battle_cards + companion_battle_cards] + CardSet),
                    "powerPlus": getPowerPlus([card["cardId"] for card in companion_battle_cards]),
                    "force_actions": force_actions,
                    "needSurrender": checkSurrender(rivalHeroDetails, round),
                    }
        return response

    # if crystal == 0:
    #     response = {"status": "succ", "action": [], "cost": 0, "score": 0, "crystal": crystal, \
    #         "coreCards": getCoreCard([card["cardId"] for card in rival_battle_cards + companion_battle_cards] + CardSet),
    #         "powerPlus": getPowerPlus([card["cardId"] for card in companion_battle_cards]),
    #         "force_actions": [],
    #         }
    #     return response

    player_hand_cards, hero_play = patch(hero_play, player_hand_cards, rival_battle_cards, companion_battle_cards, 
                              getCoreCard([card["cardId"] for card in rival_battle_cards + companion_battle_cards] + CardSet),
                              rivalHeroDetails)

    # 暮光欺诈者 TODO MYWEN
    succ, response = checkSW_444(round, crystal, player_hand_cards, companion_battle_cards, rival_battle_cards, attack_rival_hero, attack_me_hero,
                                 rivalHeroDetails, meHeroDetails)
    if succ == True:
        printForceAction(round, crystal, info_set, response["force_actions"], 0, 0, rival_battle_cards)
        return response

    info_set = get_infoset(position,
                           hero_play,
                           crystal,
                           player_hand_cards,
                           player_deck_cards,
                           played_actions,
                            companion_battle_cards,
                            costDebuff,
                            companion_died,
                            sum(card["attack"] for card in rival_battle_cards),
                            attack_rival_hero,
                            attack_me_hero,
                        )
    obs = get_obs(convertInfoset(deepcopy(info_set)))

    device = getDevice(deviceName=flags.training_device)
    obs_x = torch.from_numpy(obs['x_batch']).to(device)
    obs_z = torch.from_numpy(obs['z_batch']).to(device)
    with torch.no_grad():
        agent_output = model.forward(position, obs_z, obs_x, topk=3)
    _action_idx = agent_output['action'].cpu().detach().numpy().tolist()
    _action_idx_pk = getMockActionIndex(info_set, companion_battle_cards, player_deck_cards, 
                                                           player_hand_cards)

    _action_idx.extend([_action_idx_pk])
    actionInDetails, cost, score = compete([info_set.all_legal_actions[idx] for idx in _action_idx], info_set, companion_battle_cards, rival_battle_cards, rivalHeroDetails, meHeroDetails, player_deck_cards,
                                  player_hand_cards,
                                  secret_size,
                                  coreCards,
                                  )
    
    printAction(round, crystal, info_set, actionInDetails, cost, score, rival_battle_cards)

    response = {"status": "succ", "action": filter(actionInDetails), "cost": cost, "score": score, "crystal": crystal, \
                "coreCards": getCoreCard([card["cardId"] for card in rival_battle_cards + companion_battle_cards] + CardSet),
                "powerPlus": getPowerPlus([card["cardId"] for card in companion_battle_cards]),
                "force_actions": [],
                "needSurrender": checkSurrender(rivalHeroDetails, round),
                }
    return response

def checkSurrender(rivalHeroDetails, round):
    if round >= 8 and rivalHeroDetails["hp"] >= 10:
        return True
    else:
        return False

def annotationManually(action, handCard):
    if len([card for card in handCard if card in [
            # 宝藏经销商
            'TOY_518',
            # 随船外科医师
            'CORE_WON_065',
        ]]) > 0:

        if len([card for card in action if card in [
            # 宝藏经销商
            'TOY_518',
            # 随船外科医师
            'CORE_WON_065',
        ]]) > 0:
            return 0
        else:
            return -10
    elif len([card for card in handCard if card in [
            # 心灵按摩师
            'VAC_512',
        ]]) > 0:
        
        if len([card for card in action if card in [
                # 心灵按摩师
                'VAC_512',
            ]]) > 0:
            return 0
        else:
            return -5
    elif len([card for card in action if card in [
        # 幸运币
        'GAME_005', 
        ]]) > 0:
            return -5
    else:
        return 0