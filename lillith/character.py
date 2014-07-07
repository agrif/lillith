import lillith
import lillith.Api as Api
from .cached_property import cached_property

__all__ = ['Character']

class Character:
    def __init__(self, id, data=None):
        self.cid = id
        if data is None:
            self._data = Api.CharacterInfo.get(characterID=id)
        else:
            self._data = data
        if self._data.get("characterID") != id:
            raise ValueError("characterID mismatch")

    def __repr__(self):
        return "<Character {}>".format(self.name)

    @property
    def is_mine(self):
        return 'lastKnownLocation' in self._data

    @cached_property
    def last_known_location(self):
        if not self.is_mine:
            return None
        return lillith.SolarSystem(name=self._data['lastKnownLocation'])

    @property
    def bloodline(self):
        return self._data['bloodline']

    @property
    def name(self):
        return self._data['characterName']

    @property
    def id(self):
        return self._data['characterID']

    @property
    def race(self):
        return self._data['race']
    @property
    def securityStatus(self):
        return self._data['securityStatus']

    @cached_property
    def account_balance(self):
        balance = Api.AccountBalance.get(characterID=self.cid)
        return balance[0]['balance']

    @property
    def skills_in_training(self):
        pass

    @cached_property
    def assets(self):
        data = Api.AssetList.get(characterID=self.cid)
        items = []
        def handle_container(container, items):
            for item in items:
                if item['type'] == "container":
                    new_container = lillith.ItemContainer(item['item'])
                    handle_container(new_container, item['items'])
                    container.add(new_container)
                elif item['type'] == "item":
                    container.add(lillith.Item(item['item']))

        for item in data['items']:
            if item['type'] == 'item':
                items.append(lillith.Item(item['item']))
            elif item['type'] == 'container':
               container = lillith.ItemContainer(item['item']) 
               handle_container(container, item['items'])
               items.append(container)
        return items
                 

    @classmethod
    def mine(self):
        "Returns a list of your characters"
        return [Character(c['characterID']) for c in Api.CharacterList.get()]

    @classmethod
    def get_by_id(self, id):
        "Returns a character by ID"
        return Character(Api.CharacterID.get(id))
    
    @classmethod
    def filter(cls, id=None, name=None):
        if all([id is None, name is None]):
            raise ValueError("must provide one of id, name")
        if all([id is not None, name is not None]):
            raise ValueError("cannot specify both id and name")

        if id is not None:
            return [Character(c) for c in cls.list() if c['characterID'] == id]
        if name is not None:
            return [Character(c) for c in cls.list() if c['name'] == name]
                    
