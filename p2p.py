import socket
import json
import random
import threading
import time
import copy
import traceback
from game_logic import BackgammonGame , PLAYER_X , PLAYER_O , NUM_POINTS
import ai_player

DEFAULT_PORT = 65433
BUFFER_SIZE = 4096

peer_socket = None
game_instance = BackgammonGame ()
my_player_id = None
opponent_player_id = None
my_player_symbol = None
opponent_player_symbol = None

my_first_roll_value = None
opponent_first_roll_value = None
first_roll_event = threading.Event ()
game_started_event = threading.Event ()
global is_local_player_ai
is_local_player_ai = False


def get_local_ip() :
    s = socket.socket ( socket.AF_INET , socket.SOCK_DGRAM )
    try :
        s.connect ( ('10.255.255.255' , 1) )
        ip = s.getsockname ()[0]
    except Exception :
        ip = '127.0.0.1'
    finally :
        s.close ()
    return ip


def format_player_id_display(player_id_int) :
    if player_id_int == PLAYER_X :
        return "X"
    elif player_id_int == PLAYER_O :
        return "O"
    return "Unknown"


def print_board_p2p() :
    state = game_instance.get_state ()
    if not state :
        print ( "Waiting for game state..." )
        return

    board = state['board']
    bar = state['bar']
    borne_off = state['borne_off']
    current_player_id_from_state = state['current_player']
    dice_val = state['dice']
    winner = state['winner']

    my_char_display = my_player_symbol if my_player_symbol else "?"
    opponent_char_display = opponent_player_symbol if opponent_player_symbol else "?"

    print ( "\n" + "=" * 60 )
    if my_player_id is not None :
        ai_status = "(AI)" if is_local_player_ai and game_instance.current_player == my_player_id else ""
        print ( f"You are Player {my_char_display} (ID: {my_player_id}) {ai_status}" )
    else :
        print ( "Player ID not yet assigned." )

    s_indices_top = " " + " ".join ( f"{i:^3}" for i in range ( 12 , 18 ) ) + "   BAR   " + " ".join (
        f"{i:^3}" for i in range ( 18 , 24 ) ) + " "
    print ( s_indices_top )
    separator_line = "+" + "-" * (3 * 6 + 5) + "+" + "-" * 7 + "+" + "-" * (3 * 6 + 5) + "+"
    print ( separator_line )

    max_checkers_on_point_display = 5

    for r in range ( max_checkers_on_point_display ) :
        s_top_quad_left = []
        s_top_quad_right = []

        for i in range ( 12 , 18 ) :
            owner , count = board[i]
            char_to_print = ' '
            if count > r :
                char_to_print = format_player_id_display ( owner )
            elif count == 0 and r == max_checkers_on_point_display // 2 :
                char_to_print = '.'
            s_top_quad_left.append ( f" {char_to_print} " )

        for i in range ( 18 , 24 ) :
            owner , count = board[i]
            char_to_print = ' '
            if count > r :
                char_to_print = format_player_id_display ( owner )
            elif count == 0 and r == max_checkers_on_point_display // 2 :
                char_to_print = '.'
            s_top_quad_right.append ( f" {char_to_print} " )

        bar_display_str = "       "
        bar_int_keys = {int ( k ) : v for k , v in bar.items ()}
        if r == 0 :
            bar_o_text = f"O:{bar_int_keys.get ( PLAYER_O , 0 )}";
            bar_display_str = f"{bar_o_text:^7}"
        elif r == 1 :
            bar_x_text = f"X:{bar_int_keys.get ( PLAYER_X , 0 )}";
            bar_display_str = f"{bar_x_text:^7}"

        print ( " ".join ( s_top_quad_left ) + " |" + bar_display_str + "| " + " ".join ( s_top_quad_right ) )

    if my_player_id == PLAYER_X :
        print ( "v" * (3 * 6 + 5) + "v" + "v" * 7 + "v" + "v" * (3 * 6 + 5) + "v" )
    elif my_player_id == PLAYER_O :
        print ( "^" * (3 * 6 + 5) + "^" + "^" * 7 + "^" + "^" * (3 * 6 + 5) + "^" )
    else :
        print ( "~" * (3 * 6 + 5) + "~" + "~" * 7 + "~" + "~" * (3 * 6 + 5) + "~" )

    for r in range ( max_checkers_on_point_display - 1 , -1 , -1 ) :
        s_bot_quad_left = []
        s_bot_quad_right = []

        for i in range ( 11 , 5 , -1 ) :
            owner , count = board[i]
            char_to_print = ' '
            if count > r :
                char_to_print = format_player_id_display ( owner )
            elif count == 0 and r == max_checkers_on_point_display // 2 :
                char_to_print = '.'
            s_bot_quad_left.append ( f" {char_to_print} " )

        for i in range ( 5 , -1 , -1 ) :
            owner , count = board[i]
            char_to_print = ' '
            if count > r :
                char_to_print = format_player_id_display ( owner )
            elif count == 0 and r == max_checkers_on_point_display // 2 :
                char_to_print = '.'
            s_bot_quad_right.append ( f" {char_to_print} " )

        borne_off_placeholder = "       "
        if r == max_checkers_on_point_display - 1 : borne_off_placeholder = " Bear  "
        if r == max_checkers_on_point_display - 2 : borne_off_placeholder = " Off   "

        print ( " ".join ( s_bot_quad_left ) + " |" + borne_off_placeholder + "| " + " ".join ( s_bot_quad_right ) )

    print ( separator_line )
    s_indices_bot = " " + " ".join ( f"{i:^3}" for i in range ( 11 , 5 , -1 ) ) + "         " + " ".join (
        f"{i:^3}" for i in range ( 5 , -1 , -1 ) ) + " "
    print ( s_indices_bot )

    borne_off_int_keys = {int ( k ) : v for k , v in borne_off.items ()}
    my_b_off = borne_off_int_keys.get ( my_player_id , 0 ) if my_player_id is not None else borne_off_int_keys.get (
        PLAYER_X , 0 )
    opp_b_off = borne_off_int_keys.get ( opponent_player_id ,
                                         0 ) if opponent_player_id is not None else borne_off_int_keys.get ( PLAYER_O ,
                                                                                                             0 )

    print ( f"Borne Off - You ({my_char_display}): {my_b_off}, Opponent ({opponent_char_display}): {opp_b_off}" )

    current_player_char_from_state = format_player_id_display (
        current_player_id_from_state ) if current_player_id_from_state is not None else "N/A"
    print ( f"Current Turn: Player {current_player_char_from_state} (ID: {current_player_id_from_state})" )
    if dice_val : print ( f"Dice on Table: {dice_val}" )

    if winner is not None :
        winner_char = format_player_id_display ( winner )
        print ( f"!!! GAME OVER! Player {winner_char} (ID: {winner}) WINS !!!" )
    print ( "=" * 60 + "\n" )


