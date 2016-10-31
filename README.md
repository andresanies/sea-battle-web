#Sea Battle Back

This is a service API for a cloud based sea battle game on top of the App Engine platform.

## Set-Up Instructions:

1.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
1.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.
 
## Running the tests
1.  Set the `GAE_ROOT` variable at `tests.py` so the script can locate the app engine 
 libraries and run as stand alone script.
2. Run `python tests.py` in the root directory.
  
 
##Game Description:
 
Sea battle or Battleship is a guessing game. Each game begins with a player defined 
and computer generated fleet of 10 'ships' each one framed in a grid of 10 x 10 squares.
The player drop 'bombs' in the grid in order to sink all the opponent ships before 
the enemy sink the player fleet in turn based game.

Games are created through the `new_game` endpoint passing the 'username' and a 
list of 'ships' which structure is:
- 1 Battleship (4 squares)
- 2 Cruisers (3 squares)
- 3 Destroyers (2 squares)
- 4 Submarines (1 squares)

Each ship should have a type, a 'start square' defined by an upper case letter between A to J 
and a number from 1 to 10 like 'H5' and an orientation. The rest of the squares of the ships 
are derived from the start square and its type following the direction of the orientation(down the 
start square in vertical or right to it in horizontal). For example a Cruiser that starts 
at 'H5' in horizontal orientation fills the 'H5', 'H6' and 'H7' squares.
A sample data can be located under the `test_data` directory.

The types options are represented by:
- 1 = Battleship 
- 2 = Cruisers 
- 3 = Destroyers
- 4 = Submarines 

The orientation options are represented by:
- 1 = Vertical
- 2 = Horizontal

Bombs can be dropped at `make_move` with the `urlsafe_game_key` and a `bomb` square
which will reply the bomb result like 'Hit' or 'Mis' along with the game state.
The game state contains the result message of the dropped bomb, the player's 
and opponent's bombs, the player's and opponent's sunken ships, the user name, 
the player's ships, the url safe key of the game and a boolean indicating if the 
game is already over.


##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - ships.py: Validators and generators of ships.
 - bombers.py: Validators and generators of bombs.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.
 - tests.py: Unit testing for endpoints and Helper functions.

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists.
    
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, ships
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. ships is a list of 10
    ships in which each one has a type, start_square and orientation. Also adds a 
    task to a task queue to update the average moves remaining for active games.
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.
    
 - **get_game_history**
    - Path: 'game_history/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with the game moves record.
    - Description: Returns the list of bombs dropped by the player and 
    the opponent plus the player ships list.
 
 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, bomb
    - Returns: GameForm with new game state.
    - Description: Accepts a 'bomb' and returns the updated state of the game
    along with a message with the result of the bomb whether is a 'Hit' or a 'Mis'.
    If this causes a game to end, a corresponding Score entity will be created.
    
 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).
    
 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms. 
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.
    
 - **get_high_scores**
    - Path: 'high_scores'
    - Method: GET
    - Parameters: number_of_results(optional)
    - Returns: ScoreForms. 
    - Description: Returns a list of high scores ordered by the number 
    of bombs dropped in a won game(the best score took the least bombs to win).
 
 - **get_user_rankings**
    - Path: 'user_rankings'
    - Method: GET
    - Returns: RankingForms. 
    - Description: Returns a list of users and a performance ratio of each one 
    in descending order by the performance ratio. The performance ratio is 
    represented by wins / (loses + 1).
 
 - **get_average_attempts**
    - Path: 'games/average_attempts'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the average number of dropped bombs for all games
    from a previously cached memcache key.
    
 - **get_user_games**
    - Path: 'games/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms of the user.
    - Description: Returns all of a User's active games.
 
 - **cancel_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: DELETE
    - Parameters: urlsafe_game_key
    - Description: Cancels a game in progress by removing it from the database.


##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    
 - **Ship**
    - Stores a type, start_square and the orientation of each ship also holds 
    some ship validation logic.

 - **Bomb**
 - Stores the target square of the bomb and its result. 
 
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.
    
##Forms Included:
 - **ShipForm**
   - GameForm for describing a ship
 - **NewShipForm**
   -  
 - **BombForm**
   -   
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, attempts_remaining,
    game_over flag, message, user_name).
 - **GameHistoryForm**
   -
 - **NewGameForm**
    - Used to create a new game (user_name, min, max, attempts)
 - **MakeMoveForm**
    - Inbound make move form (guess).
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag,
    guesses).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **UserRankingForm**
    - 
 - **RankingForms**
    - 
 - **StringMessage**
    - General purpose String container.