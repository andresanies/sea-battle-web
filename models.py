# -*- coding: utf-8 -*-

import random

from google.appengine.ext import ndb
from protorpc import messages


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()


class Game(ndb.Model):
    """Game object"""
    player = ndb.KeyProperty(required=True, kind='User')
    player_ships = ndb.KeyProperty(kind='Ship', repeated=True)
    player_bombs = ndb.KeyProperty(kind='Bomb', repeated=True)
    opponent_ships = ndb.KeyProperty(kind='Ship', repeated=True)
    opponent_bombs = ndb.KeyProperty(kind='Bomb', repeated=True)
    game_over = ndb.BooleanProperty(required=True, default=False)

    @classmethod
    def new_game(cls, user, ships):
        """Creates and returns a new game"""
        ships = cls.create_ships(ships)
        game = Game(player=user, player_ships=ships,
                    opponent_ships=cls.generate_opponent_ships())
        game.put()
        return game

    @classmethod
    def create_ships(cls, ships):
        created_ships = []
        # print(ships)
        for ship in ships:
            ship_instance = Ship.create_ship(
                ship.type, ship.star_square, ship.orientation, save=False)
            created_ships.append(ship_instance)
        cls.check_overlapping_ships(created_ships)
        return cls.save_ships(created_ships)

    @classmethod
    def save_ships(cls, ships):
        saved_ships_keys = []
        for ship in ships:
            ship.put()
            saved_ships_keys.append(ship.key)

        return saved_ships_keys

    @classmethod
    def check_overlapping_ships(cls, ships):
        for test_ship in ships:
            cls.check_overlapping_ship(test_ship, ships)

    @classmethod
    def check_overlapping_ship(cls, test_ship, ships):
        for ship in ships:
            if ship != test_ship:
                for square in test_ship.squares:
                    if square in ship.squares:
                        raise ValueError('%s overlapping %s at %s' % (
                            test_ship.type_name, ship.type_name, square))

    @classmethod
    def generate_opponent_ships(cls):
        ships_number_by_type = {
            Ship.BATTLESHIP: 1,
            Ship.CRUISER: 2,
            Ship.DESTROYER: 3,
            Ship.SUBMARINE: 4
        }
        ships = []
        for ship_type in Ship.TYPE_CHOICES:
            for _ in range(ships_number_by_type[ship_type]):
                orientation = random.randint(1, len(Ship.ORIENTATION_CHOICES))
                grid_boundaries = cls.generate_restricted_grid_boundaries(
                    ship_type, orientation)

                ship = None
                while True:
                    try:
                        ship = cls.generate_ship(grid_boundaries, ship_type, orientation)
                        cls.check_overlapping_ship(ship, ships)
                        cls.check_nearby_ships(ship, ships)
                        break
                    except ValueError:
                        continue

                ships.append(ship)
        return cls.save_ships(ships)

    @classmethod
    def generate_restricted_grid_boundaries(cls, ship_type, orientation):
        row_limit = 10
        column_limit = 10

        if orientation == Ship.VERTICAL:
            row_limit -= (ship_type - 1)

        if orientation == Ship.HORIZONTAL:
            column_limit = 10 - (ship_type - 1)

        return [row_limit, column_limit]

    @classmethod
    def generate_ship(cls, grid_boundaries, ship_type, orientation):
        row_limit, column_limit = grid_boundaries[0], grid_boundaries[1]

        row = chr(64 + random.randint(1, row_limit))
        column = random.randint(1, column_limit)

        star_square = "%s%d" % (row, column)

        return Ship.create_ship(
            ship_type, star_square, orientation, save=False)

    @classmethod
    def check_nearby_ships(cls, test_ship, ships):
        for ship in ships:
            for test_square in test_ship.squares:
                nearby_rows = [ord(test_square[0]) - 1, ord(test_square[0]) + 1]
                nearby_columns = [int(test_square[1:]) - 1, int(test_square[1:]) + 1]
                for square in ship.squares:
                    is_in_the_same_row = square[0] == test_square[0]
                    is_in_the_same_column = square[1:] == test_square[1:]
                    if (ord(square[0]) in nearby_rows and is_in_the_same_column) or \
                            (int(square[1:]) in nearby_columns and is_in_the_same_row):
                        raise ValueError()

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.player.get().name
        form.player_ships = [ship.get().to_form() for ship in self.player_ships]
        form.player_bombs = self.player_bombs
        form.opponent_ships = [ship.get().to_form() for ship in self.opponent_ships]
        form.opponent_bombs = self.opponent_bombs
        form.game_over = self.game_over
        form.message = message
        return form

        # def end_game(self, won=False):
        #     """Ends the game - if won is True, the player won. - if won is False,
        #     the player lost."""
        #     self.game_over = True
        #     self.put()
        #     # Add the game to the score 'board'
        #     score = Score(user=self.user, date=date.today(), won=won,
        #                   guesses=self.attempts_allowed - self.attempts_remaining)
        #     score.put()


