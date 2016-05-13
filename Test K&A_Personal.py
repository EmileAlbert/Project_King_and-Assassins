#!/usr/bin/env python3
# kingandassassins.py
# Author: Sébastien Combéfis
# Version: April 29, 2016

from random import randint
import argparse
import json
import random
import socket
import sys

from lib import game

global TURN
TURN = -1

BUFFER_SIZE = 2048

CARDS = (
    # (AP King, AP Knight, Fetter, AP Population/Assassins)
    (1, 6, True, 5),
    (1, 5, False, 4),
    (1, 6, True, 5),
    (1, 6, True, 5),
    (1, 5, True, 4),
    (1, 5, False, 4),
    (2, 7, False, 5),
    (2, 7, False, 4),
    (1, 6, True, 5),
    (1, 6, True, 5),
    (2, 7, False, 5),
    (2, 5, False, 4),
    (1, 5, True, 5),
    (1, 5, False, 4),
    (1, 5, False, 4)
)

POPULATION = {
    'monk', 'plumwoman', 'appleman', 'hooker', 'fishwoman', 'butcher',
    'blacksmith', 'shepherd', 'squire', 'carpenter', 'witchhunter', 'farmer'
}

BOARD = (
    ('R', 'R', 'R', 'R', 'R', 'G', 'G', 'R', 'R', 'R'),
    ('R', 'R', 'R', 'R', 'R', 'G', 'G', 'R', 'R', 'R'),
    ('R', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'R'),
    ('R', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G'),
    ('R', 'G', 'G', 'G', 'G', 'R', 'R', 'G', 'G', 'G'),
    ('G', 'G', 'G', 'G', 'G', 'R', 'R', 'G', 'G', 'G'),
    ('R', 'R', 'G', 'G', 'G', 'R', 'R', 'G', 'G', 'G'),
    ('R', 'R', 'G', 'G', 'G', 'R', 'R', 'G', 'G', 'G'),
    ('R', 'R', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G'),
    ('R', 'R', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G')
)

# Coordinates of pawns on the board
KNIGHTS = {(1, 3), (3, 0), (7, 8), (8, 7), (8, 8), (8, 9), (9, 8)}
VILLAGERS = {
    (1, 7), (2, 1), (3, 4), (3, 6), (5, 2), (5, 5),
    (5, 7), (5, 9), (7, 1), (7, 5), (8, 3), (9, 5)
}

# Separate board containing the position of the pawns
PEOPLE = [[None for column in range(10)] for row in range(10)] #Tableau de 10x10 cases qui contiendra les noms des pions une fois placés


# Place the king in the right-bottom corner
PEOPLE[9][9] = 'king'

# Place the knights on the board
for coord in KNIGHTS:
    PEOPLE[coord[0]][coord[1]] = 'knight'

# Place the villagers on the board
# random.sample(A, len(A)) returns a list where the elements are shuffled
# this randomizes the position of the villagers
for villager, coord in zip(random.sample(POPULATION, len(POPULATION)), VILLAGERS):
    PEOPLE[coord[0]][coord[1]] = villager

KA_INITIAL_STATE = {
    'board': BOARD,
    'people': PEOPLE,
    'castle': [(2, 2, 'N'), (4, 1, 'W')],
    'card': None,
    'king': 'healthy',
    'lastopponentmove': [],
    'arrested': [],
    'killed': {
        'knights': 0,
        'assassins': 0
    }
}


class KingAndAssassinsState(game.GameState):
    '''Class representing a state for the King & Assassins game.'''

    DIRECTIONS = {
        'E': (0, 1),
        'W': (0, -1),
        'S': (1, 0),
        'N': (-1, 0)
    }

    def __init__(self, initialstate=KA_INITIAL_STATE):
        super().__init__(initialstate)

    def _nextfree(self, x, y, dir):
        nx, ny = self._getcoord((x, y, dir))

    def update(self, moves, player):
        visible = self._state['visible']
        hidden = self._state['hidden']
        people = visible['people']
        for move in moves:
            print(move)
            # ('move', x, y, dir): moves person at position (x,y) of one cell in direction dir
            if move[0] == 'move':
                x, y, d = int(move[1]), int(move[2]), move[3]
                p = people[x][y]
                if p is None:
                    raise game.InvalidMoveException('{}: there is no one to move'.format(move))
                nx, ny = self._getcoord((x, y, d))
                new = people[nx][ny]
                # King, assassins, villagers can only move on a free cell
                if p != 'knight' and new is not None:
                    raise game.InvalidMoveException('{}: cannot move on a cell that is not free'.format(move))
                if p == 'king' and BOARD[nx][ny] == 'R':
                    raise game.InvalidMoveException('{}: the king cannot move on a roof'.format(move))
                if p in {'assassin'}.union(POPULATION) and player != 0:
                    raise game.InvalidMoveException('{}: villagers and assassins can only be moved by player 0'.format(move))
                if p in {'king', 'knight'} and player != 1:
                    raise game.InvalidMoveException('{}: the king and knights can only be moved by player 1'.format(move))
                # Move granted if cell is free
                if new is None:
                    people[x][y], people[nx][ny] = people[nx][ny], people[x][y]
                # If cell is not free, check if the knight can push villagers
                else:
                    pass
            # ('arrest', x, y, dir): arrests the villager in direction dir with knight at position (x, y)
            elif move[0] == 'arrest':
                if player != 1:
                    raise game.InvalidMoveException('arrest action only possible for player 1')
                x, y, d = int(move[1]), int(move[2]), move[3]
                arrester = people[x][y]
                if arrester != 'knight':
                    raise game.InvalidMoveException('{}: the attacker is not a knight'.format(move))
                tx, ty = self._getcoord((x, y, d))
                target = people[tx][ty]
                if target not in POPULATION:
                    raise game.InvalidMoveException('{}: only villagers can be arrested'.format(move))
                visible['arrested'].append(people[tx][ty])
                people[tx][ty] = None
            # ('kill', x, y, dir): kills the assassin/knight in direction dir with knight/assassin at position (x, y)
            elif move[0] == 'kill':
                x, y, d = int(move[1]), int(move[2]), move[3]
                killer = people[x][y]
                if killer == 'assassin' and player != 0:
                    raise game.InvalidMoveException('{}: kill action for assassin only possible for player 0'.format(move))
                if killer == 'knight' and player != 1:
                    raise game.InvalidMoveException('{}: kill action for knight only possible for player 1'.format(move))
                tx, ty = self._getcoord((x, y, d))
                target = people[tx][ty]
                if target is None:
                    raise game.InvalidMoveException('{}: there is no one to kill'.format(move))
                if killer == 'assassin' and target == 'knight':
                    visible['killed']['knights'] += 1
                    people[tx][tx] = None
                elif killer == 'knight' and target == 'assassin':
                    visible['killed']['assassins'] += 1
                    people[tx][tx] = None
                else:
                    raise game.InvalidMoveException('{}: forbidden kill'.format(move))
            # ('attack', x, y, dir): attacks the king in direction dir with assassin at position (x, y)
            elif move[0] == 'attack':
                if player != 0:
                    raise game.InvalidMoveException('attack action only possible for player 0')
                x, y, d = int(move[1]), int(move[2]), move[3]
                attacker = people[x][y]
                if attacker != 'assassin':
                    raise game.InvalidMoveException('{}: the attacker is not an assassin'.format(move))
                tx, ty = self._getcoord((x, y, d))
                target = people[tx][ty]
                if target != 'king':
                    raise game.InvalidMoveException('{}: only the king can be attacked'.format(move))
                visible['king'] = 'injured' if visible['king'] == 'healthy' else 'dead'
            # ('reveal', x, y): reveals villager at position (x,y) as an assassin
            elif move[0] == 'reveal':
                if player != 0:
                    raise game.InvalidMoveException('raise action only possible for player 0')
                x, y = int(move[1]), int(move[2])
                p = people[x][y]
                if p not in hidden['assassins']:
                    raise game.InvalidMoveException('{}: the specified villager is not an assassin'.format(move))
                people[x][y] = 'assassin'
        # If assassins' team just played, draw a new card
        if player == 0:
            visible['card'] = hidden['cards'].pop()

    def _getcoord(self, coord):
        return tuple(coord[i] + KingAndAssassinsState.DIRECTIONS[coord[2]][i] for i in range(2))

    def winner(self):
        visible = self._state['visible']
        hidden = self._state['hidden']
        # The king reached the castle
        for doors in visible['castle']:
            coord = self._getcoord(doors)
            if visible['people'][coord[0]][coord[1]] == 'king':
                return 1
        # The are no more cards
        if len(hidden['cards']) == 0:
            return 0
        # The king has been killed
        if visible['king'] == 'dead':
            return 0
        # All the assassins have been arrested or killed
        if visible['killed']['assassins'] + len(set(visible['arrested']) & hidden['assassins']) == 3:
            return 1
        return -1

    def isinitial(self):
        return self._state['hidden']['assassins'] is None

    def setassassins(self, assassins):
        self._state['hidden']['assassins'] = set(assassins)

    def prettyprint(self):
        visible = self._state['visible']
        hidden = self._state['hidden']
        result = ''
        if hidden is not None:
            result += '   - Assassins: {}\n'.format(hidden['assassins'])
            result += '   - Remaining cards: {}\n'.format(len(hidden['cards']))
        result += '   - Current card: {}\n'.format(visible['card'])
        result += '   - King: {}\n'.format(visible['king'])
        result += '   - People:\n'
        result += '   +{}\n'.format('----+' * 10)
        for i in range(10):
            result += '   | {} |\n'.format(' | '.join(['  ' if e is None else e[0:2] for e in visible['people'][i]]))
            result += '   +{}\n'.format(''.join(['----+' if e == 'G' else '^^^^+' for e in visible['board'][i]]))
        print(result)

    @classmethod
    def buffersize(cls):
        return BUFFER_SIZE


class KingAndAssassinsServer(game.GameServer):
    '''Class representing a server for the King & Assassins game'''

    def __init__(self, verbose=False):
        super().__init__('King & Assassins', 2, KingAndAssassinsState(), verbose=verbose)
        self._state._state['hidden'] = {
            'assassins': None,
            'cards': random.sample(CARDS, len(CARDS))
        }

    def _setassassins(self, move):
        state = self._state
        if 'assassins' not in move:
            raise game.InvalidMoveException('The dictionary must contain an "assassins" key')
        if not isinstance(move['assassins'], list):
            raise game.InvalidMoveException('The value of the "assassins" key must be a list')
        for assassin in move['assassins']:
            if not isinstance(assassin, str):
                raise game.InvalidMoveException('The "assassins" must be identified by their name')
            if not assassin in POPULATION:
                raise game.InvalidMoveException('Unknown villager: {}'.format(assassin))
        state.setassassins(move['assassins'])
        state.update([], 0)

    def applymove(self, move):
        try:
            state = self._state
            move = json.loads(move)
            if state.isinitial():
                self._setassassins(move)
            else:
                self._state.update(move['actions'], self.currentplayer)
        except game.InvalidMoveException as e:
            raise e
        except Exception as e:
            print(e)
            raise game.InvalidMoveException('A valid move must be a dictionary')


class KingAndAssassinsClient(game.GameClient):
    '''Class representing a client for the King & Assassins game'''

    def __init__(self, name, server, verbose=False):
        super().__init__(server, KingAndAssassinsState, verbose=verbose)
        self.__name = name

    def _handle(self, message):
        pass

    def _nextmove(self, state):
        # Two possible situations:
        # - If the player is the first to play, it has to select his/her assassins
        #   The move is a dictionary with a key 'assassins' whose value is a list of villagers' names
        # - Otherwise, it has to choose a sequence of actions
        #   The possible actions are:
        #   ('move', x, y, dir): moves person at position (x,y) of one cell in direction dir
        #   ('arrest', x, y, dir): arrests the villager in direction dir with knight at position (x, y)
        #   ('kill', x, y, dir): kills the assassin/knight in direction dir with knight/assassin at position (x, y)
        #   ('attack', x, y, dir): attacks the king in direction dir with assassin at position (x, y)
        #   ('reveal', x, y): reveals villager at position (x,y) as an assassin

        global TURN
        TURN += 1

        state = state._state['visible']

        def findPos(character):
            #Function to find character's position
            l = 0
            position = []
            for line in state['people']:
                l += 1
                c = 0
                for n in line :
                    c += 1
                    if character == 'knight':
                        if n == 'knight':
                            position.append((l-1, c-1))

                    else:
                        if n == character:
                            return l-1, c-1
            return position

        def findCharacter(pos):
            return state['people'][pos[0]][pos[1]]

        def KingInDanger(nextmove):

            if nextmove == 'N' :
                nextpos = (posKing[0] + 1, posKing[1])
            elif nextmove == 'W' :
                nextpos = (posKing[0], posKing[1] - 1)
            elif nextmove == 'E' :
                nextpos = (posKing[0], posKing[1] + 1)

            if KA_INITIAL_STATE['king'] == 'healthy' :
                space = kingSpace('healthy')
                for n in space :
                    if state['people'][n[0], n[1]] in POPULATION :
                        return True

                    else :
                        return False

            if KA_INITIAL_STATE['king'] == 'injured' :
                space = kingSpace('injured')
                for n in space :
                    if state['people'][n[0], n[1]] in POPULATION :
                        return True

                    else :
                        return False

        def kingSpace(kingState):
            # Return the coordinates of the case around the king --> Vital space
            posy = findPos('king')[0]
            posx = findPos('king')[1]

            space = [(posy - 1, posx), (posy - 1, posx - 1), (posy, posx - 1), (posy + 1, posx - 1), (posy + 1, posx),
                     (posy + 1, posx + 1), (posy, posx + 1), (posy - 1, posx + 1)]


            space2 = [(posy - 1, posx), (posy - 1, posx - 1), (posy, posx - 1), (posy + 1, posx - 1), (posy + 1, posx),
                      (posy + 1, posx + 1) , (posy, posx + 1), (posy - 1, posx + 1),(posy - 2, posx), (posy-2, posx-1),
                      (posy - 2 , posx - 2), (posy - 1, posx - 2), (posy, posx -2), (posy+1, posx-2), (posy+2, posx-2),
                      (posy + 2, posx - 1 ), (posy+ 2, posx), (posy+2, posx+1), (posy+2 , posx+2), (posy +1, posx + 2),
                      (posy, posx + 2), (posy - 1, posx + 2), (posy - 2, posx + 2), (posy - 2, posx + 1 )]

            if kingState == 'healthy':
                spacefinal = []
                for n in space:
                    if n[0] < 10 and n[1] < 10:
                        spacefinal.append(n)
                return spacefinal

            elif kingState == 'injured':
                spacefinal = []
                for n in space2:
                    if n[0] < 10 and n[1] < 10:
                        spacefinal.append(n)
                return spacefinal

        def knightarround():
            posKnights = findPos('knight')  # List of knights' position
            kingspace = kingSpace('injured') # List of knights around the king

            knightarround = []
            for n in posKnights:
                if n in kingspace:
                    knightarround.append(n)

            return knightarround

        def Goto(start, finish, direction):
            deltaline = start[0] - finish[0]
            deltacolu = start[1] - finish[1]


            pathv = []
            for n in range(start[0], finish[0]) :
                pathv.append(n)
            pathh = []
            for n in range(start[1], finish[1]) :
                pathh.append(n)

            if pathv[0] == 'G' and pathv[1] == 'R' :
                APv = 2
            else:
                APv = 1
            if pathh[0] == 'G' and pathh[1] == 'R' :
                APh = 2
            else:
                APh = 1


            # Horizontal move
            if deltaline < 0 and direction == 'V':
                return -deltaline, 'N', APv
            elif deltaline > 0 and direction == 'V':
                return deltaline, 'S', APv
            # Vertical move
            elif deltacolu < 0 and direction == 'H':
                return -deltacolu, 'E', APh
            elif deltacolu < 0 and direction == 'H':
                return deltacolu, 'W', APh

        # Initializing turn _ Choice of assassins
        if state['card'] is None:

            kingPath = ['W', 'W', 'W', 'W', 'W', 'N', 'N', 'N', 'N', 'N', 'W', 'W', 'W'] #Debute par 6 cases a gauche
            global path
            path = kingPath

            global assassins
            assassins = [findCharacter((7, 1)), findCharacter((5, 5)), findCharacter((2, 1))]

            return json.dumps({'assassins': assassins},
                              separators=(',', ':'))

        # Others turns
        else:
            APking = state['card'][0]
            APknight = state['card'][1]
            Fetter = state['card'][2]
            APvillage = state['card'][3]

            # Play on the villagers side
            if self._playernb == 0:
                actionslistvillage = []

                # Faire converger tout les villageois vers le roi et l'assasin le plus proche vers le roi
                posKing = findPos('king')
                i = 0
                while i < APvillage:
                    min = 100
                    global char
                    char = 0
                    for n in assassins :
                        res = abs(Goto(findPos(n), findPos('king'), 'H')[0]) + abs(Goto(findPos(n), findPos('king'), 'V')[0])
                        if res < min:
                            char = n

                    dir = ['H', 'V']
                    var = Goto(findPos(char),findPos('king'), dir[randint(0, 1)])
                    actionslistvillage.append(('move', findPos(char), var[1]))
                    i += var[2]

                    var2 = Goto(findPos(villager[randint(0, 11)]), findPos('king'), dir[randint(0, 1)])
                    actionslistvillage.append((('move'), findPos('king'), var2[1]))
                    i += var2[2]

                    if i < APvillage - 2:
                        goal = kingSpace('healthy')
                        for n in assassins:
                            if findPos(n) in goal:
                                actionslistvillage.append(('reveal', findPos(n)))
                                actionslistvillage.append(('attack', findPos(n), '??????'))
                                i += 2

                    # ( Tuer les chevalier dans le coin haut gauche )

                return json.dumps({'actions': actionslistvillage}, separators=(',', ':'))

            # Play on the king side
            else:
                posKing = findPos('king')
                actionslistking = []
                # Knight's moves

                # Suivre le roi
                #   --> Goto posking[0 ou 1] +- 1
                # Arreter des que possible
                # Gestion des assasins révelés ?

                posKnights = findPos('knight')  # List of knights' position
                knightarround = knightarround()

                # King's moves
                if not KingInDanger(path[0]):
                    actionslistking.append(('move', posKing, path[0]))
                    if path[0] == 'N':
                        global newpos
                        newpos = (posKing[0] + 1, posKing[1])
                    elif path[0] == 'W':
                        newpos = (posKing[0], posKing[1] - 1)
                    del(path[0])

                if APking == 2 and KingInDanger(path[0]) == False:
                    actionslistking.append(('move', newpos[0], newpos[1], path[0]))
                    del(path[0])

                return json.dumps({'actions': actionslistking}, separators=(',', ':'))

if __name__ == '__main__':
    # Create the top-level parser
    parser = argparse.ArgumentParser(description='King & Assassins game')
    subparsers = parser.add_subparsers(
        description='server client',
        help='King & Assassins game components',
        dest='component'
    )

    # Create the parser for the 'server' subcommand
    server_parser = subparsers.add_parser('server', help='launch a server')
    server_parser.add_argument('--host', help='hostname (default: localhost)', default='localhost')
    server_parser.add_argument('--port', help='port to listen on (default: 5000)', default=5000)
    server_parser.add_argument('-v', '--verbose', action='store_true')
    # Create the parser for the 'client' subcommand
    client_parser = subparsers.add_parser('client', help='launch a client')
    client_parser.add_argument('name', help='name of the player')
    client_parser.add_argument('--host', help='hostname of the server (default: localhost)',
                               default=socket.gethostbyname(socket.gethostname()))
    client_parser.add_argument('--port', help='port of the server (default: 5000)', default=5000)
    client_parser.add_argument('-v', '--verbose', action='store_true')
    # Parse the arguments of sys.args
    args = parser.parse_args()

    if args.component == 'server':
        KingAndAssassinsServer(verbose=args.verbose).run()
    else:
        KingAndAssassinsClient(args.name, (args.host, args.port), verbose=args.verbose)

#2BA\AdvancedPython2BA_Q2\"Projet King&Assassin's"
#Documents\ECAM\(ECAM) Informatique\2BA\AdvancedPython2BA_Q2\"Projet King&Assassin's"

#Lancer le serveur python "Test K&A.py" server --verbose
#Lancer le client  python "Test K&A.py" client --verbose name
