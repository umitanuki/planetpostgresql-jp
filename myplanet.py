#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os, time
from datetime import datetime
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
#from google.appengine.api import urlfetch

from google.appengine.ext import db

from google.appengine.ext.webapp import template

from planet import feedparser, NewsItem

#class Feed(dict):
#  def __init__(self, name, url, link):
#    self.name = name
#    self.url = url
#    self.link = link

#feeds = [ Feed("Hitoshi Harada",
#            "http://postgresql.g.hatena.ne.jp/umitanuki/rss2",
#            "http://postgresql.g.hatena.ne.jp/umitanuki/"),
#          Feed("Takahiro Itagaki",
#            "http://postgresql.g.hatena.ne.jp/pgsql/rss2",
#            "http://postgresql.g.hatena.ne.jp/pgsql/"),
#          Feed("Akio Ishida",
#            "http://postgresql.g.hatena.ne.jp/iakio/rss2",
#            "http://postgresql.g.hatena.ne.jp/iakio/"),
#          Feed("Let's Postgres",
#            "http://lets.postgresql.jp/recent_changes/RSS",
#            "http://lets.postgresql.jp/") ]

class Feed(db.Model):
  name = db.StringProperty(required=True)
  url = db.LinkProperty(required=True)
  link = db.LinkProperty(required=True)
  last_update = db.DateTimeProperty(required=True, auto_now_add=True)
  

class PostEntry(db.Model):
  title = db.StringProperty(required=True)
  link = db.StringProperty(required=True)
#  description = db.TextProperty()
  content = db.TextProperty()
  author = db.StringProperty()
  entry_date = db.DateTimeProperty()
  create_date = db.DateTimeProperty()

class Channel(dict):
  def __init__(self, url):
    self.url = url
    self._cache = {}
    self.url_status = None
    self.updated = None
    self.last_updated = None
    self.info = None

  def fetch(self):
    info = feedparser.parse(self.url)
    if info.has_key("status"):
      self.url_status = str(info.status)
    elif info.has_key("entries") and len(info.entries)>0:
      self.url_status = str(200)
    elif info.bozo and info.bozo_exception.__class__.__name__=='Timeout':
      self.url_status = str(408)
    else:
      self.url_status = str(500)

    self.info = info
    self.last_updated = self.updated
    self.updated = time.gmtime()
    logging.info("Fetch Complete(%s) for %s", self.url_status, self.url)

  def entries(self):
    return self.info.entries


class DelHandler(webapp.RequestHandler):
  def get(self):
    q = db.GqlQuery("SELECT * FROM PostEntry")
    num = 0
    for result in q:
      result.delete()
      num += 1
    self.response.out.write("OK:num = %d" % num)

class AddHandler(webapp.RequestHandler):
  def get(self):
    logging.info("AddHandler")
    
    q = db.GqlQuery("SELECT * FROM Feed ORDER BY last_update ASC LIMIT 1")
    feed = q.get()
    
    url = feed.url
    channel = Channel(url)
    channel.fetch()
    for entry in channel.entries():
      entry_id = entry.link
      logging.info(entry_id)
      
      q = PostEntry.all()
      q.filter("link = ", entry.link)
      res = q.fetch(1)
      
      if len(res) > 0:
        logging.info("Already fetched link")
        continue

      item = NewsItem(channel, entry_id)
      item.update(entry)
      
      title = ""
      link = ""
      content = ""
      entry_date = None
      create_date = None
      if item.has_key("title"):
        title = item.title.decode("utf-8")
      if item.has_key("link"):
        link = item.link.decode("utf-8")
      if item.has_key("content"):
        content = item.content.decode("utf-8")
      if item.has_key("date"):
        entry_date = datetime(*item.date[:7])

      pe = PostEntry(title=title,
                     link=link,
                     content=content,
                     author=feed.name,
                     entry_date=entry_date,
                     create_date=datetime.now())
      pe.put()
    feed.last_update = datetime.now()
    feed.put()
    self.response.out.write("OK:" + feed.name)

class MainHandler(webapp.RequestHandler):
  def get(self):
    logging.info("start")

    items = db.GqlQuery("SELECT * FROM PostEntry ORDER BY entry_date DESC LIMIT 50")
    feeds = db.GqlQuery("SELECT * FROM Feed ORDER BY __key__")

    templ = "index.html"
    if self.request.params.get("mode") == "rss":
      templ = "rss20.xml"
    path = os.path.join(os.path.dirname(__file__), templ)
    self.response.out.write(template.render(path, {'items':items, 'feeds': feeds}))


def main():
  application = webapp.WSGIApplication([('/del', DelHandler),
                                        ('/add', AddHandler),
                                        ('/', MainHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