def send_message_to_peer(message_dict) :
    global peer_socket
    if peer_socket :
        try :
            peer_socket.sendall ( (json.dumps ( message_dict ) + "\n").encode ( 'utf-8' ) )
        except socket.error as e :
            print ( f"Error sending message: {e}. Opponent may have disconnected." )
            peer_socket = None
            handle_disconnect ()
        except Exception as e :
            print ( f"An unexpected error occurred while sending: {e}" )
            peer_socket = None
            handle_disconnect ()


def listen_to_peer() :
    global peer_socket
    buffer = ""
    while peer_socket :
        try :
            data = peer_socket.recv ( BUFFER_SIZE )
            if not data :
                print ( "Opponent disconnected (received no data)." )
                peer_socket = None
                handle_disconnect ()
                break

            buffer += data.decode ( 'utf-8' )
            while "\n" in buffer :
                message_str , buffer = buffer.split ( "\n" , 1 )
                if not message_str.strip () :
                    continue
                message = json.loads ( message_str )
                handle_incoming_message ( message )
        except socket.timeout :
            continue
        except ConnectionResetError :
            print ( "Opponent connection reset." )
            peer_socket = None
            handle_disconnect ()
            break
        except json.JSONDecodeError :
            print ( f"Invalid JSON received: '{message_str[:100]}...'" )
        except Exception as e :
            print ( f"Error in listener thread: {e}" )
            traceback.print_exc ()
            peer_socket = None
            handle_disconnect ()
            break
    print ( "Listener thread stopped." )


