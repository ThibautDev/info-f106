from sys import argv
from getkey import getkey

def parse_game(game_file_path: str) -> dict: # Fonction 1
    """Analyse le fichier contenant les infos de la partie contenues à l'emplacement game_file_path.
    Retourne un dictionnaire contenant :
    * la longueur du parking ('width')
    * la largeur du parking ('height')
    * une liste de la position initiale de toutes les voitures ('cars')
    * le nombre de coups maximal pour gagner la partie ('max_moves')"""

    with open(game_file_path, encoding="utf-8") as info_file:
        info_file_lst = [line for line in info_file]

    parking = [list(row.strip()[1:-1]) for row in info_file_lst[1:-2]] # Exclure les bordure
    cars = {}

    for y, row in enumerate(parking):
        for x, col in enumerate(row):

            if col in cars:
                cars[col][2] += 1 # Incrémentation de la longueur de la voiture de 1
            elif col != '.':
                cars[col] = new_car_infos(parking, x, y)

    return {
        'width': len(parking[0]),
        'height': len(parking),
        'cars': [cars[key] for key in sorted(cars.keys())],
        'max_moves': int(info_file_lst[-1])
    }

def new_car_infos(parking, x, y):
    """Check si la voiture aux coordonnées x, y est à l'orientale ou la verticale 
    puis retourne les infos de bases pour une voiture de longueur 1"""
    if x != len(parking[y]) - 1:
        if parking[y][x] == parking[y][x + 1]:
          orientation = 'h'

    if y != len(parking) - 1:
        if parking[y][x] == parking[y + 1][x]:
            orientation = 'v'

    return [(x, y), orientation, 1]

def get_game_str(game: dict, current_move_number: int) -> str: # Fonction 2
    """Retourne le texte correspondant à l'affichage du plateau de jeu (contenu dans le dictionnaire game en entrée)
    et ajoute le nombre de mouvements déjà effectué (contenu dans l'entier current_move_number)."""

    game_matrix = [["." for _ in range(game['width'])] for _ in range(game['height'])]
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
    frame = frame + '\n Moves remains: ' + str(current_move_number) + '\n Max moves: ' + str(game['max_moves'])

    return frame

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
    """Vérifie si la voiture peut être déplacé dans la direction souhaiter.
    Si oui, modifier le dictionnaire game et retourne True,
    si non, ne rien modifier et retourne False."""

    if direction == 'UP':
        if (
            game['cars'][car_index][1] == 'v'
            and game['cars'][car_index][0][1] != 0
            and (game['cars'][car_index][0][1] - 1, game['cars'][car_index][0][0]) not in used_coords(game)
        ):
            game['cars'][car_index][0] = game['cars'][car_index][0][0], game['cars'][car_index][0][1] - 1
            return True
        
    if direction == 'DOWN':
        if (
            game['cars'][car_index][1] == 'v'
            and game['cars'][car_index][0][1]+ game['cars'][car_index][2] != game['height'] 
            and (game['cars'][car_index][0][1] + game['cars'][car_index][2], game['cars'][car_index][0][0]) not in used_coords(game)
        ):
            game['cars'][car_index][0] = game['cars'][car_index][0][0], game['cars'][car_index][0][1] + 1
            return True
        
    if direction == 'LEFT':
        if (
            game['cars'][car_index][1] == 'h'
            and game['cars'][car_index][0][0]!= 0 
            and (game['cars'][car_index][0][1], game['cars'][car_index][0][0] - 1) not in used_coords(game)
        ):
            game['cars'][car_index][0] = game['cars'][car_index][0][0] - 1, game['cars'][car_index][0][1]
            return True
        
    if direction == 'RIGHT':
        if (
            game['cars'][car_index][1] == 'h'
            and game['cars'][car_index][0][0] + game['cars'][car_index][2] != game['width'] 
            and (game['cars'][car_index][0][1], game['cars'][car_index][0][0] + game['cars'][car_index][2]) not in used_coords(game)
        ):
            game['cars'][car_index][0] = game['cars'][car_index][0][0] + 1, game['cars'][car_index][0][1]
            return True

    return False

def used_coords(game):
    """Donne la liste des cases occupées par des voitures"""
    used_coords = []

    for car in game['cars']:
        for coord in get_car_coords(car):
            used_coords.append(coord)

    return(used_coords)

def is_win(game: dict) -> bool: # Fonction 4
    return bool(game['cars'][0][0][0] + game['cars'][0][2] == game['width'])

def play_game(game: dict) -> int: # Fonction 5
    """Cette fonction prendra en compte toutes les instructions de la partie, sauf l'initiation.
    Si le joueur a gagné, retourne 0,
    si le joueur a perdu, retourne 1,
    si le joueur a perdu, retourne 2."""
    moves_remains = game['max_moves']
    car_to_move, move = None, None

    while not is_win(game) and moves_remains:
        print(get_game_str(game, moves_remains))

        while not(car_to_move and move):
            user_input = getkey()

            if len(user_input) == 1:
                if (
                    ord('A') + ord(user_input) >= 0 
                    and ord(user_input) - ord('A') + 1 <= len(game['cars'])
                ) :
                    car_to_move = ord(user_input) - ord('A')

            elif(user_input in ('UP', 'DOWN', 'LEFT', 'RIGHT')):
                move = user_input
                
            elif user_input == 'ESCAPE':
                return 2

        move_car(game, car_to_move, move)
        move = None
        moves_remains -= 1

    if is_win(game):
        return 0
    
    if not moves_remains:
        return 1

if __name__ == '__main__':
    print(get_car_coords([(0, 2), 'h', 2]))

    res = play_game(parse_game(argv[1]))

    print("Fin du programme", res)
