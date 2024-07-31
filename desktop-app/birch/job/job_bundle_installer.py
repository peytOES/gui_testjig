from pubsub import pub

from .job_bundle import *


class JobBundleInstaller():
    def __init__(self, bundle_class=JobBundle, input_dir="assets/input"):
        """
        Install job bundles in input directory.
        """
        input_dir = Path(input_dir)
        if not input_dir.exists():
            input_dir.mkdir()

        install_path = Path(input_dir).parent / "active"
        if not install_path.exists():
            install_path.mkdir()

        bundles = bundle_class.list_bundles(input_dir)

        installed = []
        for b in bundles:
            jb = bundle_class.from_zipfile(b)
            if jb.validate() and jb.install(install_path):
                installed.append(str(b))
            else:
                pub.sendMessage("system", message={
                    "message": "Failed to install %s\n%s" % (
                        b,
                        jb.validation_error_msg()
                    )
                })

        if len(installed) > 0:
            pub.sendMessage("system", message={
                "message": "Job bundles detected and installed:\n%s" % (
                    "\n".join(installed)
                )
            })
