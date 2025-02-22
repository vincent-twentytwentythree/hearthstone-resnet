from copy import deepcopy
from . import move_detector as md, move_selector as ms
from .move_generator import MovesGener
import json
import random
import numpy as np

CardTypeToIndex = {
    "SPELL": 0,
    "SPELL_HERO_POWER": 1,
    "MINION": 2,
}
        
CardSet = [ # size of 21
    # 0: 0 - 1
    # 幸运币
    'GAME_005', 
    # 亡者复生
    'SCH_514',
    
    # 1: 2 - 9
    # 宝藏经销商
    'TOY_518', 

    # 心灵按摩师
    'VAC_512',

    # 暗影投弹手
    'GVG_009',

    # 海盗帕奇斯
    'CFM_637',
    # 精神灼烧
    'NX2_019',
    # 虚触侍从
    'SW_446', 
    # 针灸
    'VAC_419',
    # 随船外科医师
    'CORE_WON_065',

    # 2: 10 - 15
    # 异教低阶牧师
    'CORE_SCH_713',
    # 心灵震爆
    'DS1_233',
    # 暮光欺诈者
    'SW_444',
    # 空降歹徒
    'DRG_056',
    # 纸艺天使
    'TOY_381',
    # 迪菲亚麻风侏儒
    'DED_513',

    # 3: 16 - 17
    # 赎罪教堂
    'REV_290',
    # 虚灵神谕者
    'GDB_310',

    # 4: 18
    # 艾狂暴邪翼
    'YOD_032', 

    # 5: 19
    # 黑暗主教本尼迪塔斯
    'SW_448',

    # 英雄技能: 20
    # 心灵尖刺
    'EX1_625t',
]

RealCard2EnvCard = {key: index for index, key in enumerate(CardSet)}
EnvCard2RealCard = {value: key for key, value in RealCard2EnvCard.items()}

FullCardSet = [] + CardSet

Deck = []

for i in range(1, 4 + 1): # 8
    Deck.extend([CardSet[i] for _ in range(2)])

for i in range(6, 9 + 1): # 8
    Deck.extend([CardSet[i] for _ in range(2)])

for i in range(11, 14 + 1): # 8
    Deck.extend([CardSet[i] for _ in range(2)])
                                        # 24 25  26  27  28  29
Deck.extend([CardSet[index] for index in [5, 16, 16, 18, 18, 19]])
Deck.extend(["GAME_005"]) # 30
Deck.extend(["EX1_625t"]) # 31
#
HearthStone = {}
HearthStoneById = {}
# Open and load the JSON file
with open("cards.json", "rb") as file:
    data = json.load(file)
    for meta in data:
        if meta["id"] not in RealCard2EnvCard:
            RealCard2EnvCard[meta["id"]] = len(FullCardSet)
            EnvCard2RealCard[len(FullCardSet)] = meta["id"]
            FullCardSet.append(meta["id"])
        HearthStone[RealCard2EnvCard[meta["id"]]] = meta
        HearthStoneById[meta["id"]] = meta

