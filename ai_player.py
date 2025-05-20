
import random

def choose_move(game_state, player_id, possible_moves):

    if not possible_moves:
        return []

    return random.choice(possible_moves)