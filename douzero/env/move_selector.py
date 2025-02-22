# return all moves that can beat rivals, moves and rival_move should be same type
import collections
import random

def calculateCardCost(move, card, HearthStoneById, Deck, companion_on_battlefield,
                    attack_rival_hero,
                    ):
    count14 = len([card for card in companion_on_battlefield if Deck[card] == "TOY_381"]) \
        + len([card for card in move if Deck[card] == "TOY_381"]) # 纸艺天使
    countPirate = len([card for card in move if Deck[card] != "DRG_056" and \
                       "races" in HearthStoneById[Deck[card]] and "PIRATE" in HearthStoneById[Deck[card]]["races"]]
                       ) # 海盗
    pirateDRG_056 = [card for card in move if Deck[card] == "DRG_056"] # 空降歹徒
    
    cardId = Deck[card]
    if cardId == "YOD_032": # 艾狂暴邪翼
        return max(0, HearthStoneById[cardId]["cost"] - attack_rival_hero)
    elif cardId == "EX1_625t" and count14 > 0: # 英雄技能, 心灵尖刺
        return 0
    elif cardId == "DRG_056": # 空降歹徒
        if countPirate > 0:
            return 0
        elif len(pirateDRG_056) >= 2 and card != pirateDRG_056[-1]:
            return 0
        else:
             return HearthStoneById[cardId]["cost"]
    else:
        return HearthStoneById[cardId]["cost"]

def calculateActionCost(move, HearthStoneById, Deck, companion_on_battlefield,
                        attack_rival_hero,
                        player_deck_cards,
                        ):
    cost = 0
    minion = len(companion_on_battlefield)
    # MYWEN
    pirate_count = len([ idx for idx, card in enumerate(move) if "races" in HearthStoneById[Deck[card]] and "PIRATE" in HearthStoneById[Deck[card]]["races"] ])
    if pirate_count > 0 and 24 in player_deck_cards:
        minion += 1

    for card in move:
        cardId = Deck[card]
        if HearthStoneById[cardId]["type"] == "MINION" or HearthStoneById[cardId]["type"] == "LOCATION":
            minion += 1
        cost += calculateCardCost(move, card, HearthStoneById, Deck, companion_on_battlefield,
                        attack_rival_hero,
                        )
    return cost, minion

def filter_hearth_stone(moves, crystal, HearthStoneById, Deck,
                    companion_on_battlefield,
                    companion_died,
                    attack_rival_hero,
                    player_deck_cards,
                        CardSet=None):
    legal_moves = []
    assert len(moves) == len(attack_rival_hero)
    assert len(moves) > 0
    # print (moves)
    importantMinion = [card for card in companion_died if Deck[card] in ["TOY_518", "TOY_381", "CORE_WON_065", "SW_446"]] #宝藏经销商   纸艺天使    随船外科医师      虚触侍从
    for index, move in enumerate(moves):
        # 处理亡者复生
        if (0 in move or 1 in move) \
            and len(importantMinion) == 0 \
                and  len(companion_died) < 2:
            continue
        cost, minion = calculateActionCost(move, HearthStoneById, Deck, companion_on_battlefield,
                                            attack_rival_hero[index],
                                            player_deck_cards,
                                           )
        coin = len([ card for card in move if Deck[card] == "GAME_005" ])
        if cost <= crystal + coin and minion <= 7:
            legal_moves.extend([playCardsWithOrder(move, crystal, HearthStoneById, Deck, companion_on_battlefield,
                    attack_rival_hero[index],
                                )])
    return legal_moves

def playCardsWithOrder(action, crystal, HearthStoneById, Deck, companion_on_battlefield,
                    attack_rival_hero,
                       ):
    playList = [ # MYWEN play order
        "GAME_005", # coin
        "REV_290", # # 赎罪教堂
        "TOY_518", # 宝藏经销商
        "CORE_WON_065", # 随船外科医师
        'SW_446', # 虚触侍从
        "TOY_381", # 纸艺天使
        "HERO_POWER", # 心灵尖刺
        "SW_444", # 暮光欺诈者 # MYWEN 先放在打
        'VAC_512', # 心灵按摩师
        'CFM_637', # 海盗帕奇斯
        "DRG_056", # 空降歹徒
        "MINION",
        "SPELL",
        "YOD_032", # 艾狂暴邪翼
    ]
    
    playOrder = {value: index for index, value in enumerate(playList)}
    
    sorted_cards = sorted(action, key=lambda card: playOrder[Deck[card]] if Deck[card] in playOrder else playOrder[HearthStoneById[Deck[card]]["type"]])
    
    # if 0 in action and 4 in action and 16 in action and crystal >= 4:
    #     print ("DEBUG start", sorted_cards)
    cost = 0
    coin = 0
    cardsWithOrder = []
    for card in sorted_cards:
        cost += calculateCardCost(sorted_cards, card, HearthStoneById, Deck, companion_on_battlefield,
                    attack_rival_hero,
                    )
        while cost > crystal and coin > 0:
            coin -= 1
            crystal += 1
            cardsWithOrder.extend([0]) # add coin
        if card == 0: # coin
            coin += 1
        else:
            cardsWithOrder.extend([card])
            
    if coin > 0:
        cardsWithOrder.extend([0] * coin)
    # if 0 in action and 4 in action and 16 in action and crystal >= 4:
    #     print ("DEBUG end", cardsWithOrder)
    return cardsWithOrder

def attackRivalHero():
    return 0

def attackMeHero():
    return 0

# def calculateScore(action, HearthStone,
#                     companion_on_battlefield,
#                     companion_died,
#                     player_deck_cards,
#                     attack_rival_hero,
#                     attack_me_hero,
#                     hands_num):

