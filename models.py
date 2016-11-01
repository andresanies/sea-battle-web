# -*- coding: utf-8 -*-
"""models.py - This file contains the class definitions for the Datastore
entities used by the Game."""

from datetime import date

from google.appengine.ext import ndb
from protorpc import messages

from ships import ShipsGenerator
from ships import ShipsManager

__author__ = 'Andres Anies'
__email__ = 'andres_anies@hotmail.com'


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()


class Ship(ndb.Model):
    """Ship which forms part of the player or opponent fleet"""
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
    orientation = ndb.IntegerProperty(
        required=True, choices=ORIENTATION_CHOICES)
    sunken = ndb.BooleanProperty(default=False)

    @classmethod
    def create_ship(cls, ship_type, star_square, orientation, save=True):
        """Takes a ship components and returns a saved(optional)
         instance of the db ship model"""
        cls.validate_ship(ship_type, star_square, orientation)
        ship = Ship(type=ship_type, star_square=star_square,
                    orientation=orientation)
        if save:
            ship.put()

        return ship

    @classmethod
    def validate_ship(cls, ship_type, star_square, orientation):
        """Validates that the start square fits in the grid and has a correct
        format, the type value is of a known option and the rest of the
        squares of the ship fits in the game grid"""
        try:
            cls.validate_square(star_square)
            cls.validate_type(ship_type)
            cls.check_if_fit_in_grid(ship_type, star_square, orientation)
        except ValueError as e:
            raise ValueError('%s for %s at %s' %
                             (str(e), cls.TYPE_NAMES[ship_type], star_square))

    @classmethod
    def validate_square(cls, square):
        """Validates that the start square fits in the grid"""
        if len(square) > 3:
            raise ValueError('Invalid square')

        cls._get_row_fow_letter(square[0])
        square_column = int(square[1:])
        if square_column not in range(1, 11):
            raise ValueError('The number of the column must be '
                             'an integer between 1 to 10')

    @classmethod
    def _get_row_fow_letter(cls, letter):
        """Gets a number representation of the row(used for
        arithmetic operations)"""
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
        """Checks if the selected type option is one of the allowed types"""
        if ship_type not in cls.TYPE_CHOICES:
            raise ValueError('Invalid ship type, options are: '
                             '4 for BATTLESHIP, 3 for CRUISER '
                             '2 for DESTROYER and 1 for SUBMARINE')

    @classmethod
    def check_if_fit_in_grid(cls, ship_type, start_square, orientation):
        """Checks if all the squares in the ship fits in the game grid
        so it's a valid ship"""
        end_square = cls.get_end_square(ship_type, start_square, orientation)
        try:
            cls.validate_square(end_square)
        except ValueError:
            raise ValueError("Ship doesn't fit in sea grid")

    @classmethod
    def get_end_square(cls, ship_type, start_square, orientation):
        """Calculates and returns the last square of a ship"""
        ship_length = ship_type - 1
        return cls.get_square_at_relative_position(
            start_square, orientation, stepped_squares=ship_length)

    @classmethod
    def get_square_at_relative_position(
            cls, start_square, orientation, stepped_squares):
        """Calculates and returns the square of given position of a ship
        like the second or third, etc"""
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
        """Calculates and returns all the squares that belong to the ship"""
        ship_length = self.type

        squares = [self.star_square]
        for step in range(1, ship_length):
            relative_square = self.get_square_at_relative_position(
                self.star_square, self.orientation, stepped_squares=step)
            squares.append(relative_square)
        return squares

    @property
    def type_name(self):
        """Returns a human readable ship type representation"""
        return self.TYPE_NAMES[self.type]

    def to_form(self):
        """Returns a ShipForm representation of the Ship"""
        form = ShipForm()
        form.type = self.type
        form.star_square = self.star_square
        form.orientation = self.orientation
        form.sunken = self.sunken
        return form


class Bomb(ndb.Model):
    MIS = 'Mis'
    HIT = 'Hit'

    RESULT_CHOICES = [MIS, HIT]

    target_square = ndb.StringProperty(required=True)
    result = ndb.StringProperty(choices=RESULT_CHOICES)

    def to_form(self):
        """Returns a BombForm representation of the Bomb"""
        form = BombForm()
        form.target_square = self.target_square
        form.result = self.result
        return form


