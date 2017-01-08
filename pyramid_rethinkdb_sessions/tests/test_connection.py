# -*- coding: utf-8 -*-

import unittest

from pyramid import testing


class TestConnection(unittest.TestCase):
    def setUp(self):
        testing.setUp(self)
        self.request = testing.DummyRequest()

    def tearDown(self):
        testing.tearDown(self)

    def test_get_default_connection(self):
        from ..connection import get_default_connection
        options = dict(host='localhost', port=999)
        inst = get_default_connection(self.request,
                                      url='rethinkdb://admin:@localhost:28015/test',
                                      **options)
        self.assertEqual(inst.host, 'localhost')
        self.assertEqual(inst.port, 999)

    def test_get_default_connection_url_removes_duplicates(self):
        from ..connection import get_default_connection
        options = dict(host='localhost', port=999, password='password', db=5)
        url = 'rethinkdb://admin:@localhost:28015/test'
        inst = get_default_connection(self.request,
                                      url=url,
                                      **options)
        print(inst.__dict__)
        self.assertNotIn('password', inst.__dict__)
        self.assertNotIn('host', inst.__dict__)
        self.assertNotIn('port', inst.__dict__)
        self.assertNotIn('db', inst.__dict__)
