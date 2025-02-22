# return all moves that can beat rivals, moves and rival_move should be same type
import collections
import random

def calculateCardCost(move, cardId, HearthStoneById, companion_on_battlefield,
                    attack_rival_hero,
                    ):
    count14 = len([card for card in companion_on_battlefield if card == "TOY_381"]) \
        + len([card for card in move if card == "TOY_381"]) # 纸艺天使
    countPirate = len([card for card in move if card != "DRG_056" and \
                       "races" in HearthStoneById[card] and "PIRATE" in HearthStoneById[card]["races"]]
                       ) # 海盗
    pirateDRG_056 = [card for card in move if card == "DRG_056"] # 空降歹徒
    
    if cardId == "YOD_032": # 艾狂暴邪翼
        return max(0, HearthStoneById[cardId]["cost"] - attack_rival_hero)
    elif cardId == "EX1_625t" and count14 > 0: # 英雄技能, 心灵尖刺
        return 0
    elif cardId == "DRG_056": # 空降歹徒
        if countPirate > 0:
            return 0
        elif len(pirateDRG_056) >= 2:
            return 1
        else:
             return HearthStoneById[cardId]["cost"]
    else:
        return HearthStoneById[cardId]["cost"]

def calculateActionCost(move, HearthStoneById, companion_on_battlefield,
                        attack_rival_hero,
                        player_deck_cards,
                        ):
    cost = 0
    minion = len(companion_on_battlefield)
    pirate_count = len([ idx for idx, card in enumerate(move) if "races" in HearthStoneById[card] and "PIRATE" in HearthStoneById[card]["races"] ])
    if pirate_count > 0 and "CFM_637" in player_deck_cards:
        minion += 1

    for card in move:
        cardId = card
        if HearthStoneById[cardId]["type"] == "MINION" or HearthStoneById[cardId]["type"] == "LOCATION":
            minion += 1
        cost += calculateCardCost(move, card, HearthStoneById, companion_on_battlefield,
                        attack_rival_hero,
                        )
    return cost, minion

def calculateCardInDetailsCost(move_in_details, card_in_details, HearthStoneById, companion_on_battlefield,
                    attack_rival_hero,
                    costDebuff,
                    ):
    move = [card["cardId"] for card in move_in_details]
    count14 = len([card for card in companion_on_battlefield if card == "TOY_381"]) \
        + len([card for card in move if card == "TOY_381"]) # 纸艺天使
    countPirate = len([card for card in move if card != "DRG_056" and \
                       "races" in HearthStoneById[card] and "PIRATE" in HearthStoneById[card]["races"]]
                       ) # 海盗
    pirateDRG_056 = [card for card in move if card == "DRG_056"] # 空降歹徒
    cardId = card_in_details["cardId"]
    cardCost = card_in_details.get("cost", 0)
    cardType = HearthStoneById[cardId]["type"]
    if cardId == "YOD_032": # 艾狂暴邪翼
        return max(0, cardCost - attack_rival_hero, HearthStoneById[cardId]["cost"] + costDebuff["round"]["MINION"] - attack_rival_hero)
    elif cardId == "EX1_625t" and count14 > 0: # 英雄技能, 心灵尖刺
        return 0
    elif cardId == "DRG_056": # 空降歹徒
        cardCost = max(cardCost, HearthStoneById[cardId]["cost"] + costDebuff["round"]["MINION"])
        if countPirate > 0:
            return 0
        elif len(pirateDRG_056) >= 2:
            return cardCost / 2
        else:
             return cardCost
    else:
        return max(cardCost, HearthStoneById[cardId]["cost"] + costDebuff["round"][cardType])

def calculateActionDetailsCost(move_in_details, HearthStoneById, companion_on_battlefield,
                        attack_rival_hero,
                        player_deck_cards,
                        costDebuff,
                        ):
    cost = 0
    minion = len(companion_on_battlefield)
    move = [card["cardId"] for card in move_in_details]
    pirate_count = len([ idx for idx, card in enumerate(move) if "races" in HearthStoneById[card] and "PIRATE" in HearthStoneById[card]["races"] ])
    if pirate_count > 0 and "CFM_637" in player_deck_cards:
        minion += 1

    for card in move_in_details:
        cardId = card["cardId"]
        if HearthStoneById[cardId]["type"] == "MINION" or HearthStoneById[cardId]["type"] == "LOCATION":
            minion += 1
        cost += calculateCardInDetailsCost(move_in_details, card, HearthStoneById, companion_on_battlefield,
                        attack_rival_hero,
                        costDebuff,
                        )
    return cost, minion