def handle_disconnect() :
    global game_instance , peer_socket
    if game_instance.winner is None :
        print ( "Opponent has disconnected. Game cannot continue." )
    if peer_socket :
        try :
            peer_socket.close ()
        except :
            pass
        peer_socket = None
    first_roll_event.set ()
    game_started_event.set ()


def handle_incoming_message(message) :
    global game_instance , my_player_id , opponent_player_id , my_player_symbol , opponent_player_symbol
    global my_first_roll_value , opponent_first_roll_value

    msg_type = message.get ( "type" )

    if msg_type == "identity" :
        my_player_id = message["assigned_player_id"]
        my_player_symbol = message["assigned_symbol"]
        opponent_player_id = PLAYER_X if my_player_id == PLAYER_O else PLAYER_O
        opponent_player_symbol = "X" if my_player_symbol == "O" else "O"
        print (
            f"Identity received: You are Player {my_player_symbol} (ID: {my_player_id}). Opponent is Player {opponent_player_symbol}." )

        my_first_roll_value = random.randint ( 1 , 6 )
        print ( f"You rolled a {my_first_roll_value} for first turn determination." )
        send_message_to_peer ( {
            "type" : "first_roll_exchange" ,
            "player_id" : my_player_id ,
            "roll" : my_first_roll_value
        } )

    elif msg_type == "first_roll_exchange" :
        peer_id = message["player_id"]
        roll_value = message["roll"]
        print ( f"Player {format_player_id_display ( peer_id )} (ID: {peer_id}) rolled a {roll_value} for first turn." )

        if peer_id == opponent_player_id :
            opponent_first_roll_value = roll_value
        elif peer_id == my_player_id :
            my_first_roll_value = roll_value

        if my_first_roll_value is not None and opponent_first_roll_value is not None :
            if my_first_roll_value == opponent_first_roll_value :
                print ( "First rolls were a tie! Re-rolling..." )
                my_first_roll_value = random.randint ( 1 , 6 )
                opponent_first_roll_value = None
                print ( f"You re-rolled a {my_first_roll_value}." )
                send_message_to_peer ( {
                    "type" : "first_roll_exchange" ,
                    "player_id" : my_player_id ,
                    "roll" : my_first_roll_value
                } )
            else :
                if my_player_id == PLAYER_X :
                    actual_player_x_roll = my_first_roll_value
                    actual_player_o_roll = opponent_first_roll_value
                else :
                    actual_player_x_roll = opponent_first_roll_value
                    actual_player_o_roll = my_first_roll_value

                first_player = PLAYER_X if actual_player_x_roll > actual_player_o_roll else PLAYER_O
                initial_dice = sorted ( [actual_player_x_roll , actual_player_o_roll] , reverse=True )

                game_instance.current_player = first_player
                game_instance.dice = list ( initial_dice )
                if initial_dice[0] == initial_dice[1] :
                    game_instance.dice_used = {initial_dice[0] : [False , False , False , False]}
                else :
                    game_instance.dice_used = {val : False for val in initial_dice}
                game_instance.first_roll_made = True
                game_instance._update_log_prefix ()

                print ( f"Player {format_player_id_display ( first_player )} wins the first roll and starts." )
                print ( f"Initial dice for the first turn: {game_instance.dice}" )
                first_roll_event.set ()
                game_started_event.set ()

    elif msg_type == "action_roll_dice" :
        if message["player_id"] == opponent_player_id :
            print (
                f"Opponent (Player {format_player_id_display ( opponent_player_id )}) rolled: {message['rolled_dice']}" )
            game_instance.current_player = opponent_player_id
            game_instance.dice = list ( message['rolled_dice'] )
            if game_instance.dice[0] == game_instance.dice[1] :
                game_instance.dice_used = {game_instance.dice[0] : [False , False , False , False]}
            else :
                game_instance.dice_used = {val : False for val in game_instance.dice}
            game_instance.doubles_played_count = 0
            game_instance._update_log_prefix ()
            print_board_p2p ()
        else :
            print ( f"[DEBUG] Received own dice roll? {message}. Current dice: {game_instance.dice}" )

    elif msg_type == "action_submit_moves" :
        if message["player_id"] == opponent_player_id :
            moves_raw = message["moves"]
            parsed_moves = []
            try :
                for m_part in moves_raw :
                    start = m_part[0] if m_part[0] in ['BAR' , 'OFF'] else int ( m_part[0] )
                    end = m_part[1] if m_part[1] in ['BAR' , 'OFF'] else int ( m_part[1] )
                    parsed_moves.append ( (start , end) )
            except (ValueError , TypeError , IndexError) as e :
                print ( f"ERROR: Malformed move data from opponent: {moves_raw} - {e}" )
                return

            print (
                f"Opponent (Player {format_player_id_display ( opponent_player_id )}) submitted moves: {parsed_moves}" )

            if game_instance.current_player != opponent_player_id :
                print (
                    f"WARNING: Received moves from P{format_player_id_display ( opponent_player_id )}, but current local player is P{format_player_id_display ( game_instance.current_player )}. Adjusting." )
                game_instance.current_player = opponent_player_id

            is_valid_opponent_move = game_instance.is_move_valid ( opponent_player_id , parsed_moves )
            if is_valid_opponent_move :
                game_instance.apply_moves ( opponent_player_id , parsed_moves )
                print ( "Opponent's moves applied." )
                print_board_p2p ()
                if game_instance.winner is not None :
                    print ( f"Game Over! Player {format_player_id_display ( game_instance.winner )} wins!" )
                elif game_instance.current_player == my_player_id :
                    print ( "It's your turn!" )
                    if not game_instance.dice :
                        time.sleep ( 0.1 )
                        request_roll_and_send ()
                    else :
                        time.sleep ( 0.1 )
                        make_move_or_pass_and_send ()
            else :
                print (
                    f"!!! WARNING: Opponent (P{format_player_id_display ( opponent_player_id )}) sent invalid moves: {parsed_moves} !!!" )
                print_board_p2p ()

    elif msg_type == "action_pass_turn" :
        if message["player_id"] == opponent_player_id :
            print ( f"Opponent (Player {format_player_id_display ( opponent_player_id )}) passed their turn." )
            if game_instance.current_player != opponent_player_id :
                print (
                    f"WARNING: Received pass from P{format_player_id_display ( opponent_player_id )}, but local current player P{format_player_id_display ( game_instance.current_player )}. Adjusting." )
                game_instance.current_player = opponent_player_id

            if game_instance.is_move_valid ( opponent_player_id , [] ) :
                game_instance.switch_player ()
                print ( "Opponent's pass processed." )
                print_board_p2p ()
                if game_instance.current_player == my_player_id :
                    print ( "It's your turn!" )
                    time.sleep ( 0.1 )
                    request_roll_and_send ()
            else :
                print (
                    f"!!! WARNING: Opponent (P{format_player_id_display ( opponent_player_id )}) passed, but they had available moves locally! !!!" )
                print_board_p2p ()

    elif msg_type == "game_over_notification" :
        winner_id = message["winner_id"]
        print (
            f"!!! Received Game Over notification from opponent! Player {format_player_id_display ( winner_id )} wins! !!!" )
        game_instance.winner = winner_id
        print_board_p2p ()
        handle_disconnect ()

    elif msg_type == "chat" :
        sender_char = format_player_id_display ( message["sender_id"] )
        print ( f"[Chat P{sender_char}]: {message['message_text']}" )

    else :
        print ( f"Unknown message type received: {msg_type} | Content: {message}" )


