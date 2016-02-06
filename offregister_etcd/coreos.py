from os import path
from pkg_resources import resource_filename

from fabric.api import run, sudo, cd, local, settings
from fabric.contrib.files import append, upload_template

from offutils_strategy_register import _get_client as get_client
from offregister_etcd import get_etcd_discovery_url


def install(*args, **kwargs):
    pass  # etcd is installed by default


def serve(domain, node_name, public_ipv4, private_ipv4, etcd_discovery=None, size=3, *args, **kwargs):
    client = get_client()
    etcd_discovery = get_etcd_discovery_url(client, etcd_discovery, size)

    upload_template(
        path.join(path.dirname(resource_filename('offregister.aux_recipes', '__init__.py')),
                  'templates', 'etcd2.systemd.conf'),
        '/run/systemd/system/etcd2.service.d/10-oem.conf', context=locals(), use_sudo=True
    )

    if run('systemctl status etcd2.service', warn_only=True, quiet=True).failed:
        sudo('systemctl start etcd2.service')

    run('systemctl status etcd2.service')
    sudo('systemctl daemon-reload')
