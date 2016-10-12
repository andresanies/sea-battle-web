# -*- coding: utf-8 -*-
# Developer: Andres Anies <andres_anies@hotmail.com>
import random

from models import Bomb
from models import Ship


class PlayerBomber(object):
    def __init__(self, game, bomb):
        self.game = game
        self.bomb = bomb
        self.target_ships = [ship_key.get() for ship_key in self.game.opponent_ships]
        self.sunken_ships = self.game.sunken_opponent_ships

    @property
    def bombs(self):
        return [bomb.get() for bomb in self.game.player_bombs]

    @property
    def bombs_squares(self):
        return [bomb.target_square for bomb in self.bombs]

    def bomb_ships(self):
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
        for square in ship.squares:
            if square not in self.bombs_squares:
                return

        self.sunken_ships.append(ship.key)
        self.game.put()
        return True

    def _check_if_game_is_over(self):
        if len(self.game.sunken_opponent_ships) == 10 or (
                    len(self.game.sunken_player_ships) == 10):
            self.game.game_over = True
            self.game.put()


class OpponentBomber(PlayerBomber):
    def __init__(self, game):
        super(OpponentBomber, self).__init__(game, None)
        self.game = game
        self.target_ships = [ship_key.get() for ship_key in self.game.player_ships]
        self.sunken_ships = self.game.sunken_player_ships

    @property
    def bombs(self):
        return [bomb.get() for bomb in self.game.opponent_bombs]

    def bomb_ships(self):
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
        latest_hit_bombs = []

        sunken_ships_squares = []
        for ship_key in self.game.sunken_player_ships:
            for square in ship_key.get().squares:
                sunken_ships_squares.append(square)

        for bomb in self.bombs:
            if bomb.result == Bomb.HIT and (
                        bomb.target_square not in sunken_ships_squares):
                latest_hit_bombs.append(bomb.target_square)

        return latest_hit_bombs

    def _bomb_nearby_squares(self, latest_hit_bombs):
        latest_bomb = latest_hit_bombs[0]
        nearby_squares = self._get_nearby_squares(latest_bomb)
        self._try_bombs(nearby_squares)

    def _get_nearby_squares(self, square):
        nearby_rows = [chr(ord(square[0]) - 1), chr(ord(square[0]) + 1)]
        nearby_columns = [int(square[1:]) - 1, int(square[1:]) + 1]

        top_square = "%s%s" % (nearby_rows[1], square[1:])
        down_square = "%s%s" % (nearby_rows[0], square[1:])
        left_square = "%s%s" % (square[0], nearby_columns[0])
        right_square = "%s%s" % (square[0], nearby_columns[1])
        return [top_square, down_square, left_square, right_square]

    def _try_bombs(self, nearby_squares):
        for possible_bomb in nearby_squares:
            try:
                Ship.validate_square(possible_bomb)
                if possible_bomb not in self.bombs_squares:
                    self._save_bomb(possible_bomb)
                    break
            except ValueError:
                continue

    def _bomb_with_same_last_orientation(self, latest_hit_bombs):
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
        latest_bomb = latest_hit_bombs[-1]
        second_latest_bomb = latest_hit_bombs[-2]

        top_square, down_square, left_square, right_square = self._get_nearby_squares(latest_bomb)

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
        while True:
            row = chr(64 + random.randint(1, 10))
            column = random.randint(1, 10)
            bomb = "%s%d" % (row, column)
            if bomb not in self.bombs_squares:
                self._save_bomb(bomb)
                break

    def _save_bomb(self, bomb):
        self.bomb = bomb
        bomb_key, bombed_ship, result = self.get_bomb_result()
        self.game.opponent_bombs.append(bomb_key)
        self.game.put()

        if bombed_ship:
            if self._is_sunken_ship(bombed_ship):
                self._check_if_game_is_over()