def filter_hearth_stone(moves_in_details, crystal, HearthStoneById,
                    companion_on_battlefield_details,
                    costDebuff,
                    companion_died,
                    attack_rival_hero,
                    attack_me_hero,
                    player_deck_cards,
                    player_hand_cards,
                        CardSet=None):
    legal_moves = []
    assert len(moves_in_details) > 0
    # print (moves)
    importantMinion = [card for card in companion_died if card in ["TOY_518", "TOY_381", "CORE_WON_065", "SW_446"]] #宝藏经销商   纸艺天使    随船外科医师      虚触侍从
    companion_on_battlefield = [cardDetail["cardId"] for cardDetail in companion_on_battlefield_details]
    # print ("MYWEN", costDebuff)
    countDRG_056 = len([card for card in player_hand_cards if card["cardId"] == "DRG_056"])
    for index, move_in_details in enumerate(moves_in_details):
        # 处理亡者复生
        move = [card["cardId"] for card in move_in_details]
        if ("SCH_514" in move) \
            and len(importantMinion) == 0 \
                and  len(companion_died) < 2:
            continue
        # 处理空降歹徒
        pirate_count = len([ idx for idx, card in enumerate(move) if "races" in HearthStoneById[card] and "PIRATE" in HearthStoneById[card]["races"] ])
        current_countDRG_056 = len([card for card in move_in_details if card["cardId"] == "DRG_056"])
        if pirate_count > 0 and current_countDRG_056 != countDRG_056: # any pirate will drop all DRG_056
            continue

        actionAttack = calculateActionAttack(move, companion_on_battlefield_details, HearthStoneById)
        if attack_rival_hero + actionAttack == 0 and attack_me_hero == 0 and "SW_444" in move: # 暮光欺诈者
            continue
        
        cost, minion = calculateActionDetailsCost(move_in_details, HearthStoneById, companion_on_battlefield,
                                            attack_rival_hero + actionAttack,
                                            player_deck_cards,
                                            costDebuff,
                                           )
        coin = len([ card for card in move if card == "GAME_005" ])
        if cost <= crystal + coin and minion <= 7:
            legal_moves.extend([playCardsWithOrder(move_in_details, crystal, HearthStoneById, companion_on_battlefield,
                    attack_rival_hero,
                    attack_me_hero,
                                )])
    return legal_moves

def playCardsWithOrder(action_in_details, crystal, HearthStoneById, companion_on_battlefield,
                    attack_rival_hero,
                    attack_me_hero,
                       ):
    playList = [ # MYWEN play order
        "GAME_005", # coin
        "SCH_514", # 亡者复生
        "REV_290", # 赎罪教堂
        "TOY_518", # 宝藏经销商
        "CORE_WON_065", # 随船外科医师
        'SW_446', # 虚触侍从
        "TOY_381", # 纸艺天使
        "HERO_POWER", # 心灵尖刺
        # "SW_444", # 暮光欺诈者
        'VAC_512', # 心灵按摩师
        'CFM_637', # 海盗帕奇斯
        "DRG_056", # 空降歹徒
        "MINION",
        "SPELL",
        "NX2_019",
        "YOD_032", # 艾狂暴邪翼
    ]
    
    playOrder = {value: index for index, value in enumerate(playList)}
    if attack_rival_hero > 0 or attack_me_hero > 0 or len([card for card in action_in_details if card["cardId"] == "SCH_514"]) > 0:
        playOrder["SW_444"] = 1.2
    else:
        playOrder["SW_444"] = len(playList)

    for private in ["TOY_518", "CORE_WON_065", "VAC_512", "CFM_637"]:
        if len([card for card in action_in_details if card["cardId"] == private]) > 0:
            playOrder["DRG_056"] = playOrder[private] + 0.2
            break;
    sorted_cards = sorted(action_in_details, key=lambda card: (playOrder[card["cardId"]], card["cardId"]) if card["cardId"]  in playOrder else (playOrder[HearthStoneById[card["cardId"]]["type"]], card["cardId"]))
    
    # if 0 in action and 4 in action and 16 in action and crystal >= 4:
    #     print ("DEBUG start", sorted_cards)
    # cost = 0
    # coin = 0
    # cardsWithOrder = []
    # coinList = []
    # for card in sorted_cards:
    #     cost += calculateActionDetailsCost(sorted_cards, card, HearthStoneById, companion_on_battlefield,
    #                 attack_rival_hero,
    #                 )
    #     while cost > crystal and coin > 0:
    #         coin -= 1
    #         crystal += 1
    #         cardsWithOrder.extend(["GAME_005"]) # add coin
    #     if card["cardId"] == "GAME_005": # coin
    #         coin += 1
    #     else:
    #         cardsWithOrder.extend([card])
            
    # if coin > 0:
    #     cardsWithOrder.extend(["GAME_005"] * coin)
    # if 0 in action and 4 in action and 16 in action and crystal >= 4:
    #     print ("DEBUG end", cardsWithOrder)
    return sorted_cards

