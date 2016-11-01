# -*- coding: utf-8 -*-
"""
bombers.py: Holds validators and generators of bombs.
"""

import random

from models import Bomb
from models import Ship

__author__ = 'Andres Anies'
__email__ = 'andres_anies@hotmail.com'


class PlayerBomber(object):
    """Validates and calculates the result of a player bomb"""

    def __init__(self, game, bomb):
        self.game = game
        self.bomb = bomb
        self.target_ships = [ship_key.get()
                             for ship_key in self.game.opponents_ships]
        self.sunken_ships = self.game.sunken_opponents_ships

    @property
    def bombs(self):
        return [bomb.get() for bomb in self.game.player_bombs]

    @property
    def bombs_squares(self):
        return [bomb.target_square for bomb in self.bombs]

    def bomb_ships(self):
        """Executes the player's bombing and returns its result checking a
        possible sinking ship or a game over"""
        if self.bomb in self.bombs_squares:
            raise ValueError('That bomb has already been dropped!')

        bomb_key, bombed_ship, result = self.get_bomb_result()
        self.game.player_bombs.append(bomb_key)
        self.game.put()

        if bombed_ship:
            if self._is_sunken_ship(bombed_ship):
                self._check_if_game_is_over()

        return result

    def get_bomb_result(self):
        """Searches for a opponent ship that fills the same square as the
        dropped bomb by the player, and if so the result will be a 'Hit'
        otherwise a 'Mis'. Creates and saves in the database the Bomb's model
        instance. Returns its key, result and the beaten ship if there is one"""
        result = Bomb.MIS
        bombed_ship = None
        for target_ship in self.target_ships:
            if self.bomb in target_ship.squares:
                bombed_ship, result = target_ship, Bomb.HIT
                break

        bomb = Bomb(target_square=self.bomb, result=result)
        bomb.put()

        return bomb.key, bombed_ship, result

    def _is_sunken_ship(self, ship):
        """Checks if a given ship has all its squares bombarded and it should
        be marked as a sunken ship"""
        for square in ship.squares:
            if square not in self.bombs_squares:
                return

        self.sunken_ships.append(ship.key)
        self.game.put()
        return True

    def _check_if_game_is_over(self):
        """Checks if the player or the opponent have sunken all the enemy ships
        so the game has come to the end"""
        if len(self.game.sunken_opponents_ships) == 10:
            self.game.end_game(won=True)

        if len(self.game.sunken_players_ships) == 10:
            self.game.end_game()


