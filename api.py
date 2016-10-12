# -*- coding: utf-8 -*-
import endpoints
from protorpc import remote, messages

from models import GameForm, MakeMoveForm
from models import StringMessage, NewGameForm
from models import User, Game, Ship, Bomb
from bombers import PlayerBomber, OpponentBomber
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1), )
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1), )
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))


@endpoints.api(name='sea_battle', version='v1')
class SeaBattleApi(remote.Service):
    """Game API"""

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
            request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')

        try:
            game = Game.new_game(user.key, request.ships)
        except ValueError as e:
            raise endpoints.BadRequestException(str(e))

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        # taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form(u'Sink ´em all!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game.game_over:
            return game.to_form('Game already over!')

        try:
            Ship.validate_square(request.bomb)
            result = PlayerBomber(game, request.bomb).bomb_ships()
            if game.game_over:
                return game.to_form('You won!')

            if game.player_bombs[-1].get().result != Bomb.HIT:
                OpponentBomber(game).bomb_ships()
                while game.opponent_bombs[-1].get().result == Bomb.HIT:
                    OpponentBomber(game).bomb_ships()

            if game.game_over:
                return game.to_form('You loose!')

            return game.to_form(result)

        except ValueError as e:
            raise endpoints.BadRequestException(str(e))


api = endpoints.api_server([SeaBattleApi])
