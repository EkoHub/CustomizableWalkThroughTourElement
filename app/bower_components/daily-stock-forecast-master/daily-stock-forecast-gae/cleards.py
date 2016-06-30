
import webapp2
from google.appengine.ext import ndb
import numpy as np

from lib.Forecast import Forecast
from lib.StockList import StockList

class MainPage (webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        """
        for i in np.arange(250,6001,250):
            list_of_entities = Forecast.query(ndb.AND(Forecast.rank >= i-250,Forecast.rank < i))#Forecast.rank < 6000)
            list_of_keys = ndb.put_multi(list_of_entities)
            #list_of_entities = ndb.get_multi(list_of_keys)
            ndb.delete_multi(list_of_keys)

            list_of_entities = StockList.query(ndb.AND(StockList.rank >= i-250,StockList.rank < i))#Forecast.rank < 6000)
            list_of_keys = ndb.put_multi(list_of_entities)
            #list_of_entities = ndb.get_multi(list_of_keys)
            ndb.delete_multi(list_of_keys)
        """
        for i in np.arange(1,6001,500):
            list_of_keys = Forecast.query().fetch(500, keys_only=True)
            #list_of_keys = ndb.put_multi(list_of_entities)
            #list_of_entities = ndb.get_multi(list_of_keys)
            ndb.delete_multi(list_of_keys)

        list_of_keys = StockList.query().fetch(25, keys_only=True)
        #list_of_keys = ndb.put_multi(list_of_entities)
        #list_of_entities = ndb.get_multi(list_of_keys)
        ndb.delete_multi(list_of_keys)
        

        self.response.out.write('All Forecasts Deleted')
        self.redirect('./')

app = webapp2.WSGIApplication([
    ('/cleards', MainPage)
], debug=True)