def request_roll_and_send() :
    global game_instance
    if game_instance.current_player == my_player_id and not game_instance.dice :
        player_type_str = "(AI)" if is_local_player_ai else "(Human/Random)"
        print ( f"Rolling dice for you {player_type_str}..." )
        rolled_dice = game_instance.roll_dice ()
        print ( f"You rolled: {rolled_dice}" )
        send_message_to_peer ( {
            "type" : "action_roll_dice" ,
            "player_id" : my_player_id ,
            "rolled_dice" : rolled_dice
        } )
        print_board_p2p ()
        time.sleep ( 0.1 )
        make_move_or_pass_and_send ()
    elif game_instance.current_player != my_player_id :
        print ( "Not your turn to roll (or waiting for opponent's previous action)." )
    elif game_instance.dice :
        print ( f"You already have dice: {game_instance.dice}. Make your move." )
        make_move_or_pass_and_send ()


def make_move_or_pass_and_send() :
    global game_instance , is_local_player_ai
    if game_instance.current_player != my_player_id or not game_instance.dice :
        return

    temp_game_for_possible_moves = BackgammonGame ()
    temp_game_for_possible_moves.board = copy.deepcopy ( game_instance.board )
    temp_game_for_possible_moves.bar = {int ( k ) : v for k , v in game_instance.bar.items ()}
    temp_game_for_possible_moves.borne_off = {int ( k ) : v for k , v in game_instance.borne_off.items ()}
    temp_game_for_possible_moves.current_player = game_instance.current_player
    temp_game_for_possible_moves.dice = list ( game_instance.dice )
    temp_game_for_possible_moves.dice_used = copy.deepcopy ( game_instance.dice_used )

    possible_move_sequences = temp_game_for_possible_moves.get_possible_moves (
        my_player_id ,
        temp_game_for_possible_moves.dice ,
        temp_game_for_possible_moves.board ,
        temp_game_for_possible_moves.bar
    )

    chosen_sequence_tuples = []
    player_descriptor = f"P{format_player_id_display ( my_player_id )}"

    if possible_move_sequences :
        if is_local_player_ai :
            player_descriptor += " (AI)"
            print ( f"{player_descriptor} is thinking..." )
            current_game_state_for_ai = game_instance.get_state ()
            chosen_sequence_tuples = ai_player.choose_move (
                current_game_state_for_ai ,
                my_player_id ,
                possible_move_sequences
            )

            if chosen_sequence_tuples and chosen_sequence_tuples not in possible_move_sequences :
                print (
                    f"!!! WARNING: {player_descriptor} returned an invalid sequence {chosen_sequence_tuples} not in list of {len ( possible_move_sequences )} valid_sequences. Defaulting to first valid move." )
                chosen_sequence_tuples = possible_move_sequences[0]
            elif not chosen_sequence_tuples and possible_move_sequences :
                print (
                    f"!!! WARNING: {player_descriptor} chose to pass, but moves were available. AI should return a valid move or an empty list if it calculates no moves from given options." )
        else :
            player_descriptor += " (Human/Random)"
            print ( f"{player_descriptor} (randomly) choosing a move..." )
            chosen_sequence_tuples = random.choice ( possible_move_sequences )

        json_safe_sequence = []
        if chosen_sequence_tuples :
            for move_tuple in chosen_sequence_tuples :
                start_val , end_val = move_tuple
                json_safe_sequence.append ( [
                    str ( start_val ) if isinstance ( start_val , int ) else start_val ,
                    str ( end_val ) if isinstance ( end_val , int ) else end_val
                ] )
            print ( f"{player_descriptor} chose to move: {json_safe_sequence} (using dice: {game_instance.dice})" )
        else :
            print ( f"{player_descriptor} chose to pass (no moves in chosen_sequence_tuples)." )

        if chosen_sequence_tuples and game_instance.is_move_valid ( my_player_id , chosen_sequence_tuples ) :
            game_instance.apply_moves ( my_player_id , chosen_sequence_tuples )
            print ( "Moves applied locally." )
            send_message_to_peer ( {
                "type" : "action_submit_moves" ,
                "player_id" : my_player_id ,
                "moves" : json_safe_sequence
            } )
            print_board_p2p ()
            if game_instance.winner is not None :
                print ( f"YOU ({player_descriptor}) WIN! Game Over!" )
                send_message_to_peer ( {
                    "type" : "game_over_notification" ,
                    "winner_id" : my_player_id ,
                } )
                handle_disconnect ()
            elif game_instance.current_player == my_player_id and game_instance.dice :
                print ( f"{player_descriptor} has more moves with the current dice." )
                time.sleep ( 0.1 )
                make_move_or_pass_and_send ()
            elif game_instance.current_player == opponent_player_id :
                print ( f"Turn passed to opponent P{format_player_id_display ( opponent_player_id )}." )

        elif not chosen_sequence_tuples :
            print ( f"{player_descriptor} has no chosen moves or AI passed. Validating pass." )
            pass_turn_and_send ()
        else :
            print (
                f"!!! ERROR ({player_descriptor}): Auto-chosen/AI move was invalid by local check: {chosen_sequence_tuples} with {game_instance.dice}. Passing." )
            pass_turn_and_send ()
    else :
        print ( f"No possible moves for {player_descriptor}. Passing turn." )
        pass_turn_and_send ()


