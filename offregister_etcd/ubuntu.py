from os import path

from fabric.api import cd, local, run, sudo
from fabric.contrib.files import append, upload_template
from offregister_fab_utils.fs import cmd_avail, get_tempdir_fab
from offregister_fab_utils.misc import ubuntu_install_curl
from offutils import update_d
from offutils.util import iteritems
from pkg_resources import resource_filename

from offregister_etcd import shared_serve


def install(version="v2.3.7", *args, **kwargs):
    command = "etcd"
    if cmd_avail(command):
        installed_version = (lambda s: s[s.rfind(" ") + 1 :])(
            run("etcd --version | head -n 1", quiet=True)
        )
        if version[1:] == installed_version:
            local(
                "echo {command} {version} is already installed".format(
                    command=command, version=version
                )
            )
            return

    tempdir = get_tempdir_fab(run_command=run)

    install_dir = "{tempdir}/{version}/{epoch}".format(
        tempdir=tempdir, version=version, epoch=run("date +%s", quiet=True)
    )
    run("mkdir -p {install_dir}".format(install_dir=install_dir))

    ubuntu_install_curl()
    with cd(install_dir):
        run(
            "curl -OL "
            "https://github.com/coreos/etcd/releases/download/{version}/etcd-{version}-linux-amd64.tar.gz".format(
                version=version
            )
        )
        run("tar xf etcd-{version}-linux-amd64.tar.gz".format(version=version))
        run(
            "sudo mv etcd-{version}-linux-amd64/etcd /usr/local/bin".format(
                version=version
            )
        )
        run(
            "sudo mv etcd-{version}-linux-amd64/etcdctl /usr/local/bin".format(
                version=version
            )
        )
    run("logout")  # Need to get stuff from /etc/environment on next run


def serve(etcd_discovery=None, size=3, *args, **kwargs):
    cluster_name = "-".join(_f for _f in ("etcd2", kwargs["cluster_name"]) if _f)

    status = run(
        "status {cluster_name}".format(cluster_name=cluster_name),
        warn_only=True,
        quiet=True,
    )
    if status.succeeded and status.endswith("start/running"):
        sudo("stop {cluster_name}".format(cluster_name=cluster_name))
        if "start/running" in run(
            "status {cluster_name}".format(cluster_name=cluster_name),
            warn_only=True,
            quiet=True,
        ):
            raise RuntimeError("Cluster hasn't stopped")
    etcd_discovery = shared_serve(etcd_discovery, size, kwargs)
    append(
        "/etc/environment",
        "ETCD_DISCOVERY={etcd_discovery}".format(etcd_discovery=etcd_discovery),
        use_sudo=True,
    )

    data_dir = "/var/{cluster_name}_data_dir".format(cluster_name=cluster_name)
    sudo('mkdir -p "{data_dir}"'.format(data_dir=data_dir))

    upload_template(
        path.join(
            path.dirname(resource_filename("offregister_etcd", "__init__.py")),
            "data",
            "etcd2.upstart.conf",
        ),
        "/etc/init/{cluster_name}.conf".format(cluster_name=cluster_name),
        context={k: str(v) for k, v in iteritems(update_d(kwargs, locals()))},
        use_sudo=True,
    )

    sudo("initctl reload-configuration")
    sudo("start {cluster_name}".format(cluster_name=cluster_name), warn_only=True)
    return etcd_discovery


def tail(method_args, n=10, *args, **kwargs):
    sudo("initctl list | grep etcd")  # Chuck error if it's not installed
    sudo(
        "tail -n {n} {method_args} /var/log/upstart/etcd2-{cluster_name}.log".format(
            cluster_name=kwargs.get("cluster_name"), method_args=method_args, n=n
        )
    )