class GameEnv(object):

    def __init__(self, players, flags):
        self.flags = flags

        self.game_over = False

        self.acting_player_position = None
        self.player_utility_dict = None

        self.players = players
        
        self.played_actions = {'landlord': [],
                             'second_hand': [],
                             }
        self.scores_of_each_actions = {'landlord': [],
                        'second_hand': [],
                        }
        self.companions_of_each_actions = {'landlord': [],
                        'second_hand': [],
                        }

        self.cost_of_each_actions = {'landlord': [],
                        'second_hand': [],
                        }

        self.num_wins = {'landlord': 0,
                         'farmer': 0}

        self.num_scores = {'landlord': 0,
                           'farmer': 0}

        self.info_sets = {'landlord': InfoSet('landlord'),
                         'second_hand': InfoSet('second_hand'),
                         }

        self.round = 0
        self.scores = {
            'landlord': 0,
            'second_hand': 0,
            }
        self.deck_cards = []
        self.game_over_times = 0

    def getDeckCards(self):
        return self.deck_cards
    
    def getCardForFirstHand(self, card_play_data):
        self.info_sets["landlord"].player_hand_cards = []
        self.info_sets["landlord"].player_deck_cards = []

        pirate_count = len([card for card in card_play_data["landlord"][:3] if Deck[card] in [
            # 宝藏经销商
            'TOY_518', 
            # 心灵按摩师
            'VAC_512',
            # 随船外科医师
            'CORE_WON_065',
        ]]) # MYWEN at least one pirate宝藏经销商 心灵按摩师 随船外科医师
        if pirate_count > 0:
            for card in card_play_data["landlord"][:3]:
                cardId = Deck[card]
                if HearthStoneById[cardId]["cost"] <= 2 and HearthStoneById[cardId]["type"] == "MINION" and cardId != "CFM_637": # 海盗帕奇斯
                    self.info_sets["landlord"].player_hand_cards.extend([card])
                else:
                    self.info_sets["landlord"].player_deck_cards.extend([card])
        else :
            self.info_sets["landlord"].player_deck_cards.extend(card_play_data["landlord"][:3])

        for card in card_play_data["landlord"][3:6]:
            if len(self.info_sets["landlord"].player_hand_cards) < 3:
                self.info_sets["landlord"].player_hand_cards.extend([card])
            else:
                self.info_sets["landlord"].player_deck_cards.extend([card])
        
        self.info_sets["landlord"].player_hand_cards.extend(card_play_data["landlord"][6:7])
        self.info_sets["landlord"].player_deck_cards.extend(card_play_data["landlord"][7:])

        # if self.flags.debug != True:
        #     np.random.shuffle(self.info_sets["landlord"].player_deck_cards)

    def getCardForSecondHand(self, card_play_data):
        self.info_sets["second_hand"].player_hand_cards = []
        self.info_sets["second_hand"].player_deck_cards = []

        pirate_count = len([card for card in card_play_data["second_hand"][:4] if Deck[card] in [
            # 宝藏经销商
            'TOY_518', 
            # 心灵按摩师
            'VAC_512',
            # 随船外科医师
            'CORE_WON_065',
        ]])
        if pirate_count > 0:
            for card in card_play_data["second_hand"][:4]:
                cardId = Deck[card]
                if HearthStoneById[cardId]["cost"] <= 2 and HearthStoneById[cardId]["type"] == "MINION" and cardId != "CFM_637":
                    self.info_sets["second_hand"].player_hand_cards.extend([card])
                else:
                    self.info_sets["second_hand"].player_deck_cards.extend([card])
        else:
            self.info_sets["second_hand"].player_deck_cards.extend(card_play_data["second_hand"][:4])

        for card in card_play_data["second_hand"][4:8]:
            if len(self.info_sets["second_hand"].player_hand_cards) < 4:
                self.info_sets["second_hand"].player_hand_cards.extend([card])
            else:
                self.info_sets["second_hand"].player_deck_cards.extend([card])
        
        self.info_sets["second_hand"].player_hand_cards.extend(card_play_data["second_hand"][8:9])
        self.info_sets["second_hand"].player_deck_cards.extend(card_play_data["second_hand"][9:])
        self.info_sets["second_hand"].player_hand_cards.extend([30]) # MYWEN coin
        
        # if self.flags.debug != True:
        #     np.random.shuffle(self.info_sets["second_hand"].player_deck_cards)
        
    def card_play_init(self, card_play_data):
        # if self.flags.debug == True:
        #     card_play_data["landlord"] = [2, 20, 7, 16, 1, 4, 3, 14, 27, 29, 5, 26, 10, 17, 25, 9, 23, 0, 18, 8, 28, 6, 11, 13, 19, 15, 21, 12, 24, 22]
        #     card_play_data["second_hand"] = [2, 20, 7, 16, 1, 4, 3, 14, 27, 29, 5, 26, 10, 17, 25, 9, 23, 0, 18, 8, 28, 6, 11, 13, 19, 15, 21, 12, 24, 22]
        # MYWEN 用一套牌还是两套牌
        self.getCardForFirstHand(card_play_data)
        self.getCardForSecondHand(card_play_data)
        # print (card_play_data["landlord"])
        # print (self.info_sets["landlord"].player_deck_cards)
        # print (self.info_sets["landlord"].player_hand_cards)
        # print (card_play_data["second_hand"])
        # print (self.info_sets["second_hand"].player_deck_cards)
        # print (self.info_sets["second_hand"].player_hand_cards)
        # if self.flags.debug == True:
        #     card_play_data["landlord"] = [28, 25, 14, 19, 1, 0, 22, 27, 18, 12, 9, 26, 4, 17, 11, 13, 15, 2, 23, 3, 7, 5, 24, 20, 10, 6, 21, 29, 8, 16]
        #     self.info_sets["landlord"].player_deck_cards = [28, 25, 0, 27, 18, 12, 9, 26, 4, 17, 11, 13, 15, 2, 23, 3, 7, 5, 24, 20, 10, 6, 21, 29, 8, 16]
        #     self.info_sets["landlord"].player_hand_cards = [14, 19, 1, 22]
        #     card_play_data["second_hand"] = [28, 25, 14, 19, 1, 0, 22, 27, 18, 12, 9, 26, 4, 17, 11, 13, 15, 2, 23, 3, 7, 5, 24, 20, 10, 6, 21, 29, 8, 16]
        #     self.info_sets["second_hand"].player_deck_cards = [28, 25, 22, 27, 12, 9, 26, 4, 17, 11, 13, 15, 2, 23, 3, 7, 5, 24, 20, 10, 6, 21, 29, 8, 16]
        #     self.info_sets["second_hand"].player_hand_cards = [14, 19, 1, 0, 18, 30]


        # for debug
        # MYWEN
        self.deck_cards = []
        self.deck_cards.extend(self.info_sets["landlord"].player_hand_cards)
        self.deck_cards.extend(self.info_sets["landlord"].player_deck_cards)
        self.acting_player_position = None
        self.get_acting_player_position()
        
        self.rival_attack_on_battlefield = {
            'landlord': 0,
            'second_hand': 0,
            }
        self.companion_on_battlefield = {
            'landlord': [],
            'second_hand': [],
            }
        self.buff = {
            'landlord': {},
            'second_hand': {},
            }
        self.companion_died = {
            'landlord': [],
            'second_hand': [],
            }

        self.round = 1
        self.scores = {
            'landlord': 0,
            'second_hand': 0,
            }
        self.game_infoset = self.get_infoset()

    def game_done(self, round_change):
        if (round_change == True and self.round > 7) or abs(self.scores["landlord"] - self.scores["second_hand"]) >= 30:
            # if one of the three players discards his hand,
            # then game is over.
            # if abs(self.scores["landlord"] - self.scores["second_hand"]) < 5:
            self.debug()
            self.update_num_wins_scores()
            self.game_over = True
            self.game_over_times += 1
            if self.game_over_times % 1000 == 0:
                print ("MYWEN game_over", self.game_over_times)

    def debug(self): # MYWEN
        if self.flags.debug == True:
            print ("MYWEN", self.deck_cards)
            print ("MYWEN", [HearthStoneById[Deck[card]]["name"] for card in self.deck_cards])
            print ("MYWEN", self.scores["landlord"], self.scores["second_hand"])
            round = 1
            for index, action in enumerate(self.played_actions["landlord"]):
                print ("MYWEN ", "landlord", round, 
                    [HearthStoneById[Deck[card]]["name"] for card in action], 
                    self.scores_of_each_actions["landlord"][index],
                    self.cost_of_each_actions["landlord"][index],
                    [HearthStoneById[Deck[card]]["name"] for card in self.companions_of_each_actions["landlord"][index]],
                )
                round += 1

            round = 1
            for index, action in enumerate(self.played_actions["second_hand"]):
                print ("MYWEN ", "second_hand", round, 
                    [HearthStoneById[Deck[card]]["name"] for card in action], 
                    self.scores_of_each_actions["second_hand"][index], 
                    self.cost_of_each_actions["second_hand"][index],
                    [HearthStoneById[Deck[card]]["name"] for card in self.companions_of_each_actions["second_hand"][index]],
                )
                round += 1

    def update_num_wins_scores(self):
        self.num_scores['landlord'] = 0
        self.num_scores['second_hand'] = 0

    def get_winner(self):
        return "landlord"
    
    def get_scores(self):
        return self.scores
    
    def getMockActionIndex(self, withCoin):
        scoreMax = 0
        actionMaxIndex = 0
        self.updateLocation(buff=self.buff[self.acting_player_position])
        for index, action in enumerate(self.info_sets[self.acting_player_position].legal_actions):
            coinCount = len([card for card in action if Deck[card] == "GAME_005" ])
            if coinCount > 0 and withCoin == False:
                continue
            buff = deepcopy(self.buff[self.acting_player_position])
            action = self.updateAction(action)
            self.updateBuff(action, buff)
            self.updateLocation(buff=buff)
            score = self.getCombinedScore(action, buff)
            if score > scoreMax or (score == scoreMax and self.info_sets[self.acting_player_position].companion_died != None and 1 in action and len(self.info_sets[self.acting_player_position].companion_died) >= 2): # 特殊处理过牌
                scoreMax = score
                actionMaxIndex = index
        return actionMaxIndex

    def getCombinedScore(self, action, buff):
        score = self.calculateScore(action, buff)
        attackNextRound = self.calculateAttackNextRound(action, buff)
        hp = self.calculateHPNextRound(action, buff)
        return score + attackNextRound + hp

    def filter_hearth_stone(self, all_moves):
        attackRivalHero = []
        for action in all_moves:
            buff = deepcopy(self.buff[self.acting_player_position])
            self.updateBuff(action, buff)
            self.updateLocation(buff=buff)
            attack = self.calculateScore(action, buff)
            attackRivalHero.extend([attack])

        return ms.filter_hearth_stone(all_moves, min(10, self.round), HearthStoneById, Deck,
                                self.companion_on_battlefield[self.acting_player_position],
                                self.info_sets[self.acting_player_position].companion_died if self.info_sets[self.acting_player_position].companion_died != None else [],
                                attackRivalHero,
                                self.info_sets[self.acting_player_position].player_deck_cards,
                                )

    def calculateScore(self, action, buff):
        # if 26 in self.companion_on_battlefield[self.acting_player_position] and 26 not in buff:
        #     print ("MYWEN", self.companion_on_battlefield[self.acting_player_position], buff)
        #     print (action)
        #     assert False
        # if 25 in self.companion_on_battlefield[self.acting_player_position] and 25 not in buff:
        #     print ("MYWEN", self.companion_on_battlefield[self.acting_player_position], buff)
        #     print (action)
        #     assert False
        companion_on_battlefield_details=[buff[card] for card in self.companion_on_battlefield[self.acting_player_position] if HearthStoneById[Deck[card]]["type"] == "MINION"]
        return ms.calculateAttack(action=action, HearthStoneById=HearthStoneById, Deck=Deck,
                                 companion_on_battlefield_details=companion_on_battlefield_details,
                                 )

    def calculateAttackNextRound(self, action, buff):
        # if 26 in self.companion_on_battlefield[self.acting_player_position] and 26 not in buff:
        #     print ("MYWEN", self.companion_on_battlefield[self.acting_player_position], buff)
        #     print (action)
        #     assert False
        # if 25 in self.companion_on_battlefield[self.acting_player_position] and 25 not in buff:
        #     print ("MYWEN", self.companion_on_battlefield[self.acting_player_position], buff)
        #     print (action)
        #     assert False
        companion_on_battlefield = self.companion_on_battlefield[self.acting_player_position] + \
            [card for card in action if HearthStoneById[Deck[card]]["type"] == "MINION"]
        attack = ms.calculateAttackNextRound(
            [buff[card] for card in companion_on_battlefield if HearthStoneById[Deck[card]]["type"] == "MINION"])
        return attack
    
    def calculateHPNextRound(self, action, buff):
        companion_on_battlefield = self.companion_on_battlefield[self.acting_player_position] + \
            [card for card in action if HearthStoneById[Deck[card]]["type"] == "MINION"]
        hp = ms.calculateHPNextRound(
            [buff[card] for card in companion_on_battlefield])
        return hp

    def updateAction(self, action):
        if 24 in self.info_sets[self.acting_player_position].player_deck_cards: # 海盗帕奇斯
            pirateCards = [ idx for idx, card in enumerate(action) if "races" in HearthStoneById[Deck[card]] and "PIRATE" in HearthStoneById[Deck[card]]["races"] ]
            if len(pirateCards) > 0:
                action = action[:pirateCards[0]+1] + [24] + action[pirateCards[0]+1:]
        return action

    def cost(self, action):
        cost, _ = ms.calculateActionCost(action, HearthStoneById, Deck,
                            self.companion_on_battlefield[self.acting_player_position],
                            self.calculateScore(action, self.buff[self.acting_player_position]),
                            self.info_sets[self.acting_player_position].player_deck_cards,
                            )
        return cost
    def step(self): # MYWEN todo
        action = self.players[self.acting_player_position].act(
            self.game_infoset)
        action = self.convertAction(action)
        # if self.flags.debug == True:
        #     print ("MYWEN", self.acting_player_position)
        #     print ("MYWEN", self.round, self.info_sets[self.acting_player_position].legal_actions)
        #     print ("MYWEN", action)
        #     print ("MYWEN", self.info_sets[self.acting_player_position].player_hand_cards)
        #     print ("MYWEN", self.info_sets[self.acting_player_position].companion_on_battlefield)
        assert action in self.info_sets[self.acting_player_position].legal_actions

        # 攻击前出地标牌
        self.updateBuff(action=action, buff=self.buff[self.acting_player_position])
        self.updateLocation(buff=self.buff[self.acting_player_position])

        score_of_action = self.calculateScore(action, self.buff[self.acting_player_position])
        self.scores[self.acting_player_position] += score_of_action
        self.scores_of_each_actions[self.acting_player_position].extend([score_of_action])
        self.cost_of_each_actions[self.acting_player_position].extend([self.cost(action)])

        # 海盗帕奇斯
        action = self.updateAction(action)
        self.updateBuff(action=action, buff=self.buff[self.acting_player_position])
        
        self.played_actions[self.acting_player_position].append(action)

        # 更新战场随从
        self.companions_of_each_actions[self.acting_player_position].append(self.companion_on_battlefield[self.acting_player_position] + [card for card in action if HearthStoneById[Deck[card]]["type"] == "MINION" or HearthStoneById[Deck[card]]["type"] == "LOCATION"])
        # 攻击后更新地标
        self.updateLocation(buff=self.buff[self.acting_player_position])

        # 出牌后剩余场攻
        self.rival_attack_on_battlefield[self.get_next_player_position()] = min(9, self.calculateAttackNextRound(action, buff=self.buff[self.acting_player_position]) // 3)

        # next round
        # 更新下一回合手牌
        self.update_acting_player_hand_cards(action, score_of_action)

        # 模拟随从死亡 MYWEN
        # 处理地标
        companion_on_battlefield = deepcopy(self.companions_of_each_actions[self.acting_player_position][-1])
        if 25 in companion_on_battlefield:
            companion_on_battlefield.remove(25)
        if 26 in companion_on_battlefield:
            companion_on_battlefield.remove(26)
        self.companion_on_battlefield[self.acting_player_position] = []
        for card in companion_on_battlefield:
            if self.buff[self.acting_player_position][card]["hp"] > 2:
                self.buff[self.acting_player_position][card]["hp"] -= 2
                self.companion_on_battlefield[self.acting_player_position].extend([card])
            else:
                random_bit = random.randint(0, 1)
                if random_bit == 0:
                    self.companion_died[self.acting_player_position].extend([card])
                    self.cleanBuff([card])
                else :
                    self.companion_on_battlefield[self.acting_player_position].extend([card])
        # companion_on_battlefield = random.sample(companion_on_battlefield, len(companion_on_battlefield)) # todo 加血增加成活率 MYWEN
        # self.companion_on_battlefield[self.acting_player_position] = companion_on_battlefield[: int(len(companion_on_battlefield)/ 2)]
        # self.companion_died[self.acting_player_position].extend(companion_on_battlefield[int(len(companion_on_battlefield) / 2):])
        # self.cleanBuff(companion_on_battlefield[int(len(companion_on_battlefield) / 2):])
        # 处理地标
        if 25 in self.buff[self.acting_player_position] and self.buff[self.acting_player_position][25]["hp"] > 0:
            self.companion_on_battlefield[self.acting_player_position].extend([25])
        if 26 in self.buff[self.acting_player_position] and self.buff[self.acting_player_position][26]["hp"] > 0:
            self.companion_on_battlefield[self.acting_player_position].extend([26])

        round_change = False
        if self.acting_player_position == "second_hand":
            self.round += 1
            round_change = True
        self.game_done(round_change)
        if not self.game_over: # MYWEN 切换玩家
            self.get_acting_player_position()
            self.game_infoset = self.get_infoset()

    def get_last_move(self):
        last_move = []
        if len(self.played_actions[self.acting_player_position]) >= 1:
                last_move = self.played_actions[self.acting_player_position][-1]
        return last_move

    def get_next_player_position(self):
        if self.acting_player_position == None or self.acting_player_position == "second_hand":
            return "landlord"
        elif self.acting_player_position == "landlord": # 后手
            return 'second_hand'
        else:
            raise Exception("mode not support")
        
    def get_acting_player_position(self):
        self.acting_player_position = self.get_next_player_position()
        return self.acting_player_position

    def update_acting_player_hand_cards(self, action, score_of_action):
        player_hand_cards = self.info_sets[self.acting_player_position].player_hand_cards
        played_card = []
        if action != []:
            for card in action:
                if Deck[card] == "EX1_625t": # 英雄技能
                    continue

                if card not in player_hand_cards and Deck[card] != "CFM_637":
                    print ("MYWEN", card, action, player_hand_cards)

                played_card.extend([card])

                if Deck[card] == "CFM_637" and card not in player_hand_cards and card in self.info_sets[self.acting_player_position].player_deck_cards: # 海盗帕奇斯
                    self.info_sets[self.acting_player_position].player_deck_cards.remove(card)
                else:
                    player_hand_cards.remove(card)

                ms.newCards(played_card, HearthStoneById, Deck,
                            self.info_sets[self.acting_player_position].companion_died,
                            score_of_action, # MYWEN todo
                            0,
                            self.info_sets[self.acting_player_position].player_deck_cards,
                            self.info_sets[self.acting_player_position].player_hand_cards,
                            self.buff[self.acting_player_position],
                            self.round,
                            )
        # new round
        player_deck_cards = self.info_sets[self.acting_player_position].player_deck_cards
        count = 1
        for card in player_deck_cards[:count]:
            if len(player_hand_cards) < 10:
                player_hand_cards.extend([card])
        self.info_sets[self.acting_player_position].player_deck_cards = player_deck_cards[count:]
    
    def get_legal_card_play_actions(self):
        mg = MovesGener(
            self.info_sets[self.acting_player_position].player_hand_cards, CardSet)

        all_moves = mg.gen_moves()

        moves = self.filter_hearth_stone(all_moves)

        # for m in moves:
        #     m.sort()

        return moves

    def reset(self):

        self.game_over = False

        self.acting_player_position = None
        self.player_utility_dict = None

        self.played_actions = {'landlord': [],
                             'second_hand': [],
                             }
        self.scores_of_each_actions = {'landlord': [],
                        'second_hand': [],
                        }
        self.companions_of_each_actions = {'landlord': [],
                        'second_hand': [],
                        }
        self.cost_of_each_actions = {'landlord': [],
                        'second_hand': [],
                        }

        self.info_sets = {'landlord': InfoSet('landlord'),
                         'second_hand': InfoSet('second_hand'),
                         }

        self.round = 1
        self.scores = {
            'landlord': 0,
            'second_hand': 0,
            }

    def get_infoset(self): # updated, after env.step, so this will be the next env.step
        self.info_sets[
            self.acting_player_position].legal_actions = \
            self.get_legal_card_play_actions()

        self.info_sets[
            self.acting_player_position].minion_attack_next_round = []
        self.info_sets[
            self.acting_player_position].advice = []

        for action in self.info_sets[self.acting_player_position].legal_actions:
            buff = deepcopy(self.buff[self.acting_player_position])
            action = self.updateAction(action)
            self.updateBuff(action=action, buff=buff)
            self.updateLocation(buff=buff)
            # 预测下回合，出完牌回合结束的综合评分
            self.info_sets[
                self.acting_player_position].minion_attack_next_round.append(min(9, self.getCombinedScore(action, buff) // 3))
            # 预测下回合能打出的直伤
            self.info_sets[
                self.acting_player_position].advice.append(min(9, self.calculateScore(action, buff) // 3))

        self.info_sets[
            self.acting_player_position].last_move = self.get_last_move()
        
        self.info_sets[
            self.acting_player_position].rival_attack_on_battlefield = self.rival_attack_on_battlefield[self.acting_player_position]
        
        self.info_sets[
            self.acting_player_position].companion_on_battlefield = self.companion_on_battlefield[self.acting_player_position]

        self.info_sets[self.acting_player_position].played_actions = \
            self.played_actions[self.acting_player_position]

        # if self.flags.debug == True:
        #     print ("INFOSET")
        #     print ("MYWEN", self.acting_player_position)
        #     print ("MYWEN", self.round, self.info_sets[self.acting_player_position].legal_actions)
        #     print ("MYWEN", self.info_sets[self.acting_player_position].player_hand_cards)
        #     print ("MYWEN battle", self.acting_player_position, self.info_sets[self.acting_player_position].companion_on_battlefield)
        return self.convertInfoset(deepcopy(self.info_sets[self.acting_player_position]))

    def convertAction(self, action):
        for legal_action in self.info_sets[self.acting_player_position].legal_actions:
            if [RealCard2EnvCard[Deck[card]] for card in legal_action] == action:
                return legal_action
        assert False

    def convertInfoset(self, infoset):
        infoset.player_deck_cards = [RealCard2EnvCard[Deck[card]] for card in infoset.player_deck_cards]
        infoset.player_hand_cards = [RealCard2EnvCard[Deck[card]] for card in infoset.player_hand_cards]
        infoset.companion_on_battlefield = [RealCard2EnvCard[Deck[card]] for card in infoset.companion_on_battlefield]
        
        infoset.legal_actions = [[RealCard2EnvCard[Deck[card]] for card in action] for action in infoset.legal_actions]
        infoset.last_move = [RealCard2EnvCard[Deck[card]] for card in infoset.last_move]
        infoset.played_actions = [[RealCard2EnvCard[Deck[card]] for card in action] for action in infoset.played_actions]
        return infoset

    def updateLocation(self, buff): # MYWEN 地标buff
        # companion_on_battlefield = self.companion_on_battlefield[self.acting_player_position]
        location = [card for card in buff.keys() if Deck[card] == "REV_290" and buff[card]["hp"] > 0]
        minion = [card for card in buff.keys() if Deck[card] != "REV_290"]
        if len(location) <= 0 or len(minion) <= 0:
            return ;
        # print ("MYWEN", companion_on_battlefield)
        # print ("MYWEN", location)
        # print ("MYWEN", minion)

        playList = [ # MYWEN play order
            'SW_446', # 虚触侍从
            "TOY_381", # 纸艺天使
            "CORE_WON_065", # 随船外科医师
            "TOY_518", # 宝藏经销商
            "HERO_POWER", # 心灵尖刺
            "SW_444", # 暮光欺诈者 # MYWEN 先放在打
            'VAC_512', # 心灵按摩师
            'CFM_637', # 海盗帕奇斯
            "DRG_056", # 空降歹徒
            "YOD_032", # 艾狂暴邪翼
            "MINION",
            "LOCATION",
        ]
        playOrder = {value: index for index, value in enumerate(playList)}

        sorted_cards = sorted(minion, key=lambda card: playOrder[Deck[card]] if Deck[card] in playOrder else playOrder[HearthStoneById[Deck[card]]["type"]])
        
        for loc in location:
            if (buff[loc]["round"] <= self.round - 2 and buff[loc]["hp"] > 0) or buff[loc]["hp"] == 3:
                buff[loc]["hp"] -= 1
                buff[loc]["round"] = self.round

                buff[sorted_cards[0]]["attack"] += 2
                buff[sorted_cards[0]]["hp"] += 1

    def cleanBuff(self, compaion_died):
        buff = self.buff[self.acting_player_position]
        for card in compaion_died:
            if card in buff:
                del buff[card]

    def updateBuff(self, action, buff):
        companion_on_battlefield = self.companion_on_battlefield[self.acting_player_position]

        for card in action:
            cardId = Deck[card]
            type = HearthStoneById[cardId]["type"]
            if type != "MINION" and type != "LOCATION":
                continue
            buff[card] = {
                "cardId": Deck[card],
                "attack": 0,
                "hp": 0,
                "round": self.round,
            }

        # 海盗 attack+1
        pirate_attack_plus_count = len([card for card in companion_on_battlefield if HearthStone[card]["id"] == "TOY_518"]) # 宝藏经销商
        for card in action:
            cardId = Deck[card]
            type = HearthStoneById[cardId]["type"]

            if type != "MINION":
                continue

            attack = HearthStoneById[cardId]["attack"]
            if "races" in HearthStoneById[cardId] and "PIRATE" in HearthStoneById[cardId]["races"]:
                attack += pirate_attack_plus_count
            buff[card]["attack"] = attack

            if cardId == "TOY_518":
                pirate_attack_plus_count += 1
            

        # 随从 hp+1
        minion_hp_plus_count = len([card for card in companion_on_battlefield if HearthStone[card]["id"] == "CORE_WON_065"]) # 随船外科医师
        for card in action:
            cardId = Deck[card]
            type = HearthStoneById[cardId]["type"]
            if "MINION" != type:
                continue
            hp = HearthStoneById[cardId]["health"]
            hp += minion_hp_plus_count
            buff[card]["hp"] = hp
            
            if cardId == "CORE_WON_065":
                minion_hp_plus_count += 1
            
        # 地标
        for card in action:
            cardId = Deck[card]
            type = HearthStoneById[cardId]["type"]
            if "LOCATION" != type:
                continue
            hp = HearthStoneById[cardId]["health"]
            buff[card]["hp"] = hp

class InfoSet(object):
    """
    The game state is described as infoset, which
    includes all the information in the current situation,
    such as the hand cards of the three players, the
    historical moves, etc.
    """
    def __init__(self, player_position):
        # The player position, i.e., landlord, or second_hand
        self.player_position = player_position
        # The hand cands of the current player. A list.
        self.player_hand_cards = None
        # The deck cands of the current player. A list.
        self.player_deck_cards = None
        # The legal actions for the current move. It is a list of list
        self.legal_actions = None
        # The most recent valid move
        self.last_move = None
        # The played actions so far. It is a list.
        self.played_actions = None
        # rival num
        self.rival_attack_on_battlefield = None
        # companion num
        self.companion_on_battlefield = None
        # companion dies
        self.companion_died = None
        # advice, totaly 10 level
        self.advice = None

        # minion_attack_next_round
        self.minion_attack_next_round = None