def pass_turn_and_send() :
    global game_instance
    player_descriptor = f"P{format_player_id_display ( my_player_id )}"
    if is_local_player_ai :
        player_descriptor += " (AI)"
    else :
        player_descriptor += " (Human/Random)"

    if game_instance.current_player != my_player_id :
        return

    if game_instance.is_move_valid ( my_player_id , [] ) :
        current_dice_before_pass = list ( game_instance.dice )
        game_instance.switch_player ()
        print ( f"{player_descriptor} passed turn locally (dice were {current_dice_before_pass})." )
        send_message_to_peer ( {
            "type" : "action_pass_turn" ,
            "player_id" : my_player_id
        } )
        print_board_p2p ()
        print ( f"Turn passed to opponent P{format_player_id_display ( game_instance.current_player )}." )
    else :
        print (
            f"!!! ERROR ({player_descriptor}): Tried to pass, but moves are available according to is_move_valid([], ...). Check logic. !!!" )
        print_board_p2p ()


def connect_as_host(port=DEFAULT_PORT) :
    global peer_socket , my_player_id , opponent_player_id , my_player_symbol , opponent_player_symbol , game_instance

    my_player_id = PLAYER_X
    my_player_symbol = "X"
    opponent_player_id = PLAYER_O
    opponent_player_symbol = "O"
    game_instance = BackgammonGame ()

    server_sock = socket.socket ( socket.AF_INET , socket.SOCK_STREAM )
    server_sock.setsockopt ( socket.SOL_SOCKET , socket.SO_REUSEADDR , 1 )
    try :
        host_ip = get_local_ip ()
        server_sock.bind ( (host_ip , port) )
        server_sock.listen ( 1 )
        player_type_str = "(AI)" if is_local_player_ai else "(Human/Random)"
        print ( f"Hosting on {host_ip}:{port} as Player X {player_type_str}. Waiting for opponent..." )

        conn , addr = server_sock.accept ()
        peer_socket = conn
        peer_socket.settimeout ( 5 )
        print ( f"Opponent connected from {addr}" )

        send_message_to_peer ( {
            "type" : "identity" ,
            "assigned_player_id" : opponent_player_id ,
            "assigned_symbol" : opponent_player_symbol
        } )

        threading.Thread ( target=listen_to_peer , daemon=True ).start ()

        global my_first_roll_value
        my_first_roll_value = random.randint ( 1 , 6 )
        print ( f"You (Host - P{my_player_symbol}) rolled a {my_first_roll_value} for first turn determination." )
        send_message_to_peer ( {
            "type" : "first_roll_exchange" ,
            "player_id" : my_player_id ,
            "roll" : my_first_roll_value
        } )
        return True
    except Exception as e :
        print ( f"Error hosting game: {e}" )
        traceback.print_exc ()
        if peer_socket : peer_socket.close ()
        if server_sock : server_sock.close ()
        return False


