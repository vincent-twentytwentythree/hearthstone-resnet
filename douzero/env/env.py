from collections import Counter
import numpy as np

from douzero.env.game import GameEnv, HearthStone, CardTypeToIndex, Deck, RealCard2EnvCard, HearthStoneById
from copy import deepcopy

NumOnes2Array = {0: np.array([0, 0]),
                 1: np.array([1, 0]),
                 2: np.array([1, 1]),
                 3: np.array([1, 1]),
                 4: np.array([1, 1]),
                 5: np.array([1, 1]),
                 6: np.array([1, 1]),
                 }



class Env:
    """
    Doudizhu multi-agent wrapper
    """
    def __init__(self, objective, flags):
        """
        Objective is wp/adp/logadp. It indicates whether considers
        bomb in reward calculation. Here, we use dummy agents.
        This is because, in the orignial game, the players
        are `in` the game. Here, we want to isolate
        players and environments to have a more gym style
        interface. To achieve this, we use dummy players
        to play. For each move, we tell the corresponding
        dummy player which action to play, then the player
        will perform the actual action in the game engine.
        """
        self.objective = objective
        self.flags = flags

        # Initialize players
        # We use three dummy player for the target position
        self.players = {}
        for position in ['landlord', 'second_hand']:
            self.players[position] = DummyAgent(position)

        # Initialize the internal environment
        self._env = GameEnv(self.players, flags)

        self.infoset = None

    def getDeckCards(self):
        return self._env.getDeckCards()
    
    def getMockActionIndex(self, withCoin):
        return self._env.getMockActionIndex(withCoin)
    
    def calculateScore(self, action):
        return self._env.calculateScore(action)
    
    def reset(self):
        """
        Every time reset is called, the environment
        will be re-initialized with a new deck of cards.
        This function is usually called when a game is over.
        """
        self._env.reset()

        # Randomly shuffle the deck
        _deck = [idx for idx in range(30)]
        np.random.shuffle(_deck)
        card_play_data = {'landlord': [],
                          'second_hand': [],
                          }
        card_play_data["landlord"] = _deck[:30]
        card_play_data["second_hand"] = _deck[:30]
        # if self.flags.debug == True:
        #     # cardSetForTest = ['宝藏经销商', '虚触侍从', '暗影投弹手', '纸艺天使', '空降歹徒', '亡者复生', '虚触侍从', '空降歹徒', '针灸', '暮光欺诈者', \
        #     #                   '赎罪教堂', '海盗帕奇斯', '精神灼烧', '心灵按摩师', '心灵震爆', '暗影投弹手', '随船外科医师', '狂暴邪翼蝠', '赎罪教堂', '狂暴邪翼蝠', \
        #     #                     '暮光欺诈者', '心灵震爆', '针灸', '宝藏经销商', '纸艺天使', '随船外科医师', '精神灼烧', '黑暗主教本尼迪塔斯', '心灵按摩师', '亡者复生'] # MYWEN
        #     # card_play_data["landlord"] = []
        #     # for name in cardSetForTest:
        #     #     for card in _deck:
        #     #         if name == HearthStoneById[Deck[card]]["name"]:
        #     #             card_play_data["landlord"].extend([card])
        #     #             _deck.remove(card)
        #     #             break
        #     # assert len(cardSetForTest) == len(card_play_data["landlord"])
        #     card_play_data["landlord"] = [14, 2, 25, 3, 5, 15, 20, 16, 11, 13, 7, 17, 4, 21, 12, 1, 28, 19, 23, 24, 6, 27, 29, 26, 8, 22, 9, 10, 18, 0]
        # Initialize the cards
        self._env.card_play_init(card_play_data)
        self.infoset = self._game_infoset

        return get_obs(self.infoset)

    def step(self, action): # MYWEN
        """
        Step function takes as input the action, which
        is a list of integers, and output the next obervation,
        reward, and a Boolean variable indicating whether the
        current game is finished. It also returns an empty
        dictionary that is reserved to pass useful information.
        """
        assert action in self.infoset.legal_actions
        self.players[self._acting_player_position].set_action(action)
        self._env.step()
        self.infoset = self._game_infoset
        done = False
        reward = 0.0
        if self._game_over:
            done = True
            reward = self._get_reward()
            obs = None
        else:

            obs = get_obs(self.infoset)
        return obs, reward, done, {}

    def _get_reward(self):
        """
        This function is called in the end of each
        game. It returns either 1/-1 for win/loss,
        or ADP, i.e., every bomb will double the score.
        """
        winner = self._game_winner
        scores = self._game_scores
        if self.objective == 'adp':
            return (scores["landlord"] - scores["second_hand"]) / 7
        else:
            return 1.0 if scores["landlord"] > scores["second_hand"] else -1.0

    @property
    def _game_infoset(self):
        """
        Here, inforset is defined as all the information
        in the current situation, incuding the hand cards
        of all the players, all the historical moves, etc.
        That is, it contains perferfect infomation. Later,
        we will use functions to extract the observable
        information from the views of the three players.
        """
        return self._env.game_infoset

    @property
    def _game_scores(self):
        """
        The number of bombs played so far. This is used as
        a feature of the neural network and is also used to
        calculate ADP.
        """
        return self._env.get_scores()

    @property
    def _game_winner(self):
        """ A string of landlord/peasants
        """
        return self._env.get_winner()

    @property
    def _acting_player_position(self):
        """
        The player that is active. It can be landlord,
        landlod_down, or second_hand.
        """
        return self._env.acting_player_position

    @property
    def _game_over(self):
        """ Returns a Boolean
        """
        return self._env.game_over

