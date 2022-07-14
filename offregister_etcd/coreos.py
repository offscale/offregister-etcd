from os import path

from offregister_fab_utils.misc import upload_template_fmt
from pkg_resources import resource_filename

from offregister_etcd import shared_serve


def install(*args, **kwargs):
    pass  # etcd is installed by default


def serve(c, etcd_discovery=None, size=3, *args, **kwargs):
    """
    :param c: Connection
    :type c: ```fabric.connection.Connection```
    """
    if kwargs["cluster_name"]:
        raise NotImplementedError(
            "Running multiple etcd clusters not yet implemented for CoreOS"
        )

    cluster_name = "etcd2"  # '-'.join(ifilter(None, ('etcd2', kwargs['cluster_name'])))
    if (
        c.run(
            "systemctl status {cluster_name}.service".format(cluster_name=cluster_name),
            warn=True,
            hide=True,
        ).exited
        == 0
    ):
        c.sudo(
            "systemctl stop {cluster_name}.service".format(cluster_name=cluster_name)
        )

    etcd_discovery = shared_serve(etcd_discovery, size, cluster_name, kwargs)

    data_dir = "/var/{cluster_name}_data_dir".format(cluster_name=cluster_name)
    c.sudo('mkdir -p "{data_dir}"'.format(data_dir=data_dir))

    upload_template_fmt(
        c,
        path.join(
            path.dirname(resource_filename("offregister.aux_recipes", "__init__.py")),
            "templates",
            "etcd2.systemd.conf",
        ),
        "/run/systemd/system/{cluster_name}.service.d/10-oem.conf".format(
            cluster_name=cluster_name
        ),
        context=locals(),
        use_sudo=True,
    )

    c.sudo("systemctl daemon-reload")
    c.sudo("systemctl start {cluster_name}.service".format(cluster_name=cluster_name))
    c.run("systemctl status {cluster_name}.service".format(cluster_name=cluster_name))
