# -*- coding: utf-8 -*-
import endpoints
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from protorpc import remote, messages, message_types

from bombers import PlayerBomber, OpponentBomber
from models import GameForm, GameForms, MakeMoveForm
from models import RankingForms, UserRankingForm
from models import ScoreForms, GameHistoryForm
from models import StringMessage, NewGameForm
from models import User, Game, Ship, Bomb, Score
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1), )
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1), )
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'


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
        taskqueue.add(url='/tasks/cache_average_attempts')
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

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameHistoryForm,
                      path='game_history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_history_form()
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

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

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=ScoreForms,
                      path='high_scores',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Return the high scores"""
        scores = Score.query(Score.won == True).order(Score.bombs)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=RankingForms,
                      path='user_rankings',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Return the all players ranked by performance"""
        users = User.query()
        rankings = []
        for user in users:
            wins = len(Score.query(
                Score.user == user.key, Score.won == True).fetch())
            loses = len(Score.query(
                Score.user == user.key, Score.won == False).fetch())
            performance = wins / (loses + 1.0)
            rankings.append(UserRankingForm(name=user.name, performance=performance))

        rankings = sorted(rankings, key=lambda ranking: ranking.performance, reverse=True)

        return RankingForms(items=rankings)

    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(MEMCACHE_MOVES_REMAINING) or '')

    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average number of
        dropped bombs(attempts) of unfinished Games"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
            total_dropped_bombs = sum([len(game.player_bombs)
                                       for game in games])
            average = float(total_dropped_bombs) / count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average number of dropped bombs are {:.2f}'.format(average))

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='games/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all of an individual User's games"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        games = Game.query(Game.player == user.key)
        return GameForms(items=[game.to_form(u'Sink ´em all!') for game in games])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      path='game/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='DELETE')
    def cancel_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game and not game.game_over:
            game.key.delete()
            return message_types.VoidMessage()
        else:
            raise endpoints.NotFoundException('Game not found!')


api = endpoints.api_server([SeaBattleApi])