class Ship(ndb.Model):
    BATTLESHIP = 4
    CRUISER = 3
    DESTROYER = 2
    SUBMARINE = 1

    TYPE_CHOICES = [BATTLESHIP, CRUISER, DESTROYER, SUBMARINE]

    TYPE_NAMES = {
        BATTLESHIP: 'Battleship',
        CRUISER: 'Cruiser',
        DESTROYER: 'Destroyer',
        SUBMARINE: 'Submarine',
    }

    VERTICAL = 1
    HORIZONTAL = 2
    ORIENTATION_CHOICES = [VERTICAL, HORIZONTAL]

    type = ndb.IntegerProperty(required=True, choices=TYPE_CHOICES)
    star_square = ndb.StringProperty(required=True)
    orientation = ndb.IntegerProperty(required=True, choices=ORIENTATION_CHOICES)
    sunken = ndb.BooleanProperty(default=False)

    @classmethod
    def create_ship(cls, ship_type, star_square, orientation, save=True):
        cls.validate_ship(ship_type, star_square, orientation)
        ship = Ship(type=ship_type, star_square=star_square,
                    orientation=orientation)
        if save:
            ship.put()

        return ship

    @classmethod
    def validate_ship(cls, ship_type, star_square, orientation):
        try:
            cls.validate_square(star_square)
            cls.validate_type(ship_type)
            cls.check_if_fit_in_grid(ship_type, star_square, orientation)
        except ValueError as e:
            raise ValueError('%s for %s at %s' %
                             (str(e), cls.TYPE_NAMES[ship_type], star_square))

    @classmethod
    def validate_square(cls, square):
        if len(square) > 3:
            raise ValueError('Invalid square')

        cls._get_row_fow_letter(square[0])
        square_column = int(square[1:])
        if square_column not in range(1, 11):
            raise ValueError('The number of the column must be '
                             'an integer between 1 to 10')

    @classmethod
    def _get_row_fow_letter(cls, letter):
        row_map = {
            'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5,
            'F': 6, 'G': 7, 'H': 8, 'I': 9, 'J': 10,
        }
        try:
            return row_map[letter]
        except KeyError:
            raise ValueError('The letter of the row must '
                             'be between A to J uppercase')

    @classmethod
    def validate_type(cls, ship_type):
        if ship_type not in cls.TYPE_CHOICES:
            raise ValueError('Invalid ship type, options are: '
                             '4 for BATTLESHIP, 3 for CRUISER '
                             '2 for DESTROYER and 1 for SUBMARINE')

    @classmethod
    def check_if_fit_in_grid(cls, ship_type, start_square, orientation):
        end_square = cls.get_end_square(ship_type, start_square, orientation)
        try:
            cls.validate_square(end_square)
        except ValueError:
            raise ValueError("Ship doesn't fit in sea grid")

    @classmethod
    def get_end_square(cls, ship_type, start_square, orientation):
        ship_length = ship_type - 1
        return cls.get_square_at_relative_position(
            start_square, orientation, stepped_squares=ship_length)

    @classmethod
    def get_square_at_relative_position(
            cls, start_square, orientation, stepped_squares):
        if orientation == cls.VERTICAL:
            star_square_row = cls._get_row_fow_letter(start_square[0])
            end_square_row = star_square_row + stepped_squares
            end_square_row = chr(64 + end_square_row)
        else:
            end_square_row = start_square[0]

        start_square_column = int(start_square[1:])
        if orientation == cls.HORIZONTAL:
            end_square_column = start_square_column + stepped_squares
        else:
            end_square_column = start_square_column

        return '%s%d' % (end_square_row, end_square_column)

    @property
    def squares(self):
        ship_length = self.type

        squares = [self.star_square]
        for step in range(1, ship_length):
            relative_square = self.get_square_at_relative_position(
                self.star_square, self.orientation, stepped_squares=step)
            squares.append(relative_square)
        return squares

    @property
    def type_name(self):
        return self.TYPE_NAMES[self.type]

    def to_form(self):
        form = ShipForm()
        form.type = self.type
        form.star_square = self.star_square
        form.orientation = self.orientation
        form.sunken = self.sunken
        return form


class Bomb(ndb.Model):
    MISS = 1
    HIT = 2
    SINK = 3

    RESULT_CHOICES = [MISS, HIT, SINK]

    target_square = ndb.StringProperty(repeated=True)
    result = ndb.IntegerProperty(repeated=True, choices=RESULT_CHOICES)


class BombForm(messages.Message):
    target_square = messages.StringField(1, required=True)
    result = messages.IntegerField(2, required=True)


class ShipForm(messages.Message):
    """GameForm for describing a ship"""
    type = messages.IntegerField(1, required=True)
    star_square = messages.StringField(2, required=True)
    orientation = messages.IntegerField(3, required=True)
    sunken = messages.BooleanField(4, required=True)


class NewShipForm(messages.Message):
    """GameForm for describing a ship"""
    type = messages.IntegerField(1, required=True)
    star_square = messages.StringField(2, required=True)
    orientation = messages.IntegerField(3, required=True)


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    player_ships = messages.MessageField(ShipForm, 2, repeated=True)
    player_bombs = messages.MessageField(BombForm, 3, repeated=True)
    opponent_ships = messages.MessageField(ShipForm, 4, repeated=True)
    opponent_bombs = messages.MessageField(BombForm, 5, repeated=True)
    game_over = messages.BooleanField(6, required=True)
    message = messages.StringField(7, required=True)
    user_name = messages.StringField(8, required=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    ships = messages.MessageField(NewShipForm, 2, repeated=True)