class DummyAgent(object):
    """
    Dummy agent is designed to easily interact with the
    game engine. The agent will first be told what action
    to perform. Then the environment will call this agent
    to perform the actual action. This can help us to
    isolate environment and agents towards a gym like
    interface.
    """
    def __init__(self, position):
        self.position = position
        self.action = None

    def act(self, infoset):
        """
        Simply return the action that is set previously.
        """
        assert self.action in infoset.legal_actions
        return self.action

    def set_action(self, action):
        """
        The environment uses this function to tell
        the dummy agent what to do.
        """
        self.action = action

def get_obs(infoset):
    """
    This function obtains observations with imperfect information
    from the infoset. It has three branches since we encode
    different features for different positions.
    
    This function will return dictionary named `obs`. It contains
    several fields. These fields will be used to train the model.
    One can play with those features to improve the performance.

    `position` is a string that can be landlord/second_hand

    `x_batch` is a batch of features (excluding the hisorical moves).
    It also encodes the action feature

    `z_batch` is a batch of features with hisorical moves only.

    `legal_actions` is the legal moves

    `x_no_action`: the features (exluding the hitorical moves and
    the action features). It does not have the batch dim.

    `z`: same as z_batch but not a batch.
    """
    return _get_obs_landlord(infoset)

def _get_one_hot_array(num_left_cards, max_num_cards): # one_hot for num_left_cards
    """
    A utility function to obtain one-hot endoding
    """
    num_left_cards = int(num_left_cards)
    one_hot = np.zeros(max_num_cards)
    num_left_cards = min(num_left_cards, max_num_cards)
    if num_left_cards >= 1:
        one_hot[num_left_cards - 1] = 1
    # print ("MYWEN", num_left_cards, max_num_cards, one_hot)
    return one_hot

def _cards2array(list_cards): # size of 42
    """
    A utility function that transforms the actions, i.e.,
    A list of integers into card matrix. Here we remove
    the six entries that are always zero and flatten the
    the representations.
    """
    if len(list_cards) == 0:
        return np.zeros(42, dtype=np.int8) # 21 * 2 MYWEN

    matrix = np.zeros([2, 21], dtype=np.int8)
    counter = Counter(list_cards)
    for card, num_times in counter.items():
        matrix[:, card] = NumOnes2Array[num_times]
    return matrix.flatten('F')

def _action_seq_list2array(action_seq_list):
    """
    A utility function to encode the historical moves.
    We encode the historical 15 actions. If there is
    no 15 actions, we pad the features with 0. Since
    three moves is a round in DouDizhu, we concatenate
    the representations for each consecutive three moves.
    Finally, we obtain a 5x162 matrix, which will be fed
    into LSTM for encoding.
    """
    # action_seq_array = np.zeros((len(action_seq_list), 42))
    # for row, list_cards in enumerate(action_seq_list):
    #     action_seq_array[row, :] = _cards2array(list_cards)
    # action_seq_array = action_seq_array.reshape(5, 126)
    # return action_seq_array
    action_seq_array = np.ones((len(action_seq_list), 42)) * -1  # Default Value -1 for not using area
    for row, list_cards in enumerate(action_seq_list):
        if list_cards != []:
            action_seq_array[row, :42] = _cards2array(list_cards)
    return action_seq_array

def _process_action_seq(sequence, length=15):
    """
    A utility function encoding historical moves. We
    encode 15 moves. If there is no 15 moves, we pad
    with zeros.
    """
    sequence = sequence[-length:].copy()
    if len(sequence) < length:
        empty_sequence = [[] for _ in range(length - len(sequence))]
        empty_sequence.extend(sequence)
        sequence = empty_sequence
    return sequence

