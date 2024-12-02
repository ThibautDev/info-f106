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

    # Ovrire le fichier de jeu et mettre son contenu dans info_file_lst 
    with open(game_file_path, encoding="utf-8") as info_file:
        info_file_lst = [line for line in info_file]
    
    # Créé la matrice parking depuis le fichier de jeu
    parking = [list(row.strip()[1:-1]) for row in info_file_lst[1:-2]] 

    cars = {}

    # Ajouter les infos voitures par voitures
    for y, row in enumerate(parking):
        for x, col in enumerate(row):

            if col in cars:
                cars[col][2] += 1 
            elif col != '.':
                cars[col] = new_car_infos(parking, x, y)
    
    return {
        'width': len(parking[0]),
        'height': len(parking),
        # La liste par ordre alphabetique des voitures
        'cars': [cars[key] for key in sorted(cars.keys())],
        'max_moves': int(info_file_lst[-1])
    }

def new_car_infos(parking, x, y):
    '''
    Depuis une matrice du parking et des positions x et y,
    détermine l'orientation de la voiture à ces coordonnées
    et ajoute les infos pour qu'elle puisse être jouter dans 
    le tableau des voitures.
    '''
    orientation = None
    
    # Si la voiture ne touche pas le bord de gauche
    # et qu'il a bien une case occupé par la même voiture en bas de sa case,
    # alors son orientation est horizontalle.
    if x + 1 < len(parking[y]) and parking[y][x] == parking[y][x + 1]:
        orientation = 'h'

    # Si la voiture ne touche pas le bord du bas
    # et qu'il a bien une case occupé par la même voiture à droite de sa case,,
    # alors son orientation est verticalle.
    if y + 1 < len(parking) and parking[y][x] == parking[y + 1][x]:
        orientation = 'v'

    return [(x, y), orientation, 1]

def get_game_str(game: dict, current_move_number: int) -> str: # Fonction 2
    '''
    Depuis un dictionnaire initié par la fonction parse_game,
    retourne un text qui peut être affiché au joueur 
    à la fin de chaque tour.
    '''

    # Initie une matrice de bonne taille vide
    game_matrix = [
        [ "." for _ in range(game['width']) ] for _ in range(game['height'])
    ]

    color_index = 7

    # Ajoute les voiture une par une, case par case, dans la matrice
    for car_position, car in enumerate(game['cars']):
        for coord in get_car_coords(car):
            game_matrix[coord[0]][coord[1]] = (
                    '\u001b[4' + str(color_index) + 'm' 
                    + str(chr(ord('A') + car_position)) 
                    + '\u001b[0m'
                )

        color_index += 1
        
        # Faire boucler les couleur de voiture
        if color_index >= 7:
            color_index = 1
    
    # Transformer la matrice en texte lisible par l'utilisateur
    frame = '\n'.join([''.join(line)for line in game_matrix])

    return (
        frame + 
        '\nMoves remains: ' + str(current_move_number) + 
        '\nMax moves: ' + str(game['max_moves'])
    )

def get_car_coords(car):
    '''
    Depuis les informations d'une voiture dans le format d'un 
    dictionnaire initié par parse_game, me donne toutes les cases que 
    cette voiture occupe.
    '''

    car_coords = []

    # En fonction de l'horientation de la voiture,
    # Ajouter les coordonnées case par case
    if car[1] == 'h':
        for x in range(car[2]):
            car_coords.append((car[0][1], car[0][0] + x))
    elif car[1] == 'v':
        for y in range(car[2]):
            car_coords.append((car[0][1] + y, car[0][0]))

    return car_coords

def move_car(game: dict, car_index: int, direction: str) -> bool: # Fonction 3
    '''
    Déplace la voiture sélectionné par le mouvement donné.
    Saauvegarde le déplacement dans le dictionnaire.
    '''

    # Défini un dictionnaire de toutes les fonctions de mouvement
    direction_function_dict = {
        'UP': move_UP,
        'DOWN': move_DOWN,
        'LEFT': move_LEFT,
        'RIGHT': move_RIGHT,
    }
    
    # Exécuter et retourné le résultat de la foction du mouvement demandé
    return direction_function_dict[direction](game, car_index)

