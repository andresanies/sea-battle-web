# -*- coding: utf-8 -*-
import os
import sys
import unittest

GAE_ROOT = os.path.expanduser('~/google_appengine')

sys.path.insert(1, GAE_ROOT)
sys.path.insert(1, '{}/lib/yaml/lib'.format(GAE_ROOT))
sys.path.insert(1, '{}/lib/endpoints-1.0'.format(GAE_ROOT))
sys.path.insert(1, '{}/lib/protorpc-1.0'.format(GAE_ROOT))
sys.path.insert(1, '{}/lib/fancy_urllib'.format(GAE_ROOT))

from google.appengine.ext import testbed
from api import SeaBattleApi
from api import USER_REQUEST
from api import NEW_GAME_REQUEST
from api import GET_GAME_REQUEST
from api import MAKE_MOVE_REQUEST
from models import User
from models import Ship
from models import ShipForm
from models import Game
from ships import ShipsGenerator
from ships import ShipsManager


def get_player_ships():
    return [
        {
            'type': Ship.BATTLESHIP,
            'star_square': 'D3',
            'orientation': Ship.VERTICAL,
        },
        {
            'type': Ship.CRUISER,
            'star_square': 'F6',
            'orientation': Ship.HORIZONTAL,
        },
        {
            'type': Ship.CRUISER,
            'star_square': 'H8',
            'orientation': Ship.HORIZONTAL,
        },
        {
            'type': Ship.DESTROYER,
            'star_square': 'B1',
            'orientation': Ship.VERTICAL,
        },
        {
            'type': Ship.DESTROYER,
            'star_square': 'D6',
            'orientation': Ship.HORIZONTAL,
        },
        {
            'type': Ship.DESTROYER,
            'star_square': 'J6',
            'orientation': Ship.HORIZONTAL,
        },
        {
            'type': Ship.SUBMARINE,
            'star_square': 'A3',
            'orientation': Ship.VERTICAL,
        },
        {
            'type': Ship.SUBMARINE,
            'star_square': 'A5',
            'orientation': Ship.VERTICAL,
        },
        {
            'type': Ship.SUBMARINE,
            'star_square': 'A8',
            'orientation': Ship.VERTICAL,
        },
        {
            'type': Ship.SUBMARINE,
            'star_square': 'B10',
            'orientation': Ship.VERTICAL,
        }
    ]


