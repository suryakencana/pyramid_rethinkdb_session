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
 # util
"""
from functools import partial
from hashlib import sha256
import os
import time
from .compat import urlparse
from pyramid.exceptions import ConfigurationError
from pyramid.settings import asbool

import rethinkdb as r

R_DB = 'rsessions'
R_TABLE = 'pyramid_sessions'


def parse_url(url):
    """
        host=host,
        port=port,
        db=db,
        user=user,
        password=password,
        ssl=ssl
    """
    options = dict()
    parse = urlparse(url)

    if 'rethinkdb' not in parse.scheme:
        raise Exception('unsupported protocol: ', parse.scheme)

    options['host'] = parse.hostname or 'localhost'

    if parse.port:
        options['port'] = parse.port

    print(parse.path)
    if parse.path and '/' not in parse.path[1:]:
        options['db'] = parse.path[1:]

    options['user'] = parse.username if parse.username else 'admin'
    options['password'] = parse.password if parse.password else ''

    return options


def _generate_session_id():
    """
    Produces a random 64 character hex-encoded string. The implementation of
    `os.urandom` varies by system, but you can always supply your own function
    in your ini file with:

        redis.sessions.id_generator = my_random_id_generator
    """
    rand = os.urandom(20)
    return sha256(sha256(rand).digest()).hexdigest()


def prefixed_id(prefix='session:'):
    """
    Adds a prefix to the unique session id, for cases where you want to
    visually distinguish keys in redis.
    """
    session_id = _generate_session_id()
    return prefix + session_id


def _insert_session_id_if_unique(
        conn,
        timeout,
        session_id,
        serialize,):
    """ Attempt to insert a given ``session_id`` and return the successful id
    or ``None``."""

    try:
        value = r.table(R_TABLE).get(session_id).run(conn)
        if value is not None:
            return None

        session_dict = {
            'id': session_id,
            'expired': timeout,
            'payload': r.binary(
                serialize({
                    'managed_dict':  {},
                    'created': time.time(),
                    'timeout': timeout
                })),
        }
        results = r.table(R_TABLE).insert(session_dict).run(conn)

        if results['errors'] > 0:
            raise KeyError(u'Session ID (%s) conflicts with an existing session' % session_id)

        return session_id
    except Exception:
        return None


def get_unique_session_id(
        conn,
        timeout,
        serialize,
        generator=_generate_session_id,):
    """
    Returns a unique session id after inserting it successfully in RethinkDB.
    """
    while 1:
        session_id = generator()
        attempt = _insert_session_id_if_unique(
            conn,
            timeout,
            session_id,
            serialize,
        )
        if attempt is not None:
            return attempt


def _parse_settings(settings):
    """
    Convenience function to collect settings prefixed by 'redis.sessions' and
    coerce settings to ``int``, ``float``, and ``bool`` as needed.
    """
    keys = [s for s in settings if s.startswith('rethink.sessions.')]

    options = {}

    for k in keys:
        param = k.split('.')[-1]
        value = settings[k]
        options[param] = value

    # only required setting
    if 'secret' not in options:
        raise ConfigurationError('rethink.sessions.secret is a required setting')

    # coerce bools
    for b in ('cookie_secure', 'cookie_httponly', 'cookie_on_exception'):
        if b in options:
            options[b] = asbool(options[b])

    # coerce ints
    for i in ('timeout', 'port', 'db', 'cookie_max_age'):
        if i in options:
            options[i] = int(options[i])

    # coerce float
    if 'socket_timeout' in options:
        options['socket_timeout'] = float(options['socket_timeout'])

    # check for settings conflict
    if 'prefix' in options and 'id_generator' in options:
        err = 'cannot specify custom id_generator and a key prefix'
        raise ConfigurationError(err)

    # convenience setting for overriding key prefixes
    if 'prefix' in options:
        prefix = options.pop('prefix')
        options['id_generator'] = partial(prefixed_id, prefix=prefix)

    return options


"""
    @classmethod
  def clear_expired(cls):

      # A method to remove all expired sessions

    rethinkdb_handler  = cls.__establish_rethinkdb()
    reference_time = time.mktime(timezone.now().timetuple())

    delete_request = rethinkdb.table(SESSION_RETHINK_TABLE).filter(rethinkdb.row["expire"] < reference_time).delete()
    delete_result  = delete_request.run(rethinkdb_handler)
"""


def refresh(wrapped):
    """
    Decorator to reset the expire time for this session's key in RethinkDB.
    """
    def wrapped_refresh(session, *arg, **kw):
        result = wrapped(session, *arg, **kw)
        session.expire(session.session_id, session.timeout)
        return result

    return wrapped_refresh
