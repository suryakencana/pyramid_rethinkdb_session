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
 # connection
"""

from .util import parse_url, R_DB, R_TABLE
import rethinkdb as r
import logging

LOG = logging.getLogger(__name__)


def get_default_connection(request,
                           url=None,
                           **rethink_options):

    conn = getattr(request.registry, '_r_conn', None)

    if conn is not None:
        return conn

    if url is not None:
        rethink_options.pop('password', None)
        rethink_options.pop('user', None)
        rethink_options.pop('host', None)
        rethink_options.pop('port', None)
        rethink_options.pop('db', None)

        rethink_options.update(parse_url(url))

    LOG.debug(rethink_options)
    conn = r.connect(**rethink_options)

    if rethink_options.get('db', R_DB) not in r.db_list().run(conn):
        r.db_create(R_DB).run(conn)

    if R_TABLE not in r.table_list().run(conn):
        r.table_create(R_TABLE).run(conn)

    setattr(request.registry, '_r_conn', conn)

    return conn
