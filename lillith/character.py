import lillith
from .api import Api
from .icons import IconObject
from .cached_property import cached_property

__all__ = ['Character']


class Character(IconObject):
    _icon_type = 'Character'
    _icon_ext = 'jpg'
    
    def __new__(cls, **kwargs):
        obj, = cls.filter(**kwargs)
        return obj

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
    def security_status(self):
        return self._data['securityStatus']

    @cached_property
    def account_balance(self):
        accounts = Api.fetch("/char/AccountBalance.xml.aspx", characterID=self.id)['accounts']
        return float(accounts[0]['balance'])

    @property
    def skills_in_training(self):
        pass

    @cached_property
    def assets(self):
        data = Api.fetch("/char/AssetList.xml.aspx", characterID=self.id)['assets']
        items = []

        def handle_container(container, items):
            for item in items:
                if "contents" in item:
                    new_container = lillith.ItemContainer(item)
                    handle_container(new_container, item['contents'])
                    container.add(new_container)
                else:
                    container.add(lillith.Item(item))

        for item in data:
            if 'contents' in item:
                container = lillith.ItemContainer(item)
                handle_container(container, item['contents'])
                items.append(container)
            else:
                items.append(lillith.Item(item))
        return items

    @classmethod
    def mine(cls):
        "Returns a list of your characters"
        data = Api.fetch("/account/Characters.xml.aspx")['characters']
        return [Character(id=c['characterID'], usekey=True) for c in data]

    @classmethod
    def filter(cls, id=None, name=None, usekey=False):
        if all([id is None, name is None]):
            raise ValueError("must provide one of id, name")
        if all([id is not None, name is not None]):
            raise ValueError("cannot specify both id and name")
        
        fetch = Api.fetch_nokey
        if usekey:
            fetch = Api.fetch

        if name is not None:
            # convert name to ID
            data = fetch("/eve/CharacterID.xml.aspx", names=name)
            id = data['characters'][0]['characterID']

        data = fetch("/eve/CharacterInfo.xml.aspx", characterID=id)

        obj = super().__new__(cls)
        obj._data = data
        obj.__init__()
        return [obj]
    
    
