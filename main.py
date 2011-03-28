#!/usr/bin/env python
#
# Copyright (c) 2011 Jonhnny Weslley <http://jonhnnyweslley.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

""" git achievements rank """

__author__ = 'Jonhnny weslley'

import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'python-github2'))

import re, logging, urllib2
from datetime import datetime, timedelta
from github2.client import Github
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

class RankEntry(db.Model):

  user = db.StringProperty(required=True)
  created = db.DateProperty(auto_now_add=True)
  last_modified = db.DateTimeProperty()
  unlocked_count = db.IntegerProperty(default=0)
  achievements_count = db.IntegerProperty(default=0)
  points = db.IntegerProperty(default=0)
  error = db.StringProperty()


def extract_points_from(result):
  """
  Expected line: "Unlocked 31/50 Git Achievements for 248 points"
  """
  pattern = re.compile(r'[^0-9]*Unlocked[^0-9]+(\d+)[^0-9]+(\d+)[^0-9]+(\d+)')
  for line in result.readlines():
    match = pattern.search(line)
    if match:
      return [int(n) for n in match.groups()]
  return None

def get_user_data(user_name):
  try:
    result = urllib2.urlopen('http://%s.github.com/git-achievements' % user_name)
    last_modified = datetime.strptime(
        result.headers['last-modified'], "%a, %d %b %Y %H:%M:%S %Z")
    points = extract_points_from(result)
    return {'user': user_name, 'last_modified': last_modified, 'points': points}

  except Exception, message:
    return {'user': user_name, 'error': str(message)}

def create_record_for(user_name):
  user_data = get_user_data(user_name)
  rentry = None
  if user_data.has_key('error'):
    rentry = RankEntry(user=user_data['user'], error=user_data['error'])
  elif not user_data['points']:
    rentry = RankEntry(user=user_data['user'], error='Points not found.')
  else:
    points = user_data['points']
    rentry = RankEntry(user      = user_data['user'],
              last_modified      = user_data['last_modified'],
              unlocked_count     = points[0],
              achievements_count = points[1],
              points             = points[2])
  try:
    rentry.put()
  except:
    logging.error('There was an error saving %s\'s points.', user_name)


class RankUpdater(webapp.RequestHandler):
  def get(self):
    logging.info('generating ranking...')
    network = Github().repos.network('icefox/git-achievements')
    users = [repo['owner'] for repo in network]
    for user in users:
      create_record_for(user)


class RankPage(webapp.RequestHandler):
  def get(self):
    last_updated = datetime.today().date()
    found = None
    while not found:
      query = RankEntry.all()
      query.filter('created =', last_updated)
      query.filter('error =', None)
      query.order('-points')
      found = query.get()
      last_updated = last_updated + timedelta(-1)

    rank = [entry for entry in query]
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, {'rank':rank}))

def main():
  application = webapp.WSGIApplication([
    ('/', RankPage),
    ('/update/', RankUpdater)
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == "__main__":
  main()