class Game(ndb.Model):
    """Game object"""

    player = ndb.KeyProperty(required=True, kind='User')
    players_ships = ndb.KeyProperty(kind='Ship', repeated=True)
    player_bombs = ndb.KeyProperty(kind='Bomb', repeated=True)
    sunken_players_ships = ndb.KeyProperty(kind='Ship', repeated=True)
    opponents_ships = ndb.KeyProperty(kind='Ship', repeated=True)
    opponent_bombs = ndb.KeyProperty(kind='Bomb', repeated=True)
    sunken_opponents_ships = ndb.KeyProperty(kind='Ship', repeated=True)
    game_over = ndb.BooleanProperty(required=True, default=False)

    @classmethod
    def new_game(cls, user, raw_ships):
        """Creates and returns a new game"""
        ships = ShipsManager(Ship, raw_ships).create_ships()
        game = Game(player=user, players_ships=ships,
                    opponents_ships=ShipsGenerator(
                        Ship).generate_opponents_ships())
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.player.get().name
        form.players_ships = [ship.get().to_form()
                              for ship in self.players_ships]
        form.player_bombs = [bomb.get().to_form()
                             for bomb in self.player_bombs]
        form.sunken_players_ships = [ship.get().to_form()
                                     for ship in self.sunken_players_ships]
        form.opponent_bombs = [bomb.get().to_form()
                               for bomb in self.opponent_bombs]
        form.sunken_opponents_ships = [ship.get().to_form()
                                       for ship in self.sunken_opponents_ships]
        form.game_over = self.game_over
        form.message = message
        return form

    def to_history_form(self):
        """Returns a GameHistoryForm representation of the Game"""
        form = GameHistoryForm()
        form.players_ships = [ship.get().to_form()
                              for ship in self.players_ships]
        form.player_bombs = [bomb.get().to_form()
                             for bomb in self.player_bombs]
        form.opponent_bombs = [bomb.get().to_form()
                               for bomb in self.opponent_bombs]
        return form

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        score = Score(user=self.player, date=date.today(), won=won,
                      bombs=len(self.player_bombs))
        score.put()


class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    bombs = ndb.IntegerProperty(required=True)

    def to_form(self):
        """Returns a ScoreForm representation of the Score"""
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), bombs=self.bombs)


class BombForm(messages.Message):
    """BombForm for describing a bomb"""
    target_square = messages.StringField(1, required=True)
    result = messages.StringField(2, required=True)


class ShipForm(messages.Message):
    """ShipForm for describing a ship"""
    type = messages.IntegerField(1, required=True)
    star_square = messages.StringField(2, required=True)
    orientation = messages.IntegerField(3, required=True)
    sunken = messages.BooleanField(4, required=True)


class NewShipForm(messages.Message):
    """NewShipForm for representing a ship to be created"""
    type = messages.IntegerField(1, required=True)
    star_square = messages.StringField(2, required=True)
    orientation = messages.IntegerField(3, required=True)


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    players_ships = messages.MessageField(ShipForm, 2, repeated=True)
    player_bombs = messages.MessageField(BombForm, 3, repeated=True)
    sunken_players_ships = messages.MessageField(ShipForm, 4, repeated=True)
    opponent_bombs = messages.MessageField(BombForm, 5, repeated=True)
    sunken_opponents_ships = messages.MessageField(ShipForm, 6, repeated=True)
    game_over = messages.BooleanField(7, required=True)
    message = messages.StringField(8, required=True)
    user_name = messages.StringField(9, required=True)


class GameForms(messages.Message):
    """Return multiple GameForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class GameHistoryForm(messages.Message):
    """Representation of the history of a Game"""
    players_ships = messages.MessageField(ShipForm, 2, repeated=True)
    player_bombs = messages.MessageField(BombForm, 3, repeated=True)
    opponent_bombs = messages.MessageField(BombForm, 5, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    ships = messages.MessageField(NewShipForm, 2, repeated=True)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    bomb = messages.StringField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    bombs = messages.IntegerField(4, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class UserRankingForm(messages.Message):
    """UserRankingForm for outbound User ranking information
    through a performance indicator which calculated as wins / loss + 1 """
    name = messages.StringField(1, required=True)
    performance = messages.FloatField(2, required=True)


class RankingForms(messages.Message):
    """Return multiple UserRankingForm"""
    items = messages.MessageField(UserRankingForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
