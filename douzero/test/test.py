import os
from copy import deepcopy
import torch

import re

import json
from itertools import combinations

from douzero.env.env import get_obs
from douzero.env.game import InfoSet, Deck
from douzero.env import move_selector_by_real_id as ms
from douzero.env.game import CardTypeToIndex, CardSet, FullCardSet, RealCard2EnvCard, EnvCard2RealCard, HearthStone, HearthStoneById, GameEnv

from collections import Counter

from douzero.env.simulate_card import SimulateCard, Result, KOResult
from douzero.env import ko_strategy, clean_strategy

cardDetails = {
    "type": "HERO",
    "cardId": "HERO_09", 
    "attack": 0, 
    "hp": 30,
    "entityId": "200",
    "area": "HERO",
    "isActive": True,
    "playedRound": -1,
    "card": {
        "isImmune": True
    }
}

hero = SimulateCard(cardDetails)

print (hero.blood)
hero.blood -= 3
print (hero.blood)