class ShipValidationTestCase(unittest.TestCase):
    def test_check_number_of_ships_by_type(self):
        ships = [ShipForm(type=ship['type'], star_square=ship['star_square'],
                          orientation=ship['orientation'])
                 for ship in get_player_ships()]
        ShipsManager(Ship, ships).check_number_of_ships_by_type()
        many_ships = ships[:]
        many_ships.append(ships[2])
        self.assertRaises(
            ValueError, ShipsManager(Ship, many_ships).check_number_of_ships_by_type)

        few_ships = ships[:]
        del few_ships[0]
        self.assertRaises(
            ValueError, ShipsManager(Ship, few_ships).check_number_of_ships_by_type)

        fewer_ships = ships[:]
        del fewer_ships[7]
        del fewer_ships[8]
        self.assertRaises(
            ValueError, ShipsManager(Ship, fewer_ships).check_number_of_ships_by_type)

    def test_validate_square(self):
        Ship.validate_square('A5')
        self.assertRaises(ValueError, Ship.validate_square, 'Q5')
        self.assertRaises(ValueError, Ship.validate_square, 'C20')

    def test_validate_type(self):
        Ship.validate_type(Ship.BATTLESHIP)
        self.assertRaises(ValueError, Ship.validate_type, 10)

    def test_get_end_square_vertical(self):
        end_square = Ship.get_end_square(Ship.CRUISER, 'C7', Ship.VERTICAL)
        self.assertEqual(end_square, 'E7')

    def test_get_end_square_horizontal(self):
        end_square = Ship.get_end_square(Ship.BATTLESHIP, 'B7', Ship.HORIZONTAL)
        self.assertEqual(end_square, 'B10')

    def test_get_end_square_out_of_grid(self):
        end_square = Ship.get_end_square(Ship.DESTROYER, 'I10', Ship.HORIZONTAL)
        self.assertEqual(end_square, 'I11')

    def test_check_if_fit_in_grid(self):
        Ship.check_if_fit_in_grid(Ship.CRUISER, 'C5', Ship.VERTICAL)
        self.assertRaises(ValueError, Ship.check_if_fit_in_grid,
                          Ship.CRUISER, 'B10', Ship.HORIZONTAL)
        self.assertRaises(ValueError, Ship.check_if_fit_in_grid,
                          Ship.CRUISER, 'J5', Ship.VERTICAL)

    def test_generate_squares_for_ship(self):
        ship = Ship(type=Ship.BATTLESHIP, star_square='B10',
                    orientation=Ship.VERTICAL)
        self.assertEqual(ship.squares, ['B10', 'C10', 'D10', 'E10'])

        ship = Ship(type=Ship.CRUISER, star_square='C4',
                    orientation=Ship.HORIZONTAL)
        self.assertEqual(ship.squares, ['C4', 'C5', 'C6'])

    def test_check_overlapping_ship(self):
        ship = Ship.create_ship(Ship.BATTLESHIP, 'D3', Ship.VERTICAL, save=False)
        ships = [Ship.create_ship(Ship.CRUISER, 'F6', Ship.HORIZONTAL, save=False)]
        ShipsManager(Ship, ships).check_overlapping_ship(ship)

        overlapping_ship = Ship.create_ship(Ship.DESTROYER, 'D2', Ship.HORIZONTAL, save=False)
        ships.append(overlapping_ship)
        self.assertRaises(ValueError, ShipsManager(Ship, ships).check_overlapping_ship(ship))

    def test_generate_restricted_grid_boundaries(self):
        ship_type, orientation = Ship.CRUISER, Ship.VERTICAL
        restricted_grid_boundaries = ShipsGenerator(Ship).generate_restricted_grid_boundaries(
            ship_type, orientation)
        self.assertEqual(restricted_grid_boundaries, [8, 10])

    def test_generate_ship(self):
        grid_boundaries, ship_type = [10, 7], Ship.BATTLESHIP
        orientation = Ship.HORIZONTAL
        ship = ShipsGenerator(Ship).generate_ship(grid_boundaries, ship_type, orientation)
        self.assertIsInstance(ship, Ship)

    def test_check_nearby_ships(self):
        generator = ShipsGenerator(Ship)
        generator.ships = [Ship.create_ship(Ship.CRUISER, 'B6', Ship.HORIZONTAL, save=False)]

        ship = Ship.create_ship(Ship.BATTLESHIP, 'E4', Ship.VERTICAL, save=False)
        generator.check_nearby_ships(ship)

        nearby_ship = Ship.create_ship(Ship.DESTROYER, 'G5', Ship.HORIZONTAL, save=False)
        generator.ships.append(nearby_ship)
        self.assertRaises(ValueError, generator.check_nearby_ships, ship)


class CreateGameTestCase(unittest.TestCase):
    """
    API unit tests.
    """

    def setUp(self):
        super(CreateGameTestCase, self).setUp()
        tb = testbed.Testbed()
        tb.setup_env(current_version_id='testbed.version')
        tb.activate()
        tb.init_all_stubs()
        self.api = SeaBattleApi()
        self.testbed = tb

        self.user = User(name='pepito', email='pepito@hotmail.com')
        self.user.put()

    def tearDown(self):
        self.testbed.deactivate()
        super(CreateGameTestCase, self).tearDown()

    def test_create_user(self):
        user = USER_REQUEST.combined_message_class(
            user_name='juanito', email='juanito@hotmail.com')

        response = self.api.create_user(user)
        self.assertEqual(response.message, 'User juanito created!')

    def test_new_game(self):
        new_game_request = NEW_GAME_REQUEST.combined_message_class(
            user_name='pepito', ships=get_player_ships())

        response = self.api.new_game(new_game_request)
        self.assertIsNotNone(response.urlsafe_key)
        self.assertFalse(response.game_over)
        self.assertIsNotNone(response.message)
        self.assertEquals(response.user_name, 'pepito')
        self.assertEqual(len(response.player_ships), 10)
        self.assertEqual(len(response.sunken_player_ships), 0)
        self.assertEqual(len(response.player_bombs), 0)
        self.assertEqual(len(response.opponent_bombs), 0)
        self.assertEqual(len(response.sunken_player_ships), 0)


