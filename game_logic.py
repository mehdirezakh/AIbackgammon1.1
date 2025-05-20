import random
import json
import copy

NUM_POINTS = 24
MAX_CHECKERS_PER_PLAYER = 15
PLAYER_X = 0
PLAYER_O = 1


class BackgammonGame:
    def __init__(self):
        self.board = self.initial_board()
        self.bar = {PLAYER_X: 0, PLAYER_O: 0}
        self.borne_off = {PLAYER_X: 0, PLAYER_O: 0}
        self.current_player = None
        self.dice = []
        self.dice_used = {}

        self.doubles_played_count = 0
        self.winner = None
        self.first_roll_made = False
        self.log_prefix = "[GameLogic] "

    def _update_log_prefix(self):
        player_str = f"P{self.current_player}" if self.current_player is not None else "None"
        dice_str = f"D:{self.dice}" if self.dice else "D:[]"
        self.log_prefix = f"[GameLogic {player_str} {dice_str}] "

    def initial_board(self):
        board = [[None, 0] for _ in range(NUM_POINTS)]
        board[0] = [PLAYER_O, 2]
        board[11] = [PLAYER_O, 5]
        board[16] = [PLAYER_O, 3]
        board[18] = [PLAYER_O, 5]
        board[5] = [PLAYER_X, 5]
        board[7] = [PLAYER_X, 3]
        board[12] = [PLAYER_X, 5]
        board[23] = [PLAYER_X, 2]
        return board

    def roll_dice(self):
        self._update_log_prefix()
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        self.dice = sorted([d1, d2], reverse=True)

        if d1 == d2:
            self.dice_used = {d1: [False, False, False, False]}
        else:
            self.dice_used = {val: False for val in self.dice}

        self.doubles_played_count = 0
        self._update_log_prefix()
        print(f"{self.log_prefix}Rolled dice: {self.dice}. Initial dice_used: {self.dice_used}")
        return self.dice

    def determine_first_player(self):
        while True:
            d1, d2 = random.randint(1, 6), random.randint(1, 6)
            if d1 != d2:
                self.current_player = PLAYER_X if d1 > d2 else PLAYER_O
                self.dice = sorted([d1, d2], reverse=True)

                self.dice_used = {val: False for val in self.dice}
                self.doubles_played_count = 0

                self.first_roll_made = True
                self._update_log_prefix()
                print(
                    f"{self.log_prefix}First player P{self.current_player}, first dice {self.dice}, dice_used: {self.dice_used}")
                return self.current_player, self.dice

    def get_opponent(self, player):
        return PLAYER_O if player == PLAYER_X else PLAYER_X

    def get_player_home_board_range(self, player):
        return range(0, 6) if player == PLAYER_X else range(18, 24)

    def all_checkers_in_home_state(self, player, board_state, bar_state):
        if bar_state.get(player, 0) > 0:
            return False
        home_range = self.get_player_home_board_range(player)
        for i in range(NUM_POINTS):
            if board_state[i][0] == player and board_state[i][1] > 0 and i not in home_range:
                return False
        return True

    def get_target_point(self, player, start_point_idx, die_roll):
        if player == PLAYER_X:
            return start_point_idx - die_roll
        else:
            return start_point_idx + die_roll

    def is_move_valid(self, player, moves_from_client):
        moves = []
        for m_part in moves_from_client:
            try:
                start = m_part[0] if m_part[0] == 'BAR' else int(m_part[0])
                end = m_part[1] if m_part[1] == 'OFF' else int(m_part[1])
                moves.append(tuple((start, end)))
            except (ValueError, TypeError, IndexError):
                print(f"{self.log_prefix}IS_MOVE_VALID: FAIL - Malformed move segment: {m_part}")
                return False

        self._update_log_prefix()

        if self.winner is not None:
            print(f"{self.log_prefix}IS_MOVE_VALID: FAIL - Game winner P{self.winner} already declared.")
            return False
        if player != self.current_player:
            print(f"{self.log_prefix}IS_MOVE_VALID: FAIL - Not P{player}'s turn (Current: P{self.current_player}).")
            return False
        if not self.dice:
            print(f"{self.log_prefix}IS_MOVE_VALID: FAIL - No dice for P{player} (self.dice: {self.dice}).")
            return False

        temp_board = copy.deepcopy(self.board)
        temp_bar = {int(k): v for k, v in self.bar.items()}

        current_turn_dice_options = list(self.dice)
        is_double_roll = len(current_turn_dice_options) == 2 and current_turn_dice_options[0] == \
                         current_turn_dice_options[1]

        available_dice_for_sequence = [current_turn_dice_options[0]] * 4 if is_double_roll else list(
            current_turn_dice_options)

        if not moves:
            if self.get_possible_moves(player, current_turn_dice_options, self.board, self.bar):
                print(f"{self.log_prefix}IS_MOVE_VALID: FAIL (Pass attempt) - Moves are possible.")
                return False
            else:
                print(f"{self.log_prefix}IS_MOVE_VALID: VALID (Pass attempt) - No moves found by get_possible_moves.")
                return True

        pips_player_moved_in_sequence = []
        for i, (start_pip_val, end_pip_val) in enumerate(moves):
            sub_log = f"{self.log_prefix}  Sub-move {i + 1} ({start_pip_val} -> {end_pip_val}): "
            is_entering_from_bar = (start_pip_val == 'BAR')
            is_bearing_off = (end_pip_val == 'OFF')
            start_pip_idx = -1

            if is_entering_from_bar:
                if temp_bar.get(player, 0) == 0:
                    print(f"{sub_log}FAIL - Cannot enter from bar, P{player} bar is empty: {temp_bar.get(player, 0)}.")
                    return False
            else:
                start_pip_idx = int(start_pip_val)
                if not (0 <= start_pip_idx < NUM_POINTS):
                    print(f"{sub_log}FAIL - Start pip {start_pip_idx} out of bounds.")
                    return False
                if temp_board[start_pip_idx][0] != player or temp_board[start_pip_idx][1] == 0:
                    print(
                        f"{sub_log}FAIL - No checkers for P{player} at start pip {start_pip_idx}. Point state: {temp_board[start_pip_idx]}")
                    return False
                if temp_bar.get(player, 0) > 0:
                    print(f"{sub_log}FAIL - P{player} must enter {temp_bar.get(player, 0)} checker(s) from bar first.")
                    return False

            actual_pip_distance_for_this_move = 0
            landing_pip_idx = -1
            opponent = self.get_opponent(player)

            if is_bearing_off:
                if not self.all_checkers_in_home_state(player, temp_board, temp_bar):
                    print(f"{sub_log}FAIL - Cannot bear off, not all checkers in home board or bar not empty.")
                    return False

                home_range_for_player = self.get_player_home_board_range(player)
                if start_pip_idx not in home_range_for_player:
                    print(
                        f"{sub_log}FAIL - Bear off attempt from {start_pip_idx} which is not in home board {home_range_for_player}.")
                    return False

                required_pip_for_exact_bear_off = (start_pip_idx + 1) if player == PLAYER_X else (
                            NUM_POINTS - start_pip_idx)

                die_to_consume_for_bear_off = -1
                if required_pip_for_exact_bear_off in available_dice_for_sequence:
                    die_to_consume_for_bear_off = required_pip_for_exact_bear_off
                else:
                    is_furthest_checker_in_home = True
                    if player == PLAYER_X:
                        for p_check_idx in range(start_pip_idx + 1,
                                                 home_range_for_player.stop):
                            if p_check_idx in home_range_for_player and temp_board[p_check_idx][0] == player and \
                                    temp_board[p_check_idx][1] > 0:
                                is_furthest_checker_in_home = False;
                                break
                    else:
                        for p_check_idx in range(start_pip_idx - 1, home_range_for_player.start - 1,
                                                 -1):
                            if p_check_idx in home_range_for_player and temp_board[p_check_idx][0] == player and \
                                    temp_board[p_check_idx][1] > 0:
                                is_furthest_checker_in_home = False;
                                break

                    if is_furthest_checker_in_home:
                        suitable_overshoot_dice = [d for d in available_dice_for_sequence if
                                                   d > required_pip_for_exact_bear_off]
                        if suitable_overshoot_dice:
                            die_to_consume_for_bear_off = min(
                                suitable_overshoot_dice)

                if die_to_consume_for_bear_off == -1:
                    print(
                        f"{sub_log}FAIL - Bear off from {start_pip_idx} (req pip {required_pip_for_exact_bear_off}). No suitable die in {available_dice_for_sequence}.")
                    return False
                actual_pip_distance_for_this_move = die_to_consume_for_bear_off

            elif is_entering_from_bar:
                landing_pip_idx = int(end_pip_val)
                if player == PLAYER_X:
                    actual_pip_distance_for_this_move = NUM_POINTS - landing_pip_idx
                    if not (NUM_POINTS - 6 <= landing_pip_idx < NUM_POINTS):
                        print(f"{sub_log}FAIL - P{player}(X) entering invalid pip {landing_pip_idx} from bar.")
                        return False
                else:
                    actual_pip_distance_for_this_move = landing_pip_idx + 1
                    if not (0 <= landing_pip_idx < 6):
                        print(f"{sub_log}FAIL - P{player}(O) entering invalid pip {landing_pip_idx} from bar.")
                        return False

            else:
                landing_pip_idx = int(end_pip_val)
                if not (0 <= landing_pip_idx < NUM_POINTS):
                    print(f"{sub_log}FAIL - Target pip {landing_pip_idx} out of bounds.")
                    return False
                actual_pip_distance_for_this_move = abs(start_pip_idx - landing_pip_idx)
                if (player == PLAYER_X and landing_pip_idx >= start_pip_idx) or \
                        (player == PLAYER_O and landing_pip_idx <= start_pip_idx):
                    print(
                        f"{sub_log}FAIL - P{player} moving wrong direction from {start_pip_idx} to {landing_pip_idx}.")
                    return False

            if not (1 <= actual_pip_distance_for_this_move <= 6):
                print(
                    f"{sub_log}FAIL - Deduced pip distance {actual_pip_distance_for_this_move} is not a valid die (1-6).")
                return False
            try:
                available_dice_for_sequence.remove(actual_pip_distance_for_this_move)
                pips_player_moved_in_sequence.append(actual_pip_distance_for_this_move)
            except ValueError:
                print(
                    f"{sub_log}FAIL - Deduced pip distance {actual_pip_distance_for_this_move} not in available dice {available_dice_for_sequence}.")
                return False

            if not is_bearing_off:
                target_owner, target_checkers_count = temp_board[landing_pip_idx]
                if target_owner == opponent and target_checkers_count > 1:
                    print(
                        f"{sub_log}FAIL - Target pip {landing_pip_idx} is blocked by P{opponent} (count: {target_checkers_count}).")
                    return False

            if is_entering_from_bar:
                temp_bar[player] -= 1
            else:
                temp_board[start_pip_idx][1] -= 1
                if temp_board[start_pip_idx][1] == 0: temp_board[start_pip_idx][0] = None

            if not is_bearing_off:
                target_owner, target_checkers_count = temp_board[landing_pip_idx]
                if target_owner == opponent and target_checkers_count == 1:
                    temp_board[landing_pip_idx] = [player, 1]
                    temp_bar[opponent] += 1
                else:
                    temp_board[landing_pip_idx][0] = player
                    temp_board[landing_pip_idx][1] += 1

        num_dice_player_used_in_sequence = len(pips_player_moved_in_sequence)

        all_possible_turns_from_original_state = self.get_possible_moves(player, list(self.dice), self.board, self.bar)

        max_dice_truly_playable_this_turn = 0
        if all_possible_turns_from_original_state:
            max_dice_truly_playable_this_turn = max(len(turn) for turn in all_possible_turns_from_original_state)

        if num_dice_player_used_in_sequence < max_dice_truly_playable_this_turn:
            print(
                f"{self.log_prefix}IS_MOVE_VALID: FAIL - Player used {num_dice_player_used_in_sequence} dice, but could have used {max_dice_truly_playable_this_turn}.")
            return False

        original_dice_for_turn = list(self.dice)
        is_original_roll_double = len(original_dice_for_turn) == 2 and original_dice_for_turn[0] == \
                                  original_dice_for_turn[1]

        if not is_original_roll_double and len(original_dice_for_turn) == 2 and \
                num_dice_player_used_in_sequence == 1 and max_dice_truly_playable_this_turn == 1:

            larger_die_of_roll = original_dice_for_turn[0]
            smaller_die_of_roll = original_dice_for_turn[1]
            die_player_actually_used = pips_player_moved_in_sequence[0]

            if die_player_actually_used == smaller_die_of_roll:
                possible_single_moves_with_larger_die = self._get_possible_moves_recursive(
                    player, [larger_die_of_roll], self.board, self.bar, []
                )
                can_play_larger_die_singly = any(len(seq) == 1 for seq in possible_single_moves_with_larger_die if seq)

                if can_play_larger_die_singly:
                    print(
                        f"{self.log_prefix}IS_MOVE_VALID: FAIL - Player used smaller die ({smaller_die_of_roll}), but larger die ({larger_die_of_roll}) was playable singly.")
                    return False

        print(f"{self.log_prefix}IS_MOVE_VALID: ALL CHECKS PASSED for moves: {moves}")
        return True

    def apply_moves(self, player, moves_from_client):
        moves = []
        for m_part in moves_from_client:
            start = m_part[0] if m_part[0] == 'BAR' else int(m_part[0])
            end = m_part[1] if m_part[1] == 'OFF' else int(m_part[1])
            moves.append(tuple((start, end)))

        self._update_log_prefix()
        print(
            f"{self.log_prefix}APPLY_MOVES for P{player} with moves {moves}. Current dice_used before apply: {self.dice_used}, Current dice: {self.dice}")

        is_original_roll_double = len(self.dice) == 2 and self.dice[0] == self.dice[1]

        for start_pip_val, end_pip_val in moves:
            is_entering_from_bar = (start_pip_val == 'BAR')
            is_bearing_off = (end_pip_val == 'OFF')
            start_pip_idx = -1 if is_entering_from_bar else int(start_pip_val)

            actual_die_val_for_segment = 0

            if is_bearing_off:
                required_pip_for_exact_bear_off = (start_pip_idx + 1) if player == PLAYER_X else (
                            NUM_POINTS - start_pip_idx)

                if not is_original_roll_double:
                    if required_pip_for_exact_bear_off in self.dice_used and not self.dice_used[
                        required_pip_for_exact_bear_off]:
                        actual_die_val_for_segment = required_pip_for_exact_bear_off
                else:
                    if required_pip_for_exact_bear_off == self.dice[0] and self.doubles_played_count < 4:
                        if any(not used for used in self.dice_used[self.dice[0]]):
                            actual_die_val_for_segment = required_pip_for_exact_bear_off

                if actual_die_val_for_segment == 0:
                    home_range = self.get_player_home_board_range(player)
                    is_furthest = True
                    if player == PLAYER_X:
                        for p_check_idx in range(start_pip_idx + 1, home_range.stop):
                            if p_check_idx in home_range and self.board[p_check_idx][0] == player and \
                                    self.board[p_check_idx][1] > 0:
                                is_furthest = False;
                                break
                    else:
                        for p_check_idx in range(start_pip_idx - 1, home_range.start - 1, -1):
                            if p_check_idx in home_range and self.board[p_check_idx][0] == player and \
                                    self.board[p_check_idx][1] > 0:
                                is_furthest = False;
                                break

                    if is_furthest:
                        overshoot_candidates = []
                        if not is_original_roll_double:
                            overshoot_candidates = [d for d in self.dice_used if
                                                    not self.dice_used[d] and d > required_pip_for_exact_bear_off]
                        else:
                            if self.dice[0] > required_pip_for_exact_bear_off and self.doubles_played_count < 4:
                                if any(not used for used in self.dice_used[self.dice[0]]):
                                    overshoot_candidates = [self.dice[0]]

                        if overshoot_candidates:
                            actual_die_val_for_segment = min(overshoot_candidates)

                if actual_die_val_for_segment == 0:
                    print(
                        f"{self.log_prefix}APPLY_MOVES WARN: Bear-off die deduction complex. Defaulting to required_pip {required_pip_for_exact_bear_off} if still 0.")
                    actual_die_val_for_segment = required_pip_for_exact_bear_off


            elif is_entering_from_bar:
                landing_pip_idx = int(end_pip_val)
                actual_die_val_for_segment = (NUM_POINTS - landing_pip_idx) if player == PLAYER_X else (
                            landing_pip_idx + 1)
            else:
                landing_pip_idx = int(end_pip_val)
                actual_die_val_for_segment = abs(start_pip_idx - landing_pip_idx)

            if not (1 <= actual_die_val_for_segment <= 6):
                print(
                    f"{self.log_prefix}APPLY_MOVES CRITICAL ERROR: Deduced die {actual_die_val_for_segment} for move ({start_pip_val}->{end_pip_val}) is invalid. This shouldn't happen after is_move_valid.")

            die_marked_successfully = False
            if is_original_roll_double:
                if actual_die_val_for_segment == self.dice[0]:
                    for i in range(4):
                        if not self.dice_used[self.dice[0]][i]:
                            self.dice_used[self.dice[0]][i] = True
                            self.doubles_played_count += 1
                            die_marked_successfully = True
                            break
                    if not die_marked_successfully:
                        print(
                            f"{self.log_prefix}APPLY_MOVES ERROR: Double roll, tried to use {actual_die_val_for_segment}, but all 4 instances already marked or die mismatch. dice_used: {self.dice_used}")
                else:
                    print(
                        f"{self.log_prefix}APPLY_MOVES ERROR: Double roll ({self.dice[0]}), but segment die {actual_die_val_for_segment} doesn't match.")
            else:
                if actual_die_val_for_segment in self.dice_used:
                    if not self.dice_used[actual_die_val_for_segment]:
                        self.dice_used[actual_die_val_for_segment] = True
                        die_marked_successfully = True
                    else:
                        print(
                            f"{self.log_prefix}APPLY_MOVES WARN: Non-double, die {actual_die_val_for_segment} was already marked as used. dice_used: {self.dice_used}")
                else:
                    print(
                        f"{self.log_prefix}APPLY_MOVES ERROR: Die {actual_die_val_for_segment} not in self.dice_used keys ({list(self.dice_used.keys())}). Original roll: {self.dice}")

            if not die_marked_successfully and (
                    1 <= actual_die_val_for_segment <= 6):
                print(
                    f"{self.log_prefix}APPLY_MOVES CRITICAL: Failed to mark die {actual_die_val_for_segment} as used. This will likely break turn logic.")

            if is_entering_from_bar:
                self.bar[player] -= 1
            else:
                self.board[start_pip_idx][1] -= 1
                if self.board[start_pip_idx][1] == 0:
                    self.board[start_pip_idx][0] = None

            if is_bearing_off:
                self.borne_off[player] += 1
            else:
                landing_pip_idx = int(end_pip_val)
                opponent = self.get_opponent(player)
                target_owner, target_checkers_count = self.board[landing_pip_idx]

                if target_owner == opponent and target_checkers_count == 1:
                    self.board[landing_pip_idx] = [player, 1]
                    self.bar[opponent] += 1
                else:
                    self.board[landing_pip_idx][0] = player
                    self.board[landing_pip_idx][1] += 1

            print(
                f"{self.log_prefix} After segment ({start_pip_val}->{end_pip_val}), die {actual_die_val_for_segment} marked. dice_used: {self.dice_used}, doubles_played: {self.doubles_played_count}")

        if self.borne_off.get(player, 0) == MAX_CHECKERS_PER_PLAYER:
            self.winner = player
            print(f"{self.log_prefix}WINNER DETECTED: P{self.winner} has borne off all checkers.")
            return

        all_dice_used_or_no_further_moves_possible = False

        if is_original_roll_double:
            if self.doubles_played_count == 4:
                all_dice_used_or_no_further_moves_possible = True
            else:
                remaining_double_dice_for_check = [self.dice[0]] * (4 - self.doubles_played_count)
                if not self.get_possible_moves(player, remaining_double_dice_for_check, self.board, self.bar):
                    all_dice_used_or_no_further_moves_possible = True
        else:
            if all(self.dice_used.values()):
                all_dice_used_or_no_further_moves_possible = True
            else:
                unused_dice_values = [d_val for d_val, is_used in self.dice_used.items() if not is_used]
                if not self.get_possible_moves(player, unused_dice_values, self.board, self.bar):
                    all_dice_used_or_no_further_moves_possible = True

        if all_dice_used_or_no_further_moves_possible:
            if self.winner is None:
                print(
                    f"{self.log_prefix}APPLY_MOVES: All dice used or no more moves possible. Switching player. dice_used: {self.dice_used}")
                self.switch_player()
        else:
            print(
                f"{self.log_prefix}APPLY_MOVES: P{player} turn continues. Some dice unplayed and playable. dice_used: {self.dice_used}")

    def switch_player(self):
        if self.current_player is None: return
        self.current_player = self.get_opponent(self.current_player)
        self.dice = []
        self.dice_used = {}
        self.doubles_played_count = 0
        self._update_log_prefix()
        print(f"{self.log_prefix}SWITCH_PLAYER: To P{self.current_player}. Dice cleared, ready for roll.")

    def get_state(self):
        return {
            "board": self.board,
            "bar": self.bar,
            "borne_off": self.borne_off,
            "current_player": self.current_player,
            "dice": self.dice,
            "dice_used": self.dice_used,
            "winner": self.winner,
            "first_roll_made": self.first_roll_made
        }

    def get_possible_moves(self, player, current_dice_values, current_board_state, current_bar_state):
        bar_to_use_in_recursion = {int(k) if isinstance(k, str) else k: v for k, v in current_bar_state.items()}

        if not current_dice_values: return []

        initial_dice_list_for_recursion = []
        is_double_scenario = len(current_dice_values) == 2 and current_dice_values[0] == current_dice_values[1]

        if is_double_scenario:
            initial_dice_list_for_recursion = [current_dice_values[0]] * 4
        else:
            initial_dice_list_for_recursion = list(current_dice_values)

        found_sequences_with_dice_info = self._get_possible_moves_recursive(
            player,
            initial_dice_list_for_recursion,
            current_board_state,
            bar_to_use_in_recursion,
            []
        )

        if not found_sequences_with_dice_info: return []

        valid_found_sequences = [seq for seq in found_sequences_with_dice_info if seq]
        if not valid_found_sequences: return []

        max_dice_used_in_any_sequence = max(len(seq) for seq in valid_found_sequences)
        optimal_sequences_by_dice_count = [seq for seq in valid_found_sequences if
                                           len(seq) == max_dice_used_in_any_sequence]

        final_move_sequences_tuples_only = [[(mf, mt) for mf, mt, du_unused in seq] for seq in
                                            optimal_sequences_by_dice_count]

        unique_final_sequences = []
        for seq_tuples in final_move_sequences_tuples_only:
            if seq_tuples not in unique_final_sequences:
                unique_final_sequences.append(seq_tuples)

        return unique_final_sequences

    def _get_possible_moves_recursive(self, player, dice_still_to_play, board_state, bar_state_int_keys,
                                      current_path_taken):

        possible_next_individual_moves = []
        at_least_one_move_found_this_level = False

        unique_dice_values_to_evaluate = sorted(list(set(dice_still_to_play)), reverse=True)

        opponent = self.get_opponent(player)
        home_range_for_player = self.get_player_home_board_range(player)

        if bar_state_int_keys.get(player, 0) > 0:
            for die_val in unique_dice_values_to_evaluate:
                dest_pip_from_bar = (NUM_POINTS - die_val) if player == PLAYER_X else (die_val - 1)

                if 0 <= dest_pip_from_bar < NUM_POINTS:
                    target_owner, target_checkers_count = board_state[dest_pip_from_bar]
                    if not (target_owner == opponent and target_checkers_count > 1):
                        possible_next_individual_moves.append(('BAR', dest_pip_from_bar, die_val))
                        at_least_one_move_found_this_level = True

        else:
            can_bear_off_now = self.all_checkers_in_home_state(player, board_state, bar_state_int_keys)

            for die_val in unique_dice_values_to_evaluate:
                for p_idx in range(NUM_POINTS):
                    if board_state[p_idx][0] == player and board_state[p_idx][1] > 0:
                        dest_pip_std = self.get_target_point(player, p_idx, die_val)
                        if 0 <= dest_pip_std < NUM_POINTS:
                            target_owner_std, target_checkers_std = board_state[dest_pip_std]
                            if not (target_owner_std == opponent and target_checkers_std > 1):
                                possible_next_individual_moves.append((p_idx, dest_pip_std, die_val))
                                at_least_one_move_found_this_level = True

                        if can_bear_off_now and p_idx in home_range_for_player:
                            required_pip_for_exact_bear_off = (p_idx + 1) if player == PLAYER_X else (
                                        NUM_POINTS - p_idx)

                            if die_val == required_pip_for_exact_bear_off:
                                possible_next_individual_moves.append((p_idx, 'OFF', die_val))
                                at_least_one_move_found_this_level = True
                            elif die_val > required_pip_for_exact_bear_off:
                                is_furthest_checker = True
                                if player == PLAYER_X:
                                    for hp_idx in range(p_idx + 1, home_range_for_player.stop):
                                        if hp_idx in home_range_for_player and board_state[hp_idx][0] == player and \
                                                board_state[hp_idx][1] > 0:
                                            is_furthest_checker = False;
                                            break
                                else:
                                    for lp_idx in range(p_idx - 1, home_range_for_player.start - 1, -1):
                                        if lp_idx in home_range_for_player and board_state[lp_idx][0] == player and \
                                                board_state[lp_idx][1] > 0:
                                            is_furthest_checker = False;
                                            break
                                if is_furthest_checker:
                                    possible_next_individual_moves.append((p_idx, 'OFF', die_val))
                                    at_least_one_move_found_this_level = True

        if not dice_still_to_play or not at_least_one_move_found_this_level:
            return [current_path_taken] if current_path_taken else []

        all_completed_paths_from_this_point = []
        if not possible_next_individual_moves and current_path_taken:
            all_completed_paths_from_this_point.append(current_path_taken)

        for move_from, move_to, die_val_used_for_move in possible_next_individual_moves:
            if die_val_used_for_move not in dice_still_to_play: continue

            temp_dice_remaining_for_next_call = list(dice_still_to_play)
            temp_dice_remaining_for_next_call.remove(die_val_used_for_move)

            board_after_move, bar_after_move, _ = self._apply_hypothetical_move_sequence(
                player,
                [(move_from, move_to)],
                board_state,
                bar_state_int_keys,
                {}
            )

            recursive_paths = self._get_possible_moves_recursive(
                player,
                temp_dice_remaining_for_next_call,
                board_after_move,
                bar_after_move,
                current_path_taken + [(move_from, move_to, die_val_used_for_move)]
            )
            all_completed_paths_from_this_point.extend(recursive_paths)

        if current_path_taken and not possible_next_individual_moves and not any(
                path == current_path_taken for path in all_completed_paths_from_this_point):
            all_completed_paths_from_this_point.append(current_path_taken)
        elif not current_path_taken and not all_completed_paths_from_this_point and not possible_next_individual_moves:
            return []

        final_unique_paths = []
        for p_seq in all_completed_paths_from_this_point:
            if p_seq and p_seq not in final_unique_paths:
                final_unique_paths.append(p_seq)
        return final_unique_paths

    def _apply_hypothetical_move_sequence(self, player, move_sequence_tuples, board_orig, bar_orig_int_keys,
                                          borne_off_dummy):
        temp_board = copy.deepcopy(board_orig)
        temp_bar = copy.deepcopy(bar_orig_int_keys)

        opponent = self.get_opponent(player)

        for start_pip_val, end_pip_val in move_sequence_tuples:
            is_entering_from_bar = (start_pip_val == 'BAR')
            is_bearing_off = (end_pip_val == 'OFF')

            if is_entering_from_bar:
                temp_bar[player] -= 1
            else:
                start_pip_idx = int(start_pip_val)
                temp_board[start_pip_idx][1] -= 1
                if temp_board[start_pip_idx][1] == 0:
                    temp_board[start_pip_idx][0] = None

            if not is_bearing_off:
                landing_pip_idx = int(end_pip_val)
                target_owner, target_checkers_count = temp_board[landing_pip_idx]

                if target_owner == opponent and target_checkers_count == 1:
                    temp_board[landing_pip_idx] = [player, 1]
                    temp_bar[opponent] += 1
                else:
                    temp_board[landing_pip_idx][0] = player
                    temp_board[landing_pip_idx][1] += 1

        return temp_board, temp_bar, {}