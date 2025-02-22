from douzero.env.ko_strategy import calc_clean
from douzero.env.simulate_card import SimulateCard, Result, Action

from douzero.env.game import CardTypeToIndex, CardSet, FullCardSet, RealCard2EnvCard, EnvCard2RealCard, HearthStone, HearthStoneById, GameEnv

def case2():
    meCardDetails = [
        {
            "cardId": "REV_290",
            "type": "LOCATION",
            "attack": 0, 
            "hp": 3, 
            "entityId": "0", 
            "isActive": True,
            "playedRound": -1,
            "area": "PlayArea",
            "card": {
                "isImmune": False, 
                "isActive": False
            }
        },
        {
            "cardId": "SW_446", 
            "type": "MINION",
            "attack": 1, 
            "hp": 2, 
            "entityId": "1", 
            "isActive": True,
            "playedRound": -1,
            "area": "PlayArea",
            "card": {
                "isImmune": False, 
                "isActive": False
            }
        },
        {
            "type": "MINION",
            "cardId": "SW_444", 
            "attack": 2, 
            "hp": 3, 
            "entityId": "2", 
            "isActive": True,
            "playedRound": -1,
            "area": "PlayArea",
            "card": {
                "isImmune": False, 
                "isActive": False
            }
        },
        {
            "type": "MINION",
            "cardId": "VAC_512", 
            "attack": 3, 
            "hp": 4, 
            "entityId": "3", 
            "isActive": True,
            "area": "PlayArea",
            "playedRound": -1,
            "card": {
                "isImmune": False, 
                "isActive": False
            }
        },
        {
            "cardId": "GVG_009",
            "attack": 3,
            "hp": 1,
            "entityId": "4",
            "area": "PlayArea",
            "isActive": False,
            "playedRound": -1,
            "card": {
                "isImmune": False, 
                "isActive": False
            },
            "type": "MINION"
        },
        {
            "cardId": "EX1_625t", 
            "type": "SPELL",
            "attack": 2, 
            "hp": 1, 
            "entityId": "5", 
            "isActive": True,
            "playedRound": -1,
            "area": "HandArea",
            "card": {
                "isImmune": False, 
                "isActive": False
            }
        },
        {
            "cardId": "NX2_019", 
            "type": "SPELL",
            "attack": 2, 
            "hp": 1, 
            "entityId": "6", 
            "isActive": True,
            "playedRound": -1,
            "area": "HandArea",
            "card": {
                "isImmune": False, 
                "isActive": False
            }
        },
        {
            "cardId": "NX2_019", 
            "type": "SPELL",
            "attack": 2, 
            "hp": 1, 
            "entityId": "7", 
            "isActive": True,
            "playedRound": -1,
            "area": "HandArea",
            "card": {
                "isImmune": False, 
                "isActive": False
            }
        }
    ]

    rivalCardDetails = [
        {
            "type": "MINION",
            "cardId": "CFM_652", # CFM_652: 23, GDB_320: 19
            "attack": 4, 
            "hp": 5, 
            "entityId": "8", 
            "isActive": True,
            "playedRound": -1,
            "area": "PlayArea",
            "card": {
                "isTaunt": True,
                "isImmune": False, 
                "isLifesteal": False, # false: 23, true: 19
            }
        },
        {
            "type": "MINION",
            "cardId": "SW_444", 
            "attack": 1, 
            "hp": 5, 
            "entityId": "9", 
            "isActive": True,
            "playedRound": -1,
            "area": "PlayArea",
            "card": {
                "isImmune": False, 
                "isActive": False
            }
        },
        {
            "type": "HERO",
            "cardId": "HERO_09", 
            "attack": 0, 
            "hp": 29,
            "area": "PlayArea",
            "entityId": "10", 
            "isActive": True,
            "playedRound": -1,
            "card": {
                "isImmune": False, 
                "isActive": False,
                "isDivineShield": False, # True: 14, False: 20
            },
            "debuff": 2
        },
        {
            "cardId": "SW_446", 
            "type": "MINION",
            "attack": 1, 
            "area": "PlayArea",
            "hp": 2, 
            "entityId": "11", 
            "isActive": True,
            "playedRound": -1,
            "card": {
                "isImmune": False, 
                "isActive": False
            }
        },
    ]

    my_cards = [SimulateCard(card) for card in meCardDetails]
    rival_cards = [SimulateCard(card) for card in rivalCardDetails]

    result = calc_clean(my_cards, rival_cards)
    rivalHero = [card for card in rivalCardDetails if card["type"] == "HERO"][0]
    for action in result.actions:
        print (action)
    print (f"times: {result.times}, rivalHP: {result.heroHP}, reduceHP: {rivalHero['hp'] - result.heroHP} ")

    for attack in result.actions:
        companion = attack.my_card.cardDetails
        rival = attack.rival_card.cardDetails
        if rival != None:
            print (f"{companion['cardId']} - {rival['cardId']} ({companion['entityId']} - {rival['entityId']}) ({HearthStoneById[companion['cardId']]['name']} - {HearthStoneById[rival['cardId']]['name']})")
        else:
            print (f"{companion['cardId']} - ({companion['entityId']} - ) ({HearthStoneById[companion['entityId']]['name']} - )")

case2()