"""A local filesystem backend.

Intended to be used only when running Airflow with a LocalExceutor.
"""
from __future__ import annotations

import shutil
import sys
from functools import partial
from pathlib import Path
from zipfile import ZipFile

from .base import DbtBackend, StrPath, zip_all_paths


class DbtLocalFsBackend(DbtBackend):
    """A concrete dbt backend for a local filesystem.

    This backend is intended to be used when running Airflow with a LocalExecutor, and
    it relies on shutil from the standard library to do all the file manipulation. For
    these reasons, running multiple concurrent tasks with this backend may lead to race
    conditions if attempting to push files to the backend.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def pull_one(self, source: StrPath, destination: StrPath) -> Path:
        """Pull a file from local path.

        Args:
            source: A local path to a directory containing the file to pull.
            destination: A destination path where to pull the file to.
        """
        destination_path = Path(destination)
        destination_path.parent.mkdir(exist_ok=True, parents=True)

        return shutil.copy(source, destination)

    def pull_many(self, source: StrPath, destination: StrPath) -> Path:
        """Pull many files from local path.

        Args:
            source: A local path to a directory containing the files to pull.
            destination: A destination path where to pull the file to.
        """
        if Path(source).suffix == ".zip":
            zip_destination = Path(destination) / "dbt_project.zip"
            shutil.copy(source, zip_destination)

            with ZipFile(zip_destination, "r") as zf:
                zf.extractall(zip_destination.parent)

            zip_destination.unlink()
        else:
            if sys.version_info.major == 3 and sys.version_info.minor < 8:
                shutil.copytree(source, destination)
            else:
                shutil.copytree(source, destination, dirs_exist_ok=True)

        return Path(destination)

    def push_one(
        self, source: StrPath, destination: StrPath, replace: bool = False
    ) -> None:
        """Pull many files from local path.

        If the file already exists, it will be ignored if replace is False (the
        default).

        Args:
            source: A local path to a directory containing the files to pull.
            destination: A destination path where to pull the file to.
            replace: A bool flag to indicate whether to replace existing files.
        """
        if replace is False and Path(destination).exists():
            return
        shutil.copy(source, destination)

    def push_many(
        self,
        source: StrPath,
        destination: StrPath,
        replace: bool = False,
        delete_before: bool = False,
    ) -> None:
        """Push all dbt files under the source directory to another local path.

        Pushing supports zipped projects: the destination will be used to determine
        if we are working with a zip file by looking at the file extension.

        Args:
            source: A local file path where to fetch the files to push.
            destination: A local path where the file should be copied.
            replace: Whether to replace existing files or not.
            delete_before: Whether to delete the contents of destination before pushing.
        """
        if Path(destination).suffix == ".zip":
            if delete_before:
                Path(destination).unlink()

            all_files = Path(source).glob("**/*")

            zip_path = Path(source) / ".temp.zip"
            zip_all_paths(all_files, zip_path=zip_path)

            shutil.copy(zip_path, destination)
        else:
            if delete_before:
                shutil.rmtree(destination)

            copy_function = partial(self.push_one, replace=replace)

            if sys.version_info.major == 3 and sys.version_info.minor < 8:
                shutil.copytree(source, destination, copy_function=copy_function)
            else:
                shutil.copytree(
                    source, destination, copy_function=copy_function, dirs_exist_ok=True
                )