def _get_obs_landlord(infoset): # MYWEN obs details
    """
    Obttain the landlord features. See Table 4 in
    https://arxiv.org/pdf/2106.06135.pdf
    """
    num_legal_actions = len(infoset.legal_actions)
    my_handcards = _cards2array(infoset.player_hand_cards) # todo
    my_handcards_batch = np.repeat(my_handcards[np.newaxis, :],
                                   num_legal_actions, axis=0)

    player_deck_cards = _cards2array(infoset.player_deck_cards) # todo
    player_deck_cards_batch = np.repeat(player_deck_cards[np.newaxis, :],
                                      num_legal_actions, axis=0)
    
    companions_on_battlefield = _cards2array(infoset.companion_on_battlefield)
    companions_on_battlefield_batch = np.repeat(companions_on_battlefield[np.newaxis, :],
                                      num_legal_actions, axis=0)
    
    last_action = _cards2array(infoset.last_move)
    last_action_batch = np.repeat(last_action[np.newaxis, :],
                                  num_legal_actions, axis=0)
    
    rivals_attack = _get_one_hot_array(
        infoset.rival_attack_on_battlefield, 10)
    rivals_attack_batch = np.repeat(
        rivals_attack[np.newaxis, :],
        num_legal_actions, axis=0)

    # 5 * 7
    minion_attack_batch = np.zeros(rivals_attack_batch.shape)
    advice_batch = np.zeros(rivals_attack_batch.shape)
    my_action_batch = np.zeros(my_handcards_batch.shape)

    other_details = []
    # print ("MYWEN", infoset.minion_attack_next_round)
    for j, action in enumerate(infoset.legal_actions):
        minion_attack_batch[j,:] = _get_one_hot_array(infoset.minion_attack_next_round[j], 10)
        advice_batch[j,:] = _get_one_hot_array(infoset.advice[j], 10)
        my_action_batch[j, :] = _cards2array(action)
        other_details.append([infoset.rival_attack_on_battlefield,
                              infoset.minion_attack_next_round[j],
                              infoset.advice[j],
                              infoset.player_hand_cards,
                              ])

    # x_batch = np.hstack((my_handcards_batch, # 42
    #                      player_deck_cards_batch, # 42
    #                      last_action_batch, # 42
    #                      companions_on_battlefield_batch, # 42
    #                      rivals_attack_batch, # 10
    #                      minion_attack_batch, # 10,
    #                      advice_batch, # 10
    #                      my_action_batch)) # 42
    # x_no_action = np.hstack((my_handcards, # 42
    #                         player_deck_cards, # 42
    #                         last_action, # 42
    #                         companions_on_battlefield, # 42
    #                         rivals_attack, # 10
    #                          ))
    # z = _action_seq_list2array(_process_action_seq(
    #     infoset.played_actions))
    # z_batch = np.repeat(
    #     z[np.newaxis, :, :],
    #     num_legal_actions, axis=0)

    x_batch = np.hstack((
        rivals_attack_batch,
    )) # -> actions * 10
    x_no_action = np.hstack((
        rivals_attack,
    )) # -> 10

    z = np.vstack((my_handcards, # 42
                         player_deck_cards, # 42
                         last_action, # 42
                         companions_on_battlefield, # 42
                         _action_seq_list2array(_process_action_seq(
                            infoset.played_actions, length=8)), # 8 * 42
                         )) # 12 * 42
    _z_batch = np.repeat(
        z[np.newaxis, :, :],
        num_legal_actions, axis=0)
    
    my_action_batch = my_action_batch[:,np.newaxis,:] # actions * 1 * 42

    z_batch = np.zeros([len(_z_batch),14,42],int) # actions * 14 * 42
    for i in range(0,len(_z_batch)):
        attributes1 = np.hstack((
            rivals_attack, # 10
            minion_attack_batch[i], # 10
            advice_batch[i], # 10
            [-1] * 12, # 12 # MYWEN TODO default value
        )) # -> 42

        z_batch[i] = np.vstack((my_action_batch[i], # 1 * 42
                                [attributes1], # 1 * 42
                                _z_batch[i]) # 12 * 42
                                ) # 14 * 42

    obs = {
            'position': infoset.player_position,
            'x_batch': x_batch.astype(np.float32), # shape (num_legal_actions, 5 * 42 + 3 * 10)
            'z_batch': z_batch.astype(np.float32), # shape (num_legal_actions, 5 * 120)
            'legal_actions': infoset.legal_actions, # shape (num_legal_actions, 42)
            'x_no_action': x_no_action.astype(np.int8), # shape (4 * 42 + 1 * 10),
            'other_details': other_details, # shape (num_legal_actions, 2 * 10)
            'z': z.astype(np.int8),
          }
    return obs
