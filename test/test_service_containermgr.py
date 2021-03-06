# Copyright (C) 2016  Red Hat, Inc
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Tests for commissaire_service.service.containermgr.ContainerManagerService.
"""

from . import TestCase, mock

import commissaire.constants as C

from commissaire.bus import ContainerManagerError
from commissaire.containermgr import ContainerManagerBase
from commissaire.storage import client
from commissaire_service.containermgr import ContainerManagerService


class TestContainerManagerService(TestCase):
    """
    Tests for the ContainerManagerService class.
    """

    def setUp(self):
        """
        Called before each test case.
        """
        self._connection_patcher = mock.patch(
            'commissaire_service.service.Connection')
        self._exchange_patcher = mock.patch(
            'commissaire_service.service.Exchange')
        self._producer_patcher = mock.patch(
            'commissaire_service.service.Producer')
        self._connection = self._connection_patcher.start()
        self._exchange = self._exchange_patcher.start()
        self._producer = self._producer_patcher.start()

        self.queue_kwargs = [
            {'name': 'simple', 'routing_key': 'simple.*'},
        ]

        self.service_instance = ContainerManagerService(
            'commissaire',
            'redis://127.0.0.1:6379/'
        )

    def tearDown(self):
        """
        Called after each test case.
        """
        self._connection.stop()
        self._exchange.stop()
        self._producer.stop()

    def test_config_notification(self):
        """
        Verify ContainerManagerService._config_notification works correctly
        """
        body = {
            'class': 'ContainerManagerConfig',
            'model': {
                'name': 'test',
                'type': C.CONTAINER_MANAGER_OPENSHIFT,
                'options': {'server_url': 'http://127.0.0.1'}
            }
        }
        message = mock.MagicMock()

        body['event'] = client.NOTIFY_EVENT_CREATED
        self.service_instance._config_notification(body, message)
        model = self.service_instance.managers.get('test')
        self.assertIsInstance(model, ContainerManagerBase)

        body['event'] = client.NOTIFY_EVENT_DELETED
        self.service_instance._config_notification(body, message)
        self.assertNotIn('test', self.service_instance.managers)

        # Events 'created' and 'updated' handled the same.
        body['event'] = client.NOTIFY_EVENT_UPDATED
        self.service_instance._config_notification(body, message)
        model = self.service_instance.managers.get('test')
        self.assertIsInstance(model, ContainerManagerBase)

    def test_on_node_registered(self):
        """
        Verify ContainerManagerService.on_node_registered returns proper data.
        """
        self.service_instance.refresh_managers = mock.MagicMock()

        message = mock.MagicMock(
            payload='',
            delivery_info={
            'routing_key': 'container.node_registered'})

        ch = mock.MagicMock()
        ch.node_registered.return_value = None
        self.service_instance.managers = {'test': ch}

        self.assertIsNone(
            self.service_instance.on_node_registered(
                message, 'test', '127.0.0.1'))

    def test_on_register_node_and_remove_node(self):
        """
        Verify on_register/remove_node/remove_all_nodes responds properly.
        """
        self.service_instance.refresh_managers = mock.MagicMock()

        for method_name, args in [
                ('register_node',    ('127.0.0.1',)),
                ('remove_node',      ('127.0.0.1',)),
                ('remove_all_nodes', ())]:
            message = mock.MagicMock(
                payload='',
                delivery_info={
                    'routing_key': 'container.{}'.format(method_name)})

            ch = mock.MagicMock()
            getattr(ch, method_name).return_value = None
            self.service_instance.managers = {'test': ch}

            method = getattr(self.service_instance, 'on_' + method_name)
            self.assertIsNone(method(message, 'test', *args))

    def test_on_register_node_and_remove_node_with_exceptions(self):
        """
        Verify on_register/remove_node/remove_all_nodes handle exceptions.
        """
        self.service_instance.refresh_managers = mock.MagicMock()

        for method_name, args in [
                ('register_node',    ('127.0.0.1',)),
                ('remove_node',      ('127.0.0.1',)),
                ('remove_all_nodes', ())]:
            message = mock.MagicMock(
                payload='',
                delivery_info={
                    'routing_key': 'container.{}'.format(method_name)})

            for exc in (ContainerManagerError, KeyError, Exception):
                # XXX: This isn't the exact place the exceptions would be
                # raised, but it is in the correct block
                ch = mock.MagicMock()
                getattr(ch, method_name).side_effect = exc('test')
                self.service_instance.managers = {'test': ch}

                method = getattr(self.service_instance, 'on_' + method_name)
                self.assertRaises(exc, method, message, 'test', *args)

    def test_on_get_node_status(self):
        """
        Verify ContainerManagerService.get_node_status returns proper data on success.
        """
        self.service_instance.refresh_managers = mock.MagicMock()

        message = mock.MagicMock(
            payload='',
            delivery_info={
            'routing_key': 'container.get_node_status'})

        expected = {'test': 'test'}
        ch = mock.MagicMock()
        ch.get_node_status.return_value = expected
        self.service_instance.managers = {'test': ch}

        self.assertEquals(
            expected,
            self.service_instance.on_get_node_status(
                message, 'test', '127.0.0.1'))

    def test_on_get_node_status_with_failure(self):
        """
        Verify ContainerManagerService.get_node_status returns proper data on failure.
        """
        self.service_instance.refresh_managers = mock.MagicMock()

        message = mock.MagicMock(
            payload='',
            delivery_info={
            'routing_key': 'container.get_node_status'})

        ch = mock.MagicMock()
        ch.get_node_status.side_effect = Exception
        self.service_instance.managers = {'test': ch}

        self.assertRaises(
            Exception,
            self.service_instance.on_get_node_status,
            message, 'test', '127.0.0.1')