def move_UP(game: dict, car_index: int):
    '''
    Déplace la voiture sélectionné vers le haut.
    Retourne l'état du déplacement.
    '''
    # Vérifie que le mouvement UP est possible
    if (
        game['cars'][car_index][1] == 'v'
        and game['cars'][car_index][0][1] != 0
        and (
            game['cars'][car_index][0][1] - 1, 
            game['cars'][car_index][0][0]
        ) not in used_coords(game)
    ):
        # Modifie la valeut de la voitures dans le dictionnaire
        # en décrémentant y de 1
        game['cars'][car_index][0] = (
            game['cars'][car_index][0][0], 
            game['cars'][car_index][0][1] - 1
        )
        return True
    else:
        return False

def move_DOWN(game: dict, car_index: int):
    '''
    Déplace la voiture sélectionné vers le bas.
    Retourne l'état du déplacement.
    '''

    # Vérifie que le mouvement DOWN est possible
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
        # Modifie la valeut de la voitures dans le dictionnaire
        # en incrémentant y de 1
        game['cars'][car_index][0] = (
                game['cars'][car_index][0][0], 
                game['cars'][car_index][0][1] + 1
        )
        return True
    else:
        return False

def move_LEFT(game: dict, car_index: int):
    '''
    Déplace la voiture sélectionné vers la gauche.
    Retourne l'état du déplacement.
    '''

    # Vérifie que le mouvement LEFT est possible
    if (
        game['cars'][car_index][1] == 'h'
        and game['cars'][car_index][0][0]!= 0 
        and (
            game['cars'][car_index][0][1], 
            game['cars'][car_index][0][0] - 1
        ) not in used_coords(game)
    ):
        # Modifie la valeut de la voitures dans le dictionnaire
        # en décrémentant x de 1
        game['cars'][car_index][0] = (
            game['cars'][car_index][0][0] - 1, 
            game['cars'][car_index][0][1]
        )
        return True
    else:
        return False

def move_RIGHT(game: dict, car_index: int):
    '''
    Déplace la voiture sélectionné vers la droite.
    Retourne l'état du déplacement.
    '''

    # Vérifie que le mouvement RIGHT est possible
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
        # Modifie la valeut de la voitures dans le dictionnaire
        # en incrémentant x de 1
        game['cars'][car_index][0] = (
            game['cars'][car_index][0][0] + 1, 
            game['cars'][car_index][0][1]
        )
        return True
    else:
        return False

def used_coords(game):
    '''Donne la liste de toutes les coordonnées utilisé'''
    used_coords = []

    # Ajoute les coordonnées voiture par voiture, case par case, à la liste
    for car in game['cars']:
        for coord in get_car_coords(car):
            used_coords.append(coord)

    return(used_coords)

def is_win(game: dict) -> bool: # Fonction 4
    '''Retourne l'état de la partie'''

    # Verifie si la voiture A est sur la dernière case de sa ligne
    return bool(
        game['cars'][0][0][0] + game['cars'][0][2] == game['width']
    )

def play_game(game: dict) -> int: # Fonction 5
    '''
    Tant que la partie n'est pas fini, demande à l'utilisateur des 
    movements de voiture et les sauvegarder dans le dictionnaire game.
    Retourne 0 si partie gagné
    Retourne 1 si partie perdue par manque de mouvement
    Retourne 2 si partie abandonné par le joueur
    '''
    moves_remains = game['max_moves']
    car_to_move, move = 0, None

    while not is_win(game) and moves_remains:
        print(get_game_str(game, moves_remains))

        # Tant que le joueur n'a pas entré d'input de mouvement valide
        while not move:
            user_input = getkey()

            # Vérifie si le joueur veut entrer l'ID d'une des voiture
            if len(user_input) == 1:
                if (
                    ord('A') + ord(user_input) >= 0 
                    and (
                        ord(user_input) - ord('A') + 1
                    ) <= len(game['cars'])
                ) :
                    car_to_move = ord(user_input) - ord('A')
            
            # Verifie si le joueur veut entrer une instruction de mouvement
            elif(user_input in ('UP', 'DOWN', 'LEFT', 'RIGHT')):
                move = user_input
            
            # Vérifie si le joueur veut abandonné la partie
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
    end_game_sentence = {
        0: 'You win',
        1: 'You lose',
        2: 'Game discontinued',
    }

    print(end_game_sentence[play_game(parse_game(argv[1]))])
