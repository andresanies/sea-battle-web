# -*- coding: utf-8 -*-
"""
ships.py: Holds validators and generators of ships.
"""

import random
from collections import Counter

__author__ = 'Andres Anies'
__email__ = 'andres_anies@hotmail.com'


class ShipsManager(object):
    """Manages the validation and creation of ships model instances"""

    def __init__(self, ship_model, raw_ships):
        self.ship_model = ship_model
        self.raw_ships = raw_ships
        self.ships = []

    def create_ships(self):
        """Creates a list of ships model instances from a raw representation"""
        self.check_number_of_ships_by_type()
        for ship in self.raw_ships:
            ship_instance = self.ship_model.create_ship(
                ship.type, ship.star_square, ship.orientation, save=False)
            self.ships.append(ship_instance)
        self.check_overlapping_ships()
        return self.save_ships()

    def check_number_of_ships_by_type(self):
        """Checks if we have the appropriate number of ships per type"""
        ships_types = [ship.type for ship in self.raw_ships]
        ships_types_count = dict(Counter(ships_types))

        if len(ships_types_count) > 4:
            raise ValueError('Too many ships')
        elif len(ships_types_count) < 4:
            raise ValueError('Too few ships')

        for ship_type, count in ships_types_count.items():
            if count > self.number_of_ships_by_type[ship_type]:
                raise ValueError(
                    'Too many %ss' % self.ship_model.TYPE_NAMES[ship_type])
            elif count < self.number_of_ships_by_type[ship_type]:
                raise ValueError(
                    'Too few %ss' % self.ship_model.TYPE_NAMES[ship_type])

    @property
    def number_of_ships_by_type(self):
        """Returns a mapping dictionary of ship type and the right
        number of correspondent ships"""
        return {
            self.ship_model.BATTLESHIP: 1,
            self.ship_model.CRUISER: 2,
            self.ship_model.DESTROYER: 3,
            self.ship_model.SUBMARINE: 4
        }

    def check_overlapping_ships(self):
        """Checks if there is any ship which whose squares fills the
        same space in the grid of other ship"""
        for test_ship in self.ships:
            self.check_overlapping_ship(test_ship)

    def check_overlapping_ship(self, test_ship):
        """Checks for a given ship if overlaps any other ship"""
        for ship in self.ships:
            if ship != test_ship:
                for square in test_ship.squares:
                    if square in ship.squares:
                        raise ValueError('%s overlapping %s at %s' % (
                            test_ship.type_name, ship.type_name, square))

    def save_ships(self):
        """Saves the created and validated ships into the database
        and returns a list of its keys"""
        saved_ships_keys = []
        for ship in self.ships:
            ship.put()
            saved_ships_keys.append(ship.key)

        return saved_ships_keys


class ShipsGenerator(ShipsManager):
    """Generates a list of ships randomly for the opponent"""

    def __init__(self, ship_model):
        super(ShipsManager, self).__init__()
        self.ship_model = ship_model
        self.ships = []

    def generate_opponents_ships(self):
        """Generates randomly a valid fleet of ships that fit in the game grid"""
        for ship_type in self.ship_model.TYPE_CHOICES:
            for _ in range(self.number_of_ships_by_type[ship_type]):
                orientation = random.randint(
                    1, len(self.ship_model.ORIENTATION_CHOICES))
                grid_boundaries = self.generate_restricted_grid_boundaries(
                    ship_type, orientation)

                ship = None
                while True:
                    try:
                        ship = self.generate_ship(
                            grid_boundaries, ship_type, orientation)
                        self.check_overlapping_ship(ship)
                        self.check_nearby_ships(ship)
                        break
                    except ValueError:
                        continue

                self.ships.append(ship)
        return self.save_ships()

    def generate_restricted_grid_boundaries(self, ship_type, orientation):
        """Returns the valid boundaries in which can be placed the start square
        of a given type of ship"""
        row_limit = 10
        column_limit = 10

        if orientation == self.ship_model.VERTICAL:
            row_limit -= (ship_type - 1)

        if orientation == self.ship_model.HORIZONTAL:
            column_limit = 10 - (ship_type - 1)

        return [row_limit, column_limit]

    def generate_ship(self, grid_boundaries, ship_type, orientation):
        """Generates a random start square for a ship inside the game grid
        and returns a not saved ship model instance"""
        row_limit, column_limit = grid_boundaries[0], grid_boundaries[1]

        row = chr(64 + random.randint(1, row_limit))
        column = random.randint(1, column_limit)

        star_square = "%s%d" % (row, column)

        return self.ship_model.create_ship(
            ship_type, star_square, orientation, save=False)

    def check_nearby_ships(self, test_ship):
        """Checks if there is any ship that has a square at the top, bottom,
        left or right of a test ship"""
        for ship in self.ships:
            for test_square in test_ship.squares:
                nearby_rows = [ord(test_square[0]) - 1, ord(test_square[0]) + 1]
                nearby_columns = [
                    int(test_square[1:]) - 1, int(test_square[1:]) + 1]
                for square in ship.squares:
                    is_in_the_same_row = square[0] == test_square[0]
                    is_in_the_same_column = square[1:] == test_square[1:]
                    if (ord(square[0]) in nearby_rows and
                            is_in_the_same_column) or \
                            (int(square[1:]) in nearby_columns and
                                 is_in_the_same_row):
                        raise ValueError()
