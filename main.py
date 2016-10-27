#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""

import webapp2
from google.appengine.api import mail, app_identity

from api import SeaBattleApi
from models import Game


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every hour using a cron job"""
        app_id = app_identity.get_application_id()
        games = Game.query(Game.game_over == False)
        # users = User.query(User.email != None)
        for game in games:
            subject = 'This is a reminder!'
            continue_game_endpoint = "https://sea-battle-web.appspot.com" \
                                     "/_ah/api/explorer" \
                                     "#p/sea_battle/v1/sea_battle.make_move" \
                                     "?urlsafe_game_key="
            body = u'Hello {}, you have a pending battle! <br> ' \
                   u'Be brave and <a href="{}">Sink ´em all!</a>'.format(
                game.player.name, continue_game_endpoint + game.key.urlsafe())
            # This will send test emails, the arguments to send_mail are:
            # from, to, subject, body
            mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                           game.player.email,
                           subject,
                           body)


class UpdateAverageMovesRemaining(webapp2.RequestHandler):
    def post(self):
        """Update game listing announcement in memcache."""
        SeaBattleApi._cache_average_attempts()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_average_attempts', UpdateAverageMovesRemaining),
], debug=True)
