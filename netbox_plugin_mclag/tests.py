from dcim.models import Device, DeviceRole, DeviceType, Interface, Manufacturer, Site
from django.urls import reverse
from utilities.testing import TestCase

from .models import McDomain, McLag


class RelationshipAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        site = Site.objects.create(name='Test site', slug='test-site')
        manufacturer = Manufacturer.objects.create(name='Test manufacturer', slug='test-manufacturer')
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model='Test switch', slug='test-switch')
        role = DeviceRole.objects.create(name='Test role', slug='test-role')
        cls.devices = [
            Device.objects.create(name=f'Switch {index}', site=site, device_type=device_type, role=role)
            for index in range(2)
        ]
        cls.interfaces = [Interface.objects.create(device=device, name='bond0', type='lag') for device in cls.devices]

    def grant_permissions(self):
        self.user.is_superuser = True
        self.user.save()

    def test_domain_membership_create_update_and_nested_read(self):
        self.grant_permissions()
        response = self.client.post(
            reverse('plugins-api:netbox_plugin_mclag-api:mcdomain-list'),
            {'name': 'Test domain', 'devices': [device.pk for device in self.devices]},
            content_type='application/json',
        )
        self.assertHttpStatus(response, 201)
        domain = McDomain.objects.get(pk=response.json()['id'])
        self.assertEqual(set(domain.devices.values_list('pk', flat=True)), {device.pk for device in self.devices})
        self.assertEqual({device['id'] for device in response.json()['devices']}, {device.pk for device in self.devices})
        self.assertEqual(response.json()['mc_lags'], [])

        response = self.client.patch(
            reverse('plugins-api:netbox_plugin_mclag-api:mcdomain-detail', args=[domain.pk]),
            {'devices': [self.devices[0].pk]},
            content_type='application/json',
        )
        self.assertHttpStatus(response, 200)
        self.assertEqual(list(domain.devices.values_list('pk', flat=True)), [self.devices[0].pk])

    def test_lag_membership_create_update_read_and_delete(self):
        self.grant_permissions()
        domain = McDomain.objects.create(name='Test domain')
        domain.devices.set(self.devices)
        response = self.client.post(
            reverse('plugins-api:netbox_plugin_mclag-api:mclag-list'),
            {'name': 'Test LAG', 'mc_domain': domain.pk, 'interfaces': [interface.pk for interface in self.interfaces]},
            content_type='application/json',
        )
        self.assertHttpStatus(response, 201)
        lag = McLag.objects.get(pk=response.json()['id'])
        self.assertEqual(lag.mc_domain_id, domain.pk)
        self.assertEqual(set(lag.interfaces.values_list('pk', flat=True)), {interface.pk for interface in self.interfaces})
        self.assertEqual(response.json()['mc_domain']['id'], domain.pk)

        path = reverse('plugins-api:netbox_plugin_mclag-api:mclag-detail', args=[lag.pk])
        response = self.client.patch(path, {'interfaces': [self.interfaces[1].pk]}, content_type='application/json')
        self.assertHttpStatus(response, 200)
        self.assertEqual(list(lag.interfaces.values_list('pk', flat=True)), [self.interfaces[1].pk])
        self.assertEqual([interface['id'] for interface in self.client.get(path).json()['interfaces']], [self.interfaces[1].pk])
        self.assertHttpStatus(self.client.delete(path), 204)
        self.assertFalse(McLag.objects.filter(pk=lag.pk).exists())

    def test_invalid_membership_does_not_create_domain(self):
        self.grant_permissions()
        response = self.client.post(
            reverse('plugins-api:netbox_plugin_mclag-api:mcdomain-list'),
            {'name': 'Invalid domain', 'devices': [max(device.pk for device in self.devices) + 1]},
            content_type='application/json',
        )
        self.assertHttpStatus(response, 400)
        self.assertFalse(McDomain.objects.filter(name='Invalid domain').exists())