class OpponentBomber(PlayerBomber):
    """Generates, validates and calculates the result of an opponent bomb"""

    def __init__(self, game):
        super(OpponentBomber, self).__init__(game, None)
        self.game = game
        self.target_ships = [ship_key.get()
                             for ship_key in self.game.players_ships]
        self.sunken_ships = self.game.sunken_players_ships

    @property
    def bombs(self):
        return [bomb.get() for bomb in self.game.opponent_bombs]

    def bomb_ships(self):
        """Generates a random bomb to be dropped in the player's fleet if
        there is not a ship partially sunken else find the rest of the ship
        and bombard it until has been sunken"""
        latest_hit_bombs = self._get_latest_hit_bombs()
        if latest_hit_bombs:

            if len(latest_hit_bombs) == 1:
                self._bomb_nearby_squares(latest_hit_bombs)
            else:

                if self.bombs[-1].result == Bomb.HIT:
                    self._bomb_with_same_last_orientation_and_direction(
                        latest_hit_bombs)
                else:
                    self._bomb_with_same_last_orientation(latest_hit_bombs)

        else:
            self._bomb_random_square()

    def _get_latest_hit_bombs(self):
        """Returns the latest bombs that had hit a partially sunken ship"""
        latest_hit_bombs = []

        sunken_ships_squares = []
        for ship_key in self.game.sunken_players_ships:
            for square in ship_key.get().squares:
                sunken_ships_squares.append(square)

        for bomb in self.bombs:
            if bomb.result == Bomb.HIT and (
                        bomb.target_square not in sunken_ships_squares):
                latest_hit_bombs.append(bomb.target_square)

        return latest_hit_bombs

    def _bomb_nearby_squares(self, latest_hit_bombs):
        """Finds the rest of the squares of a partially sunken ship
        and bombard it guessing the position of the next square of that ship"""
        latest_bomb = latest_hit_bombs[0]
        nearby_squares = self._get_nearby_squares(latest_bomb)
        self._try_bombs(nearby_squares)

    def _get_nearby_squares(self, square):
        """Finds all nearby(top, down, left and right) squares
        of a given square"""
        nearby_rows = [chr(ord(square[0]) - 1), chr(ord(square[0]) + 1)]
        nearby_columns = [int(square[1:]) - 1, int(square[1:]) + 1]

        top_square = "%s%s" % (nearby_rows[1], square[1:])
        down_square = "%s%s" % (nearby_rows[0], square[1:])
        left_square = "%s%s" % (square[0], nearby_columns[0])
        right_square = "%s%s" % (square[0], nearby_columns[1])
        return [top_square, down_square, left_square, right_square]

    def _try_bombs(self, nearby_squares):
        """Tries to guess the next square of the partially sunken ship bombarding
        if possible a nearby square of the latest bomb that was a hit"""
        for possible_bomb in nearby_squares:
            try:
                Ship.validate_square(possible_bomb)
                if possible_bomb not in self.bombs_squares:
                    self._save_bomb(possible_bomb)
                    break
            except ValueError:
                continue

    def _bomb_with_same_last_orientation(self, latest_hit_bombs):
        """Tries to guess the next square of the partially sunken ship
         knowing that the possible Hit will be in the same orientation
         of the last hit"""
        latest_bomb = latest_hit_bombs[0]
        second_latest_bomb = latest_hit_bombs[1]

        nearby_squares = self._get_nearby_squares(latest_bomb)
        nearby_squares_vertically = nearby_squares[:2]
        nearby_squares_horizontally = nearby_squares[2:]

        if latest_bomb[0] == second_latest_bomb[0]:
            # We guess player ship is in horizontal orientation
            self._try_bombs(nearby_squares_horizontally)
        else:
            # We guess player ship is in vertical orientation
            self._try_bombs(nearby_squares_vertically)

    def _bomb_with_same_last_orientation_and_direction(self, latest_hit_bombs):
        """Guesses the next square of the partially sunken ship
         knowing that the possible Hit will be in the same orientation and
         the same direction of the last hit"""
        latest_bomb = latest_hit_bombs[-1]
        second_latest_bomb = latest_hit_bombs[-2]

        top_square, down_square, left_square, right_square = \
            self._get_nearby_squares(latest_bomb)

        if latest_bomb[0] == second_latest_bomb[0]:
            # We guess player ship is in horizontal orientation
            if second_latest_bomb == left_square:
                self._try_bombs([right_square])
            else:
                self._try_bombs([left_square])
        else:
            # We guess player ship is in vertical orientation
            if second_latest_bomb == down_square:
                self._try_bombs([top_square])
            else:
                self._try_bombs([down_square])

    def _bomb_random_square(self):
        """Drops a bomb in any available square"""
        while True:
            row = chr(64 + random.randint(1, 10))
            column = random.randint(1, 10)
            bomb = "%s%d" % (row, column)
            if bomb not in self.bombs_squares:
                self._save_bomb(bomb)
                break

    def _save_bomb(self, bomb):
        """Gets the bomb saved in the database and adds its key to the
        opponent_bombs list of the current game. Check if there is a sunken
        ship or the game has come to the end"""
        self.bomb = bomb
        bomb_key, bombed_ship, result = self.get_bomb_result()
        self.game.opponent_bombs.append(bomb_key)
        self.game.put()

        if bombed_ship:
            if self._is_sunken_ship(bombed_ship):
                self._check_if_game_is_over()
