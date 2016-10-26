#!/usr/bin/env python
# -*- coding: utf-8 -*-
from distutils.core import setup, Distribution
from distutils.command.build_py import build_py as _build_py
from distutils.command.build_ext import build_ext as _build_ext
from distutils.extension import Extension
from Cython.Build.Dependencies import cythonize

import warnings
warnings.simplefilter("always")

import os
from glob import glob

opj = os.path.join


cythonize_dir = "build"

kwds = dict(include_dirs=[opj("src", "cysignals"),
                          opj(cythonize_dir, "src"),
                          opj(cythonize_dir, "src", "cysignals")],
            depends=glob(opj("src", "cysignals", "*.h")))

extensions = [
    Extension("cysignals.signals", ["src/cysignals/signals.pyx"], **kwds),
    Extension("cysignals.alarm", ["src/cysignals/alarm.pyx"], **kwds),
    Extension("cysignals.tests", ["src/cysignals/tests.pyx"], **kwds)
]


def write_if_changed(filename, text):
    """
    Write ``text`` to ``filename`` but only if it differs from the
    current content of ``filename``. If needed, the file and the
    containing directory are created.
    """
    try:
        f = open(filename, "r+")
    except IOError:
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError:
            pass
        f = open(filename, "w")
    else:
        if f.read() == text:
            # File is up-to-date
            f.close()
            return
        f.seek(0)
        f.truncate()

    print("generating {0}".format(filename))
    f.write(text)
    f.close()


# Run Distutils
class build_py(_build_py):
    """
    Custom distutils build_py class. For every package FOO, we also
    check package data for a "fake" FOO-cython package.
    """
    def get_data_files(self):
        """Generate list of '(package,src_dir,build_dir,filenames)' tuples"""
        data = []
        if not self.packages:
            return data
        for package in self.packages:
            for src_package in [package, package + "-cython"]:
                # Locate package source directory
                src_dir = self.get_package_dir(src_package)

                # Compute package build directory
                build_dir = os.path.join(*([self.build_lib] + package.split('.')))

                # Length of path to strip from found files
                plen = 0
                if src_dir:
                    plen = len(src_dir)+1

                # Strip directory from globbed filenames
                filenames = [
                    file[plen:] for file in self.find_data_files(src_package, src_dir)
                    ]
                data.append((package, src_dir, build_dir, filenames))
        return data


class build_ext(_build_ext):
    def finalize_options(self):
        _build_ext.finalize_options(self)
        self.create_init_pxd()
        ext_modules = self.distribution.ext_modules
        if ext_modules:
            self.distribution.ext_modules[:] = self.cythonize(ext_modules)

    def cythonize(self, extensions):
        return cythonize(extensions,
                build_dir=cythonize_dir, include_path=["src"])

    def create_init_pxd(self):
        """
        Create an ``__init__.pxd`` file in the build directory. This
        file will then be installed.

        The ``__init__.pxd`` file sets the correct compiler options for
        packages using cysignals.
        """
        dist = self.distribution

        # Determine installation directory
        inst = dist.get_command_obj("install")
        inst.ensure_finalized()
        install_dir = opj(inst.install_platlib, "cysignals")

        # The variable "init_pxd" is the string which should be written to
        # __init__.pxd
        init_pxd = "# distutils: include_dirs = {0}\n".format(install_dir)
        # Append __init__.pxd from configure
        init_pxd += self.get_init_pxd()

        init_pxd_file = opj(self.build_lib, "cysignals", "__init__.pxd")
        write_if_changed(init_pxd_file, init_pxd)

    def get_init_pxd(self):
        """
        Get the contents of ``__init__.pxd`` as generated by configure.
        """
        configure_init_pxd_file = opj(cythonize_dir, "src", "cysignals", "__init__.pxd")
        # Run configure if needed
        try:
            f = open(configure_init_pxd_file, "r")
        except IOError:
            import subprocess
            subprocess.check_call(["make", "configure"])
            subprocess.check_call(["sh", "configure"])
            f = open(configure_init_pxd_file, "r")
        with f:
            return f.read()


setup(
    name="cysignals",
    author=u"Martin R. Albrecht, François Bissey, Volker Braun, Jeroen Demeyer",
    author_email="sage-devel@googlegroups.com",
    version=open("VERSION").read().strip(),
    url="https://github.com/sagemath/cysignals",
    license="GNU Lesser General Public License, version 3 or later",
    description="Interrupt and signal handling for Cython",
    long_description=open('README.rst').read(),
    platforms=["POSIX"],

    ext_modules=extensions,
    packages=["cysignals"],
    package_dir={"cysignals": opj("src", "cysignals"),
                 "cysignals-cython": opj(cythonize_dir, "src", "cysignals")},
    package_data={"cysignals": ["*.pxi", "*.pxd", "*.h"],
                  "cysignals-cython": ["*.h"]},
    scripts=glob(opj("src", "scripts", "*")),
    cmdclass=dict(build_py=build_py, build_ext=build_ext),
)