class PlayGameTestCase(unittest.TestCase):
    def setUp(self):
        super(PlayGameTestCase, self).setUp()
        tb = testbed.Testbed()
        tb.setup_env(current_version_id='testbed.version')
        tb.activate()
        tb.init_all_stubs()
        self.api = SeaBattleApi()
        self.testbed = tb

        self.user = User(name='pepito', email='pepito@hotmail.com')
        self.user.put()

        ships = [Ship.create_ship(
            ship['type'], ship['star_square'], ship['orientation']).key
                 for ship in get_player_ships()]
        game = Game(player=self.user.key, player_ships=ships,
                    opponent_ships=ships)
        game.put()
        self.game = game.to_form(u'Sink ´em all!')
        self.opponent_ships = ships

    def tearDown(self):
        self.testbed.deactivate()
        super(PlayGameTestCase, self).tearDown()

    def test_get_game(self):
        game_request = GET_GAME_REQUEST.combined_message_class(
            urlsafe_game_key=self.game.urlsafe_key)
        found_game = self.api.get_game(game_request)

        self.assertEqual(self.game.user_name, found_game.user_name)
        self.assertEqual(self.game.player_ships, found_game.player_ships)

    def test_make_move(self):
        mis_bomb_request = MAKE_MOVE_REQUEST.combined_message_class(
            bomb='F4', urlsafe_game_key=self.game.urlsafe_key)
        game = self.api.make_move(mis_bomb_request)
        self.assertEqual(game.message, 'Mis')
        self.assertEqual(len(game.sunken_opponent_ships), 0)

        self.assertEqual(len(game.opponent_bombs), 1)

        opponent_ship_square = self.opponent_ships[0].get().to_form().star_square
        hit_bomb_request = MAKE_MOVE_REQUEST.combined_message_class(
            bomb=opponent_ship_square, urlsafe_game_key=self.game.urlsafe_key)
        game = self.api.make_move(hit_bomb_request)
        self.assertEqual(game.message, 'Hit')
        self.assertEqual(len(game.sunken_opponent_ships), 0)

        for ship in [ship_key.get() for ship_key in self.opponent_ships]:
            if ship.type == Ship.SUBMARINE:
                opponent_ship_square = ship.to_form().star_square
                break
        bomb_request = MAKE_MOVE_REQUEST.combined_message_class(
            bomb=opponent_ship_square, urlsafe_game_key=self.game.urlsafe_key)
        game = self.api.make_move(bomb_request)
        self.assertEqual(game.message, 'Hit')
        self.assertEqual(len(game.sunken_opponent_ships), 1)

    def test_win_a_game(self):
        for opponent_ship in self.opponent_ships[:]:
            for hit_bomb in opponent_ship.squares:
                hit_bomb_request = MAKE_MOVE_REQUEST.combined_message_class(
                    bomb=hit_bomb, urlsafe_game_key=self.game.urlsafe_key)
                self.api.make_move(hit_bomb_request)

    def test_lost_a_game(self):
        for ship in self.game.player_ships[:]:
            for hit_bomb in ship.squares:

                hit_bomb_request = MAKE_MOVE_REQUEST.combined_message_class(
                    bomb=hit_bomb, urlsafe_game_key=self.game.urlsafe_key)
                self.api.make_move(hit_bomb_request)

        # def test_get_scores(self):
        #     response = self.api.get_scores(message_types.VoidMessage())
        #     self.assertIsNotNone(response.items)


if __name__ == '__main__':
    unittest.main()