from sys import argv
from getkey import getkey

def parse_game(game_file_path: str) -> dict: # Fonction 1
    '''
    Depuis un nom de ficher de sauvegarde donné,
    retourne une dictionnaire dans la configuration de:
    - La taille de la grilles
    - Les positions des voitures
    - Le nombre maximal de coup
    '''
    with open(game_file_path, encoding="utf-8") as info_file:
        info_file_lst = [line for line in info_file]

    parking = [list(row.strip()[1:-1]) for row in info_file_lst[1:-2]] 
    cars = {}

    for y, row in enumerate(parking):
        for x, col in enumerate(row):

            if col in cars:
                cars[col][2] += 1 
            elif col != '.':
                cars[col] = new_car_infos(parking, x, y)

    return {
        'width': len(parking[0]),
        'height': len(parking),
        'cars': [cars[key] for key in sorted(cars.keys())],
        'max_moves': int(info_file_lst[-1])
    }

def new_car_infos(parking, x, y):
    '''
    Depuis une matrice du parking et des positions x et y,
    détermine l'orientation de la voiture à ces coordonnées
    et ajoute les infos pour qu'elle puisse être jouter dans 
    le tableau des voitures
    '''
    orientation = None

    if x + 1 < len(parking[y]) and parking[y][x] == parking[y][x + 1]:
        orientation = 'h'

    if y + 1 < len(parking) and parking[y][x] == parking[y + 1][x]:
        orientation = 'v'

    return [(x, y), orientation, 1]

def get_game_str(game: dict, current_move_number: int) -> str: # Fonction 2
    game_matrix = [
        [
            "." for _ in range(game['width'])
        ] for _ in range(game['height'])
    ]

    color_index = 7

    for car_position, car in enumerate(game['cars']):
        for coord in get_car_coords(car):
            game_matrix[coord[0]][coord[1]] = (
                    '\u001b[4' + str(color_index) + 'm' 
                    + str(chr(ord('A') + car_position)) 
                    + '\u001b[0m'
                )

        color_index += 1

        if color_index >= 7:
            color_index = 1

    frame = '\n'.join([''.join(line)for line in game_matrix])
    return (
        frame + 
        '\nMoves remains: ' + str(current_move_number) + 
        '\nMax moves: ' + str(game['max_moves'])
    )

def get_car_coords(car):

    car_coords = []

    if car[1] == 'h':
        for x in range(car[2]):
            car_coords.append((car[0][1], car[0][0] + x))
    elif car[1] == 'v':
        for y in range(car[2]):
            car_coords.append((car[0][1] + y, car[0][0]))

    return car_coords

def move_car(game: dict, car_index: int, direction: str) -> bool: # Fonction 3
    direction_function_dict = {
        'UP': move_UP,
        'DOWN': move_DOWN,
        'LEFT': move_LEFT,
        'RIGHT': move_RIGHT,
    }

    return direction_function_dict[direction](game, car_index)

def move_UP(game: dict, car_index: int):
    if (
        game['cars'][car_index][1] == 'v'
        and game['cars'][car_index][0][1] != 0
        and (
            game['cars'][car_index][0][1] - 1, 
            game['cars'][car_index][0][0]
        ) not in used_coords(game)
    ):
        game['cars'][car_index][0] = (
            game['cars'][car_index][0][0], 
            game['cars'][car_index][0][1] - 1
        )
        return True
    else:
        return False

def move_DOWN(game: dict, car_index: int):
    if (
        game['cars'][car_index][1] == 'v'
        and (
            game['cars'][car_index][0][1] + 
            game['cars'][car_index][2]
        ) != game['height'] 
        and (
            game['cars'][car_index][0][1] + game['cars'][car_index][2], 
            game['cars'][car_index][0][0]
        ) not in used_coords(game)
    ):
        game['cars'][car_index][0] = (
                game['cars'][car_index][0][0], 
                game['cars'][car_index][0][1] + 1
        )
        return True
    else:
        return False

def move_LEFT(game: dict, car_index: int):
    if (
        game['cars'][car_index][1] == 'h'
        and game['cars'][car_index][0][0]!= 0 
        and (
            game['cars'][car_index][0][1], 
            game['cars'][car_index][0][0] - 1
        ) not in used_coords(game)
    ):
        game['cars'][car_index][0] = (
            game['cars'][car_index][0][0] - 1, 
            game['cars'][car_index][0][1]
        )
        return True
    else:
        return False

def move_RIGHT(game: dict, car_index: int):
    if (
        game['cars'][car_index][1] == 'h'
        and (
            game['cars'][car_index][0][0] + 
            game['cars'][car_index][2]
        ) != game['width'] 
        and (
            game['cars'][car_index][0][1], 
            game['cars'][car_index][0][0] + game['cars'][car_index][2]
        ) not in used_coords(game)
    ):
        game['cars'][car_index][0] = (
            game['cars'][car_index][0][0] + 1, 
            game['cars'][car_index][0][1]
        )
        return True
    else:
        return False



def used_coords(game):
    used_coords = []

    for car in game['cars']:
        for coord in get_car_coords(car):
            used_coords.append(coord)

    return(used_coords)

def is_win(game: dict) -> bool: # Fonction 4
    return bool(
        game['cars'][0][0][0] + game['cars'][0][2] == game['width']
    )

def play_game(game: dict) -> int: # Fonction 5
    moves_remains = game['max_moves']
    car_to_move, move = 0, None

    while not is_win(game) and moves_remains:
        print(get_game_str(game, moves_remains))

        while not move:
            user_input = getkey()

            if len(user_input) == 1:
                if (
                    ord('A') + ord(user_input) >= 0 
                    and (
                        ord(user_input) - ord('A') + 1
                    ) <= len(game['cars'])
                ) :
                    car_to_move = ord(user_input) - ord('A')

            elif(user_input in ('UP', 'DOWN', 'LEFT', 'RIGHT')):
                move = user_input
                
            elif user_input == 'ESCAPE':
                return 2

        if move_car(game, car_to_move, move):
            moves_remains -= 1

        move = None


    if is_win(game):
        return 0
    else:
        return 1

if __name__ == '__main__':
    print(get_car_coords([(0, 2), 'h', 2]))

    res = play_game(parse_game(argv[1]))

    print("Fin du programme", res)