def connect_as_joiner(host_ip , port=DEFAULT_PORT) :
    global peer_socket , game_instance
    game_instance = BackgammonGame ()
    try :
        player_type_str = "(AI)" if is_local_player_ai else "(Human/Random)"
        print ( f"Attempting to connect to {host_ip}:{port} as Player O {player_type_str}..." )
        sock = socket.socket ( socket.AF_INET , socket.SOCK_STREAM )
        sock.connect ( (host_ip , port) )
        peer_socket = sock
        peer_socket.settimeout ( 5 )
        print ( "Connected to host!" )

        threading.Thread ( target=listen_to_peer , daemon=True ).start ()
        return True
    except Exception as e :
        print ( f"Error joining game: {e}" )
        traceback.print_exc ()
        if peer_socket : peer_socket.close ()
        return False


def game_loop() :
    global game_instance
    print ( "Waiting for first roll determination to complete..." )
    if not first_roll_event.wait ( timeout=30 ) :
        print ( "Timeout waiting for first roll determination. Exiting." )
        handle_disconnect ()
        return

    if not peer_socket :
        print ( "Game cannot start, opponent disconnected during setup." )
        return

    print ( "--- Game Starting! ---" )
    print_board_p2p ()

    if game_instance.current_player == my_player_id :
        player_type_str = "(AI)" if is_local_player_ai else "(Human/Random)"
        print ( f"You {player_type_str} start the first turn with the initial dice: {game_instance.dice}." )
        time.sleep ( 0.2 )
        make_move_or_pass_and_send ()
    else :
        print ( "Opponent starts the first turn. Waiting for their move..." )

    while game_instance.winner is None and peer_socket is not None :
        try :
            time.sleep ( 1 )
        except EOFError :
            time.sleep ( 1 )
        except KeyboardInterrupt :
            print ( "\nKeyboard interrupt. Exiting game." )
            if peer_socket :
                try :
                    send_message_to_peer ( {"type" : "chat" , "sender_id" : my_player_id ,
                                            "message_text" : "Opponent left (KeyboardInterrupt)."} )
                except :
                    pass
            handle_disconnect ()
            break

    if game_instance.winner is not None :
        print ( f"Game has ended. Winner: Player {format_player_id_display ( game_instance.winner )}" )
    elif peer_socket is None :
        print ( "Game has ended due to disconnection." )
    print ( "Exiting game loop." )


