#!/usr/bin/env python

__author__ = 'Samuel Marks'
__version__ = '0.0.1'

from etcd import EtcdKeyNotFound
from fabric.api import run


def get_etcd_discovery_url(client, etcd_discovery, size, discovery_path):
    try:
        etcd_discovery = client.get(discovery_path).value
    except EtcdKeyNotFound:
        etcd_discovery = etcd_discovery or run('curl https://discovery.etcd.io/new?size={size}'.format(size=size))
        client.set(discovery_path, etcd_discovery)

    return etcd_discovery
