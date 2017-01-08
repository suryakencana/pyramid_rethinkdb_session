"""
 # Copyright (c) 2017 Boolein Integer Indonesia, PT.
 # suryakencana 1/8/17 @author nanang.suryadi@boolein.id
 #
 # You are hereby granted a non-exclusive, worldwide, royalty-free license to
 # use, copy, modify, and distribute this software in source code or binary
 # form for use in connection with the web services and APIs provided by
 # Boolein.
 #
 # As with any software that integrates with the Boolein platform, your use
 # of this software is subject to the Boolein Developer Principles and
 # Policies [http://developers.Boolein.com/policy/]. This copyright notice
 # shall be included in all copies or substantial portions of the software.
 #
 # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 # THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 # FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 # DEALINGS IN THE SOFTWARE
 # 
 # session
"""

import binascii
import os

from pyramid.compat import text_
from pyramid.decorator import reify
from pyramid.interfaces import ISession
from zope.interface import implementer

from .compat import cPickle, text_type
from .util import refresh, R_TABLE, persist

import rethinkdb as r


class _SessionState(object):
    def __init__(self, session_id, managed_dict, created, timeout, new):
        self.session_id = session_id
        self.managed_dict = managed_dict
        self.created = created
        self.timeout = timeout
        self.new = new


@implementer(ISession)
class RethinkDBSession(object):

    def __init__(self,
                 conn,
                 session_id,
                 new,
                 new_session,
                 serialize=cPickle.dumps,
                 deserialize=cPickle.loads):

        self.conn = conn
        self.serialize = serialize
        self.deserialize = deserialize
        self._new_session = new_session
        self._session_state = self._make_session_state(
            session_id=session_id,
            new=new,
        )

    @reify
    def _session_state(self):
        return self._make_session_state(
            session_id=self._new_session(),
            new=True,
        )

    def _make_session_state(self, session_id, new):
        persisted = self.from_r(session_id=session_id)
        # self.from_redis needs to take a session_id here, because otherwise it
        # would look up self.session_id, which is not ready yet as
        # session_state has not been created yet.
        return _SessionState(
            session_id=session_id,
            managed_dict=persisted['managed_dict'],
            created=persisted['created'],
            timeout=persisted['timeout'],
            new=new,
        )

    @property
    def session_id(self):
        return self._session_state.session_id

    @property
    def managed_dict(self):
        return self._session_state.managed_dict

    @property
    def created(self):
        return self._session_state.created

    @property
    def timeout(self):
        return self._session_state.timeout

    @property
    def new(self):
        return self._session_state.new

    def to_r(self):
        """Serialize a dict of the data that needs to be persisted for this
        session, for storage in Redis.

        Primarily used by the ``@persist`` decorator to save the current
        session state to Redis.
        """
        return self.serialize({
            'managed_dict': self.managed_dict,
            'created': self.created,
            'timeout': self.timeout,
        })

    def from_r(self, session_id=None):
        """Get and deserialize the persisted data for this session from Redis.
        """
        persisted = r.table(R_TABLE).get(session_id).run(self.conn)

        deserialized = self.deserialize(persisted['payload'])
        return deserialized

    def invalidate(self):
        """Invalidate the session."""
        r.table(R_TABLE).get(self.session_id).delete().run(self.conn)
        del self._session_state
        # Delete the self._session_state attribute so that direct access to or
        # indirect access via other methods and properties to .session_id,
        # .managed_dict, .created, .timeout and .new (i.e. anything stored in
        # self._session_state) after this will trigger the creation of a new
        # session with a new session_id.

    # dict modifying methods decorated with @persist
     @persist
    def __delitem__(self, key):
        del self.managed_dict[key]

    @persist
    def __setitem__(self, key, value):
        self.managed_dict[key] = value

    @persist
    def setdefault(self, key, default=None):
        return self.managed_dict.setdefault(key, default)

    @persist
    def clear(self):
        return self.managed_dict.clear()

    @persist
    def pop(self, key, default=None):
        return self.managed_dict.pop(key, default)

    @persist
    def update(self, other):
        return self.managed_dict.update(other)

    @persist
    def popitem(self):
        return self.managed_dict.popitem()

    # dict read-only methods decorated with @refresh
    @refresh
    def __getitem__(self, key):
        return self.managed_dict[key]

    @refresh
    def __contains__(self, key):
        return key in self.managed_dict

    @refresh
    def keys(self):
        return self.managed_dict.keys()

    @refresh
    def items(self):
        return self.managed_dict.items()

    @refresh
    def get(self, key, default=None):
        return self.managed_dict.get(key, default)

    @refresh
    def __iter__(self):
        return self.managed_dict.__iter__()

    @refresh
    def has_key(self, key):
        return key in self.managed_dict

    @refresh
    def values(self):
        return self.managed_dict.values()

    @refresh
    def itervalues(self):
        try:
            values = self.managed_dict.itervalues()
        except AttributeError: # pragma: no cover
            values = self.managed_dict.values()
        return values

    @refresh
    def iteritems(self):
        try:
            items = self.managed_dict.iteritems()
        except AttributeError: # pragma: no cover
            items = self.managed_dict.items()
        return items

    @refresh
    def iterkeys(self):
        try:
            keys = self.managed_dict.iterkeys()
        except AttributeError: # pragma: no cover
            keys = self.managed_dict.keys()
        return keys

    @persist
    def changed(self):
        """ Persist all the data that needs to be persisted for this session
        immediately with ``@persist``.
        """
        pass

    # session methods persist or refresh using above dict methods
    def new_csrf_token(self):
        token = text_(binascii.hexlify(os.urandom(20)))
        self['_csrft_'] = token
        return token

    def get_csrf_token(self):
        token = self.get('_csrft_', None)
        if token is None:
            token = self.new_csrf_token()
        else:
            token = text_type(token)
        return token

    def flash(self, msg, queue='', allow_duplicate=True):
        storage = self.setdefault('_f_' + queue, [])
        if allow_duplicate or (msg not in storage):
            storage.append(msg)
            self.changed()  # notify redis of change to ``storage`` mutable

    def peek_flash(self, queue=''):
        storage = self.get('_f_' + queue, [])
        return storage

    def pop_flash(self, queue=''):
        storage = self.pop('_f_' + queue, [])
        return storage

    # # RedisSession extra methods
    # @persist
    # def adjust_timeout_for_session(self, timeout_seconds):
    #     """
    #     Permanently adjusts the timeout for this session to ``timeout_seconds``
    #     for as long as this session is active. Useful in situations where you
    #     want to change the expire time for a session dynamically.
    #     """
    #     self._session_state.timeout = timeout_seconds

    @property
    def _invalidated(self):
        """
        Boolean property indicating whether the session is in the state where
        it has been invalidated but a new session has not been created in its
        place.
        """
        return '_session_state' not in self.__dict__

    def expire(self, session_id, timeout):
        session_dict = {
            'id': session_id,
            'expired': timeout,
            'payload': r.binary(self.to_r()),
        }
        results = r.table(R_TABLE).get(session_id).replace(session_dict).run(self.conn)

        if results['errors'] > 0:
            raise KeyError(u'Session ID (%s) conflicts with an existing session' % session_id)