if __name__ == "__main__" :


    print ( "Welcome to P2P Backgammon!" )

    mode = ""
    while mode not in ['host' , 'join'] :
        mode = input ( "Do you want to (host) a game or (join) an existing game? " ).strip ().lower ()

    ai_choice = input ( "Is the local player an AI? (yes/no default: no): " ).strip ().lower ()
    if ai_choice == 'yes' :
        is_local_player_ai = True
        print ( "Local player will be controlled by AI." )
    else :
        is_local_player_ai = False
        print ( "Local player will be controlled by Human (current: random moves)." )

    success = False
    if mode == 'host' :
        port_str = input ( f"Enter port to host on (default {DEFAULT_PORT}): " ).strip ()
        port = int ( port_str ) if port_str.isdigit () else DEFAULT_PORT
        success = connect_as_host ( port )
    else :
        host_ip = input ( "Enter host IP address: " ).strip ()
        port_str = input ( f"Enter host port (default {DEFAULT_PORT}): " ).strip ()
        port = int ( port_str ) if port_str.isdigit () else DEFAULT_PORT
        success = connect_as_joiner ( host_ip , port )

    if success :
        try :
            game_loop ()
        except Exception as e :
            print ( f"An error occurred in the main game loop: {e}" )
            traceback.print_exc ()
        finally :
            if peer_socket :
                print ( "Closing peer socket." )
                try :
                    peer_socket.shutdown ( socket.SHUT_RDWR )
                except :
                    pass
                try :
                    peer_socket.close ()
                except :
                    pass
            print ( "Game finished. Goodbye!" )
    else :
        print ( "Failed to start P2P game. Exiting." )