# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json

from orchestrator import OrchestratorError

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from mgr_util import merge_dicts
from .orchestrator import OrchClient
from .. import mgr


class IscsiGatewayAlreadyExists(Exception):
    def __init__(self, gateway_name):
        super(IscsiGatewayAlreadyExists, self).__init__(
            "iSCSI gateway '{}' already exists".format(gateway_name))


class IscsiGatewayDoesNotExist(Exception):
    def __init__(self, hostname):
        super(IscsiGatewayDoesNotExist, self).__init__(
            "iSCSI gateway '{}' does not exist".format(hostname))


class IscsiGatewayInUse(Exception):
    def __init__(self, hostname):
        super(IscsiGatewayInUse, self).__init__(
            "iSCSI gateway '{}' is in use".format(hostname))


class InvalidServiceUrl(Exception):
    def __init__(self, service_url):
        super(InvalidServiceUrl, self).__init__(
            "Invalid service URL '{}'. "
            "Valid format: '<scheme>://<username>:<password>@<host>[:port]'.".format(service_url))


class ManagedByOrchestratorException(Exception):
    def __init__(self):
        super(ManagedByOrchestratorException, self).__init__(
            "iSCSI configuration is managed by the orchestrator")


_ISCSI_STORE_KEY = "_iscsi_config"


class IscsiGatewaysConfig(object):
    @classmethod
    def _load_config_from_store(cls):
        json_db = mgr.get_store(_ISCSI_STORE_KEY,
                                '{"gateways": {}}')
        return json.loads(json_db)

    @staticmethod
    def _load_config_from_orchestrator():
        config = {'gateways': {}}
        try:
            instances = OrchClient().list_service_info("iscsi")
            for instance in instances:
                config['gateways'][instance.nodename] = {
                    'service_url': instance.service_url
                }
        except (RuntimeError, OrchestratorError, ImportError):
            pass
        return config

    @classmethod
    def _save_config(cls, config):
        mgr.set_store(_ISCSI_STORE_KEY, json.dumps(config))

    @classmethod
    def validate_service_url(cls, service_url):
        url = urlparse(service_url)
        if not url.scheme or not url.hostname or not url.username or not url.password:
            raise InvalidServiceUrl(service_url)

    @classmethod
    def add_gateway(cls, name, service_url):
        config = cls.get_gateways_config()
        if name in config:
            raise IscsiGatewayAlreadyExists(name)
        IscsiGatewaysConfig.validate_service_url(service_url)
        config['gateways'][name] = {'service_url': service_url}
        cls._save_config(config)

    @classmethod
    def remove_gateway(cls, name):
        if name in cls._load_config_from_orchestrator()['gateways']:
            raise ManagedByOrchestratorException()

        config = cls._load_config_from_store()
        if name not in config['gateways']:
            raise IscsiGatewayDoesNotExist(name)

        del config['gateways'][name]
        cls._save_config(config)

    @classmethod
    def get_gateways_config(cls):
        orch_config = cls._load_config_from_orchestrator()
        local_config = cls._load_config_from_store()

        return {'gateways': merge_dicts(orch_config['gateways'], local_config['gateways'])}

    @classmethod
    def get_gateway_config(cls, name):
        config = IscsiGatewaysConfig.get_gateways_config()
        if name not in config['gateways']:
            raise IscsiGatewayDoesNotExist(name)
        return config['gateways'][name]
