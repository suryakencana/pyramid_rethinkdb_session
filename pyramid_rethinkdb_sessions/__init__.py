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
 # __init__.py
"""
import functools
import logging

from pyramid.session import (
    signed_deserialize,
    signed_serialize,
)
from .compat import cPickle
from .connection import get_default_connection
from pyramid_rethinkdb_sessions.session import RethinkDBSession
from .util import R_TABLE, get_unique_session_id, _parse_settings, _generate_session_id
import rethinkdb as r

LOG = logging.getLogger(__name__)


def includeme(config):
    """
    This function is detected by Pyramid so that you cna easily include
    `pyramid_rethinkdb_sessions` in your `main` method like so::

        config.include('pyramid_rethinkdb_sessions')

    Parameters:

    ``config``
    A pyramid ``config.Configurator``
    """
    settings = config.registry.settings

    # special rule for converting dotted python paths to callables
    for option in ('client_callable', 'serialize', 'deserialize',
                   'id_generator'):
        key = 'rethink.sessions.%s' % option
        if key in settings:
            settings[key] = config.maybe_dotted(settings[key])

    session_factory = session_factory_from_settings(settings)
    config.set_session_factory(session_factory)


def session_factory_from_settings(settings):
    """
    Convenience method to construct a ``RethinkSessionFactory`` from Paste config
    settings. Only settings prefixed with "rethink.sessions" will be inspected
    and, if needed, coerced to their appropriate types (for example, casting
    the ``timeout`` value as an `int`).

    Parameters:

    ``settings``
    A dict of Pyramid application settings
    """
    options = _parse_settings(settings)
    LOG.debug(options)
    return RethinkSessionFactory(**options)


def RethinkSessionFactory(
        secret,
        timeout=1200,
        cookie_name='session',
        cookie_max_age=None,
        cookie_path='/',
        cookie_domain=None,
        cookie_secure=False,
        cookie_httponly=True,
        cookie_on_exception=True,
        url=None,
        host='localhost',
        port=28015,
        db='rsessions',
        user='admin',
        password=None,
        ssl=None,
        socket_timeout=None,
        connection_pool=None,
        encoding='utf-8',
        encoding_errors='strict',
        unix_socket_path=None,
        client_callable=None,
        serialize=cPickle.dumps,
        deserialize=cPickle.loads,
        id_generator=_generate_session_id,):
    """
    Constructs and returns a session factory that will provide session data
    from a RethinkDB server. The returned factory can be supplied as the
    ``session_factory`` argument of a :class:`pyramid.config.Configurator`
    constructor, or used as the ``session_factory`` argument of the
    :meth:`pyramid.config.Configurator.set_session_factory` method.

    Parameters:

    ``secret``
    A string which is used to sign the cookie.

    ``timeout``
    A number of seconds of inactivity before a session times out.

    ``cookie_name``
    The name of the cookie used for sessioning. Default: ``session``.

    ``cookie_max_age``
    The maximum age of the cookie used for sessioning (in seconds).
    Default: ``None`` (browser scope).

    ``cookie_path``
    The path used for the session cookie. Default: ``/``.

    ``cookie_domain``
    The domain used for the session cookie. Default: ``None`` (no domain).

    ``cookie_secure``
    The 'secure' flag of the session cookie. Default: ``False``.

    ``cookie_httponly``
    The 'httpOnly' flag of the session cookie. Default: ``True``.

    ``cookie_on_exception``
    If ``True``, set a session cookie even if an exception occurs
    while rendering a view. Default: ``True``.

    ``url``
    A connection string for a RethinkDB server, in the format:
    rethinkdb://username:password@localhost:28015/rsessions
    conn = r.connect(host='localhost',
                 port=28015,
                 db='rethinksessions',
                 user='herofinder',
                 password='metropolis')
    Default: ``None``.

    ``host``
    A string representing the IP of your RethinkDB server. Default: ``localhost``.

    ``port``
    An integer representing the port of your RethinkDB server. Default: ``28015``.

    ``db``
    An integer to select a specific database on your RethinkDB server.
    Default: ``rsessions``

    ``user``
    A string user to connect to your RethinkDB server/database if
    required. Default: ``admin``.

    ``password``
    A string password to connect to your RethinkDB server/database if
    required. Default: ``None``.

    ``ssl``
    A hash of options to support SSL connections if required.
    Currently, there is only one option available, and if the ssl option is specified, this key is required:
    Default: ``None``.
        ssl={'ca_certs': '/path/to/ca.crt'}

    ``client_callable``
    A python callable that accepts a Pyramid `request` and RethinkDB config options
    and returns a RethinkDB client.
    Default: ``None``.

    ``serialize``
    A function to serialize the session dict for storage in RethinkDB.
    Default: ``cPickle.dumps``.

    ``deserialize``
    A function to deserialize the stored session data in RethinkDB.
    Default: ``cPickle.loads``.

    ``id_generator``
    A function to create a unique ID to be used as the session key when a
    session is first created.
    Default: private function that uses sha1 with the time and random elements
    to create a 40 character unique ID.

    host: host of the RethinkDB instance. The default value is localhost.
    port: the driver port, by default 28015.
    db: the database used if not explicitly specified in a query, by default test.
    user: the user account to connect as (default admin).
    password: the password for the user account to connect as (default '', empty).
    timeout: timeout period in seconds for the connection to be opened (default 20).
    ssl: a hash of options to support SSL connections (default None). Currently, there is only one option available, and if the ssl option is specified, this key is required:
    ca_certs: a path to the SSL CA certificate.

    """
    def factory(request, new_session_id=get_unique_session_id):
        rethinkdb_options = dict(
            host=host,
            port=port,
            db=db,
            user=user,
            password=password,
            ssl=ssl
        )

        conn = get_default_connection(request, url=url, **rethinkdb_options)

        # attempt to retrieve a session_id from the cookie
        # document UUID rethinkdb primary key
        session_id_from_cookie = _get_session_id_from_cookie(
            request=request,
            cookie_name=cookie_name,
            secret=secret,
        )

        new_session = functools.partial(
            new_session_id,
            conn=conn,
            timeout=timeout,
            serialize=serialize,
            generator=id_generator,
        )

        if session_id_from_cookie and r.table(R_TABLE) \
                .get(session_id_from_cookie).run(conn):
            session_id = session_id_from_cookie
            session_cookie_was_valid = True
        else:
            session_id = new_session()
            session_cookie_was_valid = False

        session = RethinkDBSession(
            conn=conn,
            session_id=session_id,
            new=not session_cookie_was_valid,
            new_session=new_session,
            serialize=serialize,
            deserialize=deserialize,
        )
        set_cookie = functools.partial(
            _set_cookie,
            session,
            cookie_name=cookie_name,
            cookie_max_age=cookie_max_age,
            cookie_path=cookie_path,
            cookie_domain=cookie_domain,
            cookie_secure=cookie_secure,
            cookie_httponly=cookie_httponly,
            secret=secret,
        )
        delete_cookie = functools.partial(
            _delete_cookie,
            cookie_name=cookie_name,
            cookie_path=cookie_path,
            cookie_domain=cookie_domain,
        )
        cookie_callback = functools.partial(
            _cookie_callback,
            session,
            session_cookie_was_valid=session_cookie_was_valid,
            cookie_on_exception=cookie_on_exception,
            set_cookie=set_cookie,
            delete_cookie=delete_cookie,
        )
        request.add_response_callback(cookie_callback)

        return session

    return factory


def _get_session_id_from_cookie(request, cookie_name, secret):
    """
    Attempts to retrieve and return a session ID from a session cookie in the
    current request. Returns None if the cookie isn't found or the value cannot
    be deserialized for any reason.
    """
    cookieval = request.cookies.get(cookie_name)

    if cookieval is not None:
        try:
            session_id = signed_deserialize(cookieval, secret)
            return session_id
        except ValueError:
            pass

    return None


def _set_cookie(
        session,
        request,
        response,
        cookie_name,
        cookie_max_age,
        cookie_path,
        cookie_domain,
        cookie_secure,
        cookie_httponly,
        secret,
):
    """
    `session` is via functools.partial
    `request` and `response` are appended by add_response_callback
    """
    cookieval = signed_serialize(session.session_id, secret)
    response.set_cookie(
        cookie_name,
        value=cookieval,
        max_age=cookie_max_age,
        path=cookie_path,
        domain=cookie_domain,
        secure=cookie_secure,
        httponly=cookie_httponly,
    )


def _delete_cookie(response, cookie_name, cookie_path, cookie_domain):
    response.delete_cookie(cookie_name, path=cookie_path, domain=cookie_domain)


def _cookie_callback(
        session,
        request,
        response,
        session_cookie_was_valid,
        cookie_on_exception,
        set_cookie,
        delete_cookie,
):
    """
    Response callback to set the appropriate Set-Cookie header.
    `session` is via functools.partial
    `request` and `response` are appended by add_response_callback
    """
    if session._invalidated:
        if session_cookie_was_valid:
            delete_cookie(response=response)
        return
    if session.new:
        if cookie_on_exception is True or request.exception is None:
            set_cookie(request=request, response=response)
        elif session_cookie_was_valid:
            # We don't set a cookie for the new session here (as
            # cookie_on_exception is False and an exception was raised), but we
            # still need to delete the existing cookie for the session that the
            # request started with (as the session has now been invalidated).
            delete_cookie(response=response)