#     score = 0
#     for card in action:
#         cardId = HearthStone[card]["id"]
#         score += HearthStone[card]["cost"]

#     # 海盗 attack+1
#     pirate_attack_plus_count = len([card for card in companion_on_battlefield if HearthStone[card]["id"] == "TOY_518"]) # 宝藏经销商
#     for card in action:
#         cardId = HearthStone[card]["id"]
#         races = HearthStone[card]["races"]
#         if "PIRATE" in races:
#             score += pirate_attack_plus_count
#         if cardId == "TOY_518":
#             pirate_attack_plus_count += 1

#     # 随从 hp+1
#     minion_hp_plus_count = len([card for card in companion_on_battlefield if HearthStone[card]["id"] == "CORE_WON_065"]) # 随船外科医师
#     for card in action:
#         cardId = HearthStone[card]["id"]
#         type = HearthStone[card]["type"]
#         if "MINION" == type:
#             score += minion_hp_plus_count
#         if cardId == "CORE_WON_065":
#             minion_hp_plus_count += 1

#     # MYWEN todo 肥婆

#     # 过牌
#     hands_num_tmp = hands_num
#     SHADOW_count = len([deckCard for deckCard in player_deck_cards if HearthStone[deckCard]["spellSchool"] == "SHADOW" and HearthStone[deckCard]["type"] == "SPELL"])
#     for card in action:
#         cardId = HearthStone[card]["id"]
#         hands_num_tmp -= 1
#         if cardId == "SCH_514": # 亡者复生
#             newCard = min(10 - hands_num_tmp, companion_died, 2)
#             hands_num_tmp += newCard
#             score += newCard
#         if cardId == "SW_444" and (attack_me_hero > 0 or attack_rival_hero > 0): # 暮光欺诈者
#              newCard = min(10 - hands_num_tmp, SHADOW_count, 1)
#              hands_num_tmp += newCard
#              SHADOW_count -= newCard
#              score += newCard
#     return score

# {
#     "cardId": "SW_446",
#     "hp": 3,
#     "attack": 3
# }
def calculateAttack(action, HearthStoneById, Deck,
                    companion_on_battlefield_details,
                    ): # MYWEN

    attack = 0

    # 伤害加成
    SW_446_Count = len([cardDetails for cardDetails in companion_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从
    SW_446_Count += len([card for card in action if HearthStoneById[Deck[card]]['id'] == "SW_446"]) # 虚触侍从

    # 随从伤害
    for cardDetails in companion_on_battlefield_details:
        attack += cardDetails["attack"] + SW_446_Count
    
    # 法术伤害
    for card in action:
        cardId = Deck[card]
        if cardId == "NX2_019": # 精神灼烧 MYWEN todo 不一定能打出3点伤害
            attack += 3 + SW_446_Count
        elif cardId == "VAC_419": # 针灸
            attack += 4 + SW_446_Count
        elif cardId == "DS1_233": # 心灵震爆
            attack += 5 + SW_446_Count

    # 英雄技能
    for card in action:
        cardId = Deck[card]
        if cardId == "EX1_625t": # 心灵尖刺
            attack += 2 + SW_446_Count

    # 战吼伤害
    for card in action:
        cardId = Deck[card]
        if cardId == "GVG_009": # 暗影投弹手
            attack += 3 + SW_446_Count
    return attack

def calculateAttackNextRound(companion_on_battlefield_details):

    attack = 0

    # 伤害加成
    SW_446_Count = len([cardDetails for cardDetails in companion_on_battlefield_details if cardDetails["cardId"] == "SW_446"]) # 虚触侍从

    # 随从伤害
    for cardDetails in companion_on_battlefield_details:
        attack += cardDetails["attack"] + SW_446_Count

    return attack

def calculateHPNextRound(companion_on_battlefield_details):
    hp = 0
    # 随从伤害
    for cardDetails in companion_on_battlefield_details:
        if cardDetails["cardId"] != "REV_290": # 赎罪教堂
            hp += cardDetails["hp"]
    return hp

def newCards(played_card, HearthStoneById, Deck,
                companion_died,
                attack_rival_hero,
                attack_me_hero,
                player_deck_cards,
                player_hand_cards,
                buff,
                round,
                ): # todo MYWEN 赎罪教堂
    lastCard = played_card[-1]

    # 过牌
    cardId = Deck[lastCard]
    if cardId == "SCH_514" and companion_died != None: # 亡者复生
        newCard = min(10 - len(player_hand_cards), len(companion_died), 2)
        if newCard > 0:
            random_values = random.sample(companion_died, newCard)
            player_hand_cards.extend(random_values)
    if cardId == "SW_444" and (attack_me_hero > 0 or attack_rival_hero > 0): # 暮光欺诈者
        SHADOW_spell = [card for card in player_deck_cards if HearthStoneById[Deck[card]]["type"] == "SPELL" and "spellSchool" in HearthStoneById[Deck[card]] and HearthStoneById[Deck[card]]["spellSchool"] == "SHADOW"] # MYWEN todo
        newCard = min(10 - len(player_hand_cards), len(SHADOW_spell), 1)
        if newCard > 0:
            random_values = random.sample(SHADOW_spell, newCard)
            player_hand_cards.extend(random_values)
            player_deck_cards.remove(random_values[0])

    if cardId == "REV_290" and buff[lastCard]["round"] == round and len(player_deck_cards) > 0:
        newCard = player_deck_cards[0]
        player_hand_cards.extend([newCard])
        player_deck_cards.remove(newCard)