# {
#     "cardId": "SW_446",
#     "hp": 3,
#     "attack": 3
# }
def calculateAttack(action,
                    companion_on_battlefield_details,
                    HearthStoneById,
                    ): # MYWEN

    attack = 0

    # 伤害加成
    SW_446_Count = len([cardDetails for cardDetails in companion_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从
    SW_446_Count += len([card for card in action if card == "SW_446"]) # 虚触侍从

    # 随从伤害
    for cardDetails in companion_on_battlefield_details:
        if cardDetails["isActive"] == True and cardDetails["cardId"] != "REV_290": # 赎罪教堂:
            attack += cardDetails["attack"] + SW_446_Count

    return attack + calculateActionAttack(action, companion_on_battlefield_details, HearthStoneById)

def calculateActionAttack(action,
                    companion_on_battlefield_details,
                    HearthStoneById,
                    ): # MYWEN

    attack = 0

    # 伤害加成
    SW_446_Count = len([cardDetails for cardDetails in companion_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从
    SW_446_Count += len([card for card in action if card == "SW_446"]) # 虚触侍从
    
    # 法术伤害
    for card in action:
        cardId = card
        if cardId == "NX2_019": # 精神灼烧 MYWEN todo 不一定能打出3点伤害
            attack += 3 + SW_446_Count
        elif cardId == "VAC_419": # 针灸
            attack += 4 + SW_446_Count
        elif cardId == "DS1_233": # 心灵震爆
            attack += 5 + SW_446_Count

    # 英雄技能
    for card in action:
        cardId = card
        if cardId == "EX1_625t": # 心灵尖刺
            attack += 2 + SW_446_Count

    # 战吼伤害
    for card in action:
        cardId = card
        if HearthStoneById[cardId]["name"] == "暗影投弹手": # 暗影投弹手
            attack += 3 + SW_446_Count
    return attack

def calculateAttackNextRound(companion_on_battlefield_details):

    attack = 0

    # 伤害加成
    SW_446_Count = len([cardDetails for cardDetails in companion_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从

    # 随从伤害
    for cardDetails in companion_on_battlefield_details:
        if cardDetails["cardId"] != "REV_290": # 赎罪教堂
            attack += cardDetails["attack"] + SW_446_Count

    return attack

def calculateHPNextRound(companion_on_battlefield_details):
    hp = 0
    # 随从伤害
    for cardDetails in companion_on_battlefield_details:
        if cardDetails["cardId"] != "REV_290": # 赎罪教堂
            hp += cardDetails["hp"]
    return hp


def checkTaunt(cardDetails, HearthStoneById):
    if "isTaunt" in cardDetails["card"]:
        return cardDetails["card"]["isTaunt"]
    if ("text" in HearthStoneById[cardDetails["cardId"]] and "嘲讽" in HearthStoneById[cardDetails["cardId"]]["text"] and \
            HearthStoneById[cardDetails["cardId"]]["text"].startswith("<b>嘲讽")
            ):
        return True
    else :
        return False

def checkHealthSteal(cardDetails, HearthStoneById):
    if "isLifesteal" in cardDetails["card"]:
        return cardDetails["card"]["isLifesteal"]
    if ("text" in HearthStoneById[cardDetails["cardId"]] and "吸血" in HearthStoneById[cardDetails["cardId"]]["text"]):
        return True
    else :
        return False

def getHeroTypes():
        #   死亡骑士        猎人      德鲁伊    法师    圣骑士      牧师       潜行者   萨满       术士       战士       恶魔猎手
    return ["DEATHKNIGHT", "HUNTER", "DRUID", "MAGE", "PALADIN", "PRIEST", "ROGUE", "SHAMAN", "WARLOCK", "WARRIOR", "DEMONHUNTER"]

def calculateKO(action,
                    companion_on_battlefield_details,
                    rival_on_battlefield_details,
                    rival_hero,
                    secret_size,
                    HearthStoneById,
                    ):
    if secret_size > 0 and HearthStoneById[rival_hero["cardId"]]["cardClass"] in ["HUNTER", "MAGE"]:
        return False

    if rival_hero["isActive"] == False:
        return False

    tauntSize =  len([card for card in rival_on_battlefield_details if checkTaunt(card, HearthStoneById)])

    is_divine_shield = rival_hero["card"].get("isDivineShield", False)

    # MYWEN todo 手牌中的随从
    lessHPMinion = len([card for card in rival_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] != "SW_446"]) + \
        len([card for card in companion_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] != "SW_446"])

    lessHPMinionSW446 = len([card for card in rival_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] == "SW_446"]) + \
        len([card for card in companion_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] == "SW_446"])

    # print (f"lessHPMinion: {lessHPMinion}, lessHPMinionSW446: {lessHPMinionSW446}")
    if len([card for card in action if card == "NX2_019"]) > lessHPMinion + lessHPMinionSW446:
        return False

    attack = 0

    # 伤害加成
    SW_446_Count = len([cardDetails for cardDetails in companion_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从
    SW_446_Count += len([card for card in action if card == "SW_446"]) # 虚触侍从
    SW_446_Count += len([cardDetails for cardDetails in rival_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从

    # 随从伤害
    locationCount = len([card for card in companion_on_battlefield_details if card["cardId"] == "REV_290" and card["isActive"] == True]) + \
        len([card for card in action if card == "REV_290"])
    if tauntSize == 0: # 回合开始
        for idx, cardDetails in enumerate(companion_on_battlefield_details):
            if HearthStoneById[cardDetails["cardId"]]["type"] == "MINION" and cardDetails["isActive"] == True:
                if is_divine_shield == True:
                    is_divine_shield = False
                else:
                    attack += cardDetails["attack"] + SW_446_Count
                    if idx == len(companion_on_battlefield_details) - 1:
                        attack += 2 * locationCount

    # print ("MINION", attack)
    # 英雄技能
    for card in action:
        cardId = card
        if cardId == "EX1_625t": # 心灵尖刺
            if is_divine_shield:
                is_divine_shield = False
            else:
                attack += 2 + SW_446_Count
    # print ("英雄技能", attack)
    # 法术伤害
    SW_446_Died = 0
    for card in action:
        cardId = card
        if cardId == "NX2_019": # 精神灼烧 MYWEN todo 不一定能打出3点伤害
            if lessHPMinion > 0:
                if is_divine_shield:
                    is_divine_shield = False
                else:
                    attack += 3 + SW_446_Count
                lessHPMinion -= 1
            elif lessHPMinionSW446 > 0:
                SW_446_Died += 1
                if is_divine_shield:
                    is_divine_shield = False
                else:
                    attack += 3 + SW_446_Count - SW_446_Died
                lessHPMinionSW446 -= 1
        elif cardId == "VAC_419": # 针灸
            if is_divine_shield:
                is_divine_shield = False
            else:
                attack += 4 + SW_446_Count
        elif cardId == "DS1_233": # 心灵震爆
            if is_divine_shield:
                is_divine_shield = False
            else:
                attack += 5 + SW_446_Count
    # print ("法术伤害", attack)
    # 战吼伤害
    for card in action:
        cardId = card
        if HearthStoneById[cardId]["name"] == "暗影投弹手": # 暗影投弹手
            if is_divine_shield:
                is_divine_shield = False
            else:
                attack += 3 + SW_446_Count
    # print ("战吼伤害", attack)
    if attack >= rival_hero["hp"]:
        print ("Simple KO", action, attack, rival_hero["hp"])
        return True
    else:
        return False

# def calculateDirectAttack(reval_hero, action,
#                     companion_on_battlefield_details,
#                     rival_on_battlefield_details,
#                     ):
#     attack = 0

#     # 伤害加成
#     SW_446_Count = len([cardDetails for cardDetails in companion_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从
#     SW_446_Count += len([card for card in action if card == "SW_446"]) # 虚触侍从
#     SW_446_Count += len([cardDetails for cardDetails in rival_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从
#     is_divine_shield = reval_hero["card"].get("isDivineShield", False)
#     # 法术伤害
#     for card in action:
#         cardId = card
#         if cardId == "VAC_419": # 针灸
#             if is_divine_shield:
#                 is_divine_shield = False
#             else:
#                 attack += 4 + SW_446_Count
#         elif cardId == "DS1_233": # 心灵震爆
#             if is_divine_shield:
#                 is_divine_shield = False
#             else:
#                 attack += 5 + SW_446_Count

#     # 战吼伤害
#     for card in action:
#         cardId = card
#         if cardId == "GVG_009": # 暗影投弹手
#             if is_divine_shield:
#                 is_divine_shield = False
#             else:
#                 attack += 3 + SW_446_Count
#     return attack, is_divine_shield

# def genereateAttackActionForKO(actionInDetails, companion_on_battlefield_details, rival_on_battlefield_details, rival_hero, me_hero, coreCards,
#                                HearthStoneById,
#                                ):
#     attackAction = []
#     for companion in companion_on_battlefield_details:
#         attackAction.extend([
#             {
#                 "companion": companion,
#                 "rival": rival_hero
#             }
#         ])
    
#     activateCompanion = [card for card in companion_on_battlefield_details if HearthStoneById[card["cardId"]]["type"] == "MINION" and card["isActive"] == True]

#     # MYWEN todo NX2_019
#     lessHPMinion = len([card for card in rival_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] != "SW_446"]) == 0 + \
#         len([card for card in companion_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] != "SW_446" and card["isActive"] == False])
#     lessHPMinionIndex = 0
#     lessHPMinionSW446 = len([card for card in rival_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] == "SW_446"]) == 0 + \
#         len([card for card in companion_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] == "SW_446" and card["isActive"] == False])
#     lessHPMinionSW664Index = 0

#     for card in actionInDetails:
#         if card["cardId"] == "REV_290" and len(activateCompanion):
#             attackAction.extend([
#                 {
#                     "companion": card,
#                     "rival": activateCompanion[0]
#                 }
#             ])
#         if card["cardId"] == "NX2_019":
#             if lessHPMinionIndex < len(lessHPMinion):
#                 attackAction.extend([
#                     {
#                         "companion": card,
#                         "rival": lessHPMinion[lessHPMinionIndex]
#                     }
#                 ])
#                 lessHPMinionIndex += 1
#             if lessHPMinionSW664Index < len(lessHPMinionSW446):
#                 attackAction.extend([
#                     {
#                         "companion": card,
#                         "rival": lessHPMinionSW446[lessHPMinionSW664Index]
#                     }
#                 ])
#                 lessHPMinionSW664Index += 1

#     return attackAction

# def genereateAttackAction(action, companion_on_battlefield_details, rival_on_battlefield_details, rival_hero, me_hero, coreCards, HearthStoneById,
#                                ):
#     attackAction = []
#     for companion in companion_on_battlefield_details:
#         attackAction.extend([
#             {
#                 "companion": companion,
#                 "rival": rival_hero
#             }
#         ])
    
#     activateCompanion = [card for card in companion_on_battlefield_details if HearthStoneById[card["cardId"]]["type"] == "MINION" and card["isActive"] == True]

#     # MYWEN todo NX2_019
#     lessHPMinion = len([card for card in rival_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] != "SW_446"]) == 0 + \
#         len([card for card in companion_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] != "SW_446" and card["isActive"] == False])
#     lessHPMinionIndex = 0
#     lessHPMinionSW446 = len([card for card in rival_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] == "SW_446"]) == 0 + \
#         len([card for card in companion_on_battlefield_details if card["hp"] <= 2 and HearthStoneById[card["cardId"]]["type"] == "MINION" and card["cardId"] == "SW_446" and card["isActive"] == False])
#     lessHPMinionSW664Index = 0

#     for card in action:
#         if card["cardId"] == "REV_290" and len(activateCompanion):
#             attackAction.extend([
#                 {
#                     "companion": card,
#                     "rival": activateCompanion[0]
#                 }
#             ])
#         if card["cardId"] == "NX2_019":
#             if lessHPMinionIndex < len(lessHPMinion):
#                 attackAction.extend([
#                     {
#                         "companion": card,
#                         "rival": lessHPMinion[lessHPMinionIndex]
#                     }
#                 ])
#                 lessHPMinionIndex += 1
#             if lessHPMinionSW664Index < len(lessHPMinionSW446):
#                 attackAction.extend([
#                     {
#                         "companion": card,
#                         "rival": lessHPMinionSW446[lessHPMinionSW664Index]
#                     }
#                 ])
#                 lessHPMinionSW664Index += 1

#     return attackAction