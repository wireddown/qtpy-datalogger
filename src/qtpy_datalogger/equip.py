"""Functions for creating, configuring, and updating QT Py Datalogger sensor nodes."""

import datetime as dt
import functools
import logging
import pathlib
import shutil
import subprocess
import sys
import textwrap
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple

import bs4
import circup
import click
import findimports
import toml
from circup.lazy_metadata import LazyMetadata
from packaging.version import Version

from qtpy_datalogger import discovery

from .datatypes import UNKNOWN_VERSION, ConnectionTransport, ExitCode, Links, SnsrNotice, SnsrPath

CircupModuleCatalog = dict[str, LazyMetadata]

logger = logging.getLogger(__name__)
circup_logger = circup.logger
if not logger.isEnabledFor(logging.DEBUG):
    circup_logger.setLevel(logging.CRITICAL)

_PC_ONLY_IMPORTS = [
    "typing",
    "collections",
]

_EQUIP_IGNORE_PATTERNS = frozenset(
    {
        "__pycache__",
    }
)

_SNSR_NODE_SECRET_KEY_NAMES = frozenset(
    {
        "CIRCUITPY_WIFI_SSID",
        "CIRCUITPY_WIFI_PASSWORD",
        "QTPY_BROKER_IP_ADDRESS",
        "QTPY_NODE_GROUP",
        "QTPY_NODE_NAME",
    }
)

_ALLOWED_USER_APP_FILE_TYPES = frozenset(
    {
        ".json",
        ".py",
        ".toml",
    }
)

_FALLBACK_CPY_VERSION = Version("9.0.0")

_UNKNOWN_QTPY_BOARD_ID = "(unknown)"
_FALLBACK_QTPY_BOARD_ID = "adafruit_qtpy_esp32s3_nopsram"


class Behavior(StrEnum):
    """Supported installation behaviors for QT Py Datalogger sensor_node devices."""

    Compare = "Compare"
    Describe = "Describe"
    Force = "Force"
    Upgrade = "Upgrade"


class SecretsBehavior(StrEnum):
    """Supported behaviors for handling the --secrets option."""

    Analyze = "Analyze"
    Noop = "Noop"
    Update = "Update"

    def as_full_name(self) -> str:
        """Return a string of the value's full name."""
        return f"{self.__class__.__name__}.{self.name}"


class FileWithAge(NamedTuple):
    """Associates a file with its last modification time."""

    path: pathlib.Path
    """The path to the file."""

    age: dt.datetime
    """The last modification time of the file."""

    @staticmethod
    def from_path(path: pathlib.Path) -> "FileWithAge":
        """Create a FileWithAge using the file's absolute path."""
        modified_time = max(path.stat().st_mtime, 86400)  # Windows timezone bug, see python/cpython #107078
        timestamp = dt.datetime.fromtimestamp(modified_time).astimezone()
        return FileWithAge(path, timestamp)

    @staticmethod
    def make_relative(path: pathlib.Path, root: pathlib.Path) -> "FileWithAge":
        """Use the file's absolute path to get its age and return a FileWithAge with a relative path from the specified root."""
        as_absolute = FileWithAge.from_path(path)
        as_relative = FileWithAge(path.relative_to(root), as_absolute.age)
        return as_relative


class ModuleWithVersion(NamedTuple):
    """Associates a CircuitPython module with its version."""

    name: str
    """The name of the CircuitPython module."""

    version: Version
    """The version of the CircuitPython module."""


@dataclass(frozen=True, kw_only=True)
class ImportUsage:
    """Represents used, unused, and base references to imported modules."""

    used: Sequence[findimports.ImportInfo]
    """References to imported modules describing where they are used in their file."""

    unused: Sequence[findimports.ImportInfo]
    """References to imported modules that are unused in their file."""

    base: Sequence[str]
    """The first name segment of each imported module, usually the package name."""

    @staticmethod
    def from_files(paths: Sequence[pathlib.Path]) -> "ImportUsage":
        """Scan the specified files for imports and return a new ImportUsage instance."""
        all_used_imports = []
        all_unused_imports = []
        python_files = [str(path) for path in paths if path.suffix == ".py"]
        for file in python_files:
            used_imports, unused_imports = findimports.find_imports_and_track_names(file)
            all_used_imports.extend(used_imports)
            all_unused_imports.extend(unused_imports)

        all_import_names = sorted({used_import.name for used_import in all_used_imports})
        if all_import_names:
            logger.debug(f"Detected {len(all_import_names)} imports")
        for name in all_import_names:
            logger.debug(f" * {name}")

        all_base_imports = sorted(
            {str(name).split(".", maxsplit=1)[0] for name in all_import_names} - {*_PC_ONLY_IMPORTS}
        )
        import_usage = ImportUsage(used=all_used_imports, unused=all_unused_imports, base=all_base_imports)
        return import_usage

    @staticmethod
    def format_reference(import_: findimports.ImportInfo) -> str:
        """Format a string that reports the location of the specified import."""
        line = f" ! {import_.name:<20}  imported on  line {import_.lineno}  in  {import_.filename}"
        return line


@dataclass(frozen=True)
class AppDetails:
    """Describes a sensor_node app."""

    path: pathlib.Path
    """The path to the app."""

    @functools.cached_property
    def name(self) -> str:
        """The name of the app."""
        return self.path.stem

    @functools.cached_property
    def description(self) -> str:
        """The description of the app."""
        with self.path.open("r") as file:
            app_help = file.readline().strip().replace('"""', "")
        return app_help


@dataclass(frozen=True, kw_only=True)
class AppImportUsage:
    """Associates a collection of apps with their the import references."""

    details: Sequence[AppDetails]
    """The collection of apps with their details."""

    imports: ImportUsage
    """The imports referenced by the collection of apps."""

    @functools.cached_property
    def files(self) -> Sequence[pathlib.Path]:
        """Return the paths for each app in the collection."""
        return tuple(a.path for a in self.details)

    @staticmethod
    def from_files(files: Sequence[pathlib.Path]) -> "AppImportUsage":
        """Create an AppImportUsage from the specified files."""
        app_details = [AppDetails(file) for file in files]
        app_imports = ImportUsage.from_files(files)
        return AppImportUsage(details=app_details, imports=app_imports)


@dataclass(frozen=True, kw_only=True)
class SnsrFileTree:
    """Represents the file tree for a QT Py Datalogger sensor_node device."""

    root: pathlib.Path
    """The absolute path to the device's root folder."""

    relative_tree: Sequence[FileWithAge]
    """The relative paths for every folder and file under the device's root folder."""

    reserved_app_names: frozenset[str]
    """The app names reserved by the snsr runtime."""

    relative_runtime_apps: Sequence[FileWithAge]
    """The public apps as relative paths from the device's root folder."""

    @staticmethod
    def from_folder(main_folder: pathlib.Path) -> "SnsrFileTree":
        """Create a SnsrFileTree rooted at main_folder."""
        relative_tree = _collect_relative_folder_details(main_folder)
        reserved_app_names: list[str] = []
        relative_public_apps: list[FileWithAge] = []
        for relative_entry in relative_tree:
            if relative_entry.path.is_relative_to(SnsrPath.apps) and relative_entry.path.suffix == ".py":
                reserved_app_names.append(relative_entry.path.stem)
                if relative_entry.path.stem != "__init__":
                    relative_public_apps.append(relative_entry)
        return SnsrFileTree(
            root=main_folder,
            relative_tree=relative_tree,
            reserved_app_names=frozenset(reserved_app_names),
            relative_runtime_apps=relative_public_apps,
        )


@dataclass(frozen=True, kw_only=True)
class SnsrDeviceSnapshot:
    """Represents the version, contents, and dependencies for a CircuitPython device."""

    board_id: str
    """The hardware board ID of the CircuitPython device from Links.Board_Support_Matrix."""

    circuitpython: Version
    """The version of CircuitPython on the device."""

    builtin_imports: frozenset[str]
    """The builtin imports specific to the CircuitPython device's hardware support."""

    snsr_runtime: Version
    """The version of the QT Py Datalogger runtime on the device."""

    snsr_timestamp: dt.datetime
    """The timestamp of the QT Py Datalogger runtime on the device."""

    snsr_commit: str
    """The commit hash of the QT Py Datalogger runtime on the device."""

    apps: Sequence[AppDetails]
    """The QT Py Datalogger apps on the device."""

    files: SnsrFileTree
    """The file tree for the device."""

    snsr_imports: frozenset[str]
    """The import modules belonging to the QT Py Datalogger runtime."""

    external_imports: frozenset[str]
    """The import modules belonging to the CircuitPython ecosystem."""

    unused_imports: Sequence[findimports.ImportInfo]
    """The unused import references in the QT Py Datalogger runtime."""

    required_modules: Sequence[ModuleWithVersion]
    """The CircuitPython modules required by the QT Py Datalogger runtime and apps."""

    installed_modules: Sequence[ModuleWithVersion]
    """The CircuitPython modules installed on the device."""

    @functools.cached_property
    def root(self) -> pathlib.Path:
        """The path to the device's main folder."""
        return self.files.root

    @functools.cached_property
    def is_circuitpython_device(self) -> bool:
        """True when the device is a CircuitPython device."""
        return self.files.root.joinpath(SnsrPath.boot_out_txt).exists()

    @functools.cached_property
    def is_sensor_node(self) -> bool:
        """True when the device is a QT Py Datalogger sensor_node."""
        return self.files.root.joinpath(SnsrPath.notice_toml).exists()

    @staticmethod
    def as_runtime(board_id: str, circuitpy_version: Version) -> "SnsrDeviceSnapshot":
        """Create a package runtime SnsrDeviceSnapshot using the specified board_id and circuitpy_version."""
        this_file = pathlib.Path(__file__)
        this_folder = this_file.parent
        this_sensor_node_root = this_folder.joinpath("sensor_node")
        return SnsrDeviceSnapshot._create_new_snapshot(
            this_sensor_node_root,
            board_id,
            circuitpy_version,
            is_runtime=True,
        )

    @staticmethod
    def from_folder(folder: pathlib.Path) -> "SnsrDeviceSnapshot":
        """Create a SnsrDeviceSnapshot from the specified folder."""
        board_id, circuitpy_version = SnsrDeviceSnapshot._get_device_platform(folder)
        return SnsrDeviceSnapshot._create_new_snapshot(folder, board_id, circuitpy_version, is_runtime=False)

    @classmethod
    def _create_new_snapshot(
        cls,
        folder: pathlib.Path,
        board_id: str,
        circuitpy_version: Version,
        is_runtime: bool,
    ) -> "SnsrDeviceSnapshot":
        """Create a SnsrDeviceSnapshot from the specified folder with the specified board_id and circuitpy_version."""
        notice = SnsrDeviceSnapshot._get_device_notice(folder, is_runtime)
        file_tree = SnsrFileTree.from_folder(folder)
        apps = []
        for app_file in file_tree.relative_runtime_apps:
            app_details = AppDetails(file_tree.root.joinpath(app_file.path))
            apps.append(app_details)
        (
            unused_imports,
            snsr_imports,
            builtin_imports,
            external_imports,
        ) = SnsrDeviceSnapshot._get_imports(file_tree, board_id)
        required = CircupTool.query_required_modules(circuitpy_version, external_imports)
        installed = CircupTool.query_installed_modules(folder)

        return cls(
            board_id=board_id,
            circuitpython=circuitpy_version,
            builtin_imports=frozenset(builtin_imports),
            snsr_runtime=Version(notice.version),
            snsr_timestamp=notice.timestamp,
            snsr_commit=notice.commit,
            apps=tuple(apps),
            files=file_tree,
            snsr_imports=frozenset(snsr_imports),
            external_imports=frozenset(external_imports),
            unused_imports=tuple(unused_imports),
            required_modules=tuple(required),
            installed_modules=tuple(installed),
        )

    @staticmethod
    def _get_device_platform(main_folder: pathlib.Path) -> tuple[str, Version]:
        """Return the device's board_id and CircuitPython version."""
        boot_out_file = main_folder.joinpath(SnsrPath.boot_out_txt)
        if boot_out_file.exists():
            return CircupTool.get_circuitpython_platform(boot_out_file)
        return _FALLBACK_QTPY_BOARD_ID, _FALLBACK_CPY_VERSION

    @staticmethod
    def _get_device_notice(main_folder: pathlib.Path, for_this_runtime: bool) -> SnsrNotice:
        """Return the device's SnsrNotice information."""
        if for_this_runtime:
            return SnsrNotice.get_package_notice_info(allow_dev_version=True)
        notice_file = main_folder.joinpath(SnsrPath.notice_toml)
        if notice_file.exists():
            return CircupTool.get_snsr_notice(notice_file)
        return SnsrNotice.unknown()

    @staticmethod
    def _get_imports(
        device_files: SnsrFileTree,
        device_id: str,
    ) -> tuple[Sequence[findimports.ImportInfo], Sequence[str], Sequence[str], Sequence[str]]:
        """Scan the device_files for Python dependencies and return a tuple of (unused import references, runtime import names, builtin import names, and CircuitPython import names)."""
        rooted_snsr_runtime_files = [
            device_files.root.joinpath(entry.path)
            for entry in device_files.relative_tree
            if entry.path.is_relative_to(SnsrPath.root) or str(entry.path) == SnsrPath.code_py
        ]
        snsr_node_folders = [entry for entry in rooted_snsr_runtime_files if entry.is_dir()]
        snsr_node_files = [entry for entry in rooted_snsr_runtime_files if entry.suffix == ".py"]
        internal_folders = [folder.name for folder in snsr_node_folders]
        internal_files = [file.stem for file in snsr_node_files]
        internal_imports: set[str] = {*internal_folders, *internal_files}
        internal_imports.discard("__init__")

        builtin_circuitpython_imports = _load_builtin_import_data()
        stdlib_import_names = builtin_circuitpython_imports["standard_library"]
        builtin_import_names = builtin_circuitpython_imports[device_id]
        all_builtin_circuitpython_imports: set[str] = {*stdlib_import_names, *builtin_import_names}

        import_usage = ImportUsage.from_files(rooted_snsr_runtime_files)
        all_base_imports = import_usage.base

        external_import_names = set(all_base_imports) - internal_imports - all_builtin_circuitpython_imports
        external_imports = tuple(sorted(external_import_names))

        if all_base_imports:

            def get_import_mark(import_name: str) -> str:
                if import_name in external_import_names:
                    return "*"
                if import_name in builtin_circuitpython_imports:
                    return "."
                return "~"

            grouped_by_source = sorted(
                f"{get_import_mark(base_import):>2} {base_import}" for base_import in all_base_imports
            )
            logger.debug(f"Found {len(all_base_imports)} total import references   * external   . builtin   ~ internal")
            for line in grouped_by_source:
                logger.debug(line)

        return (
            import_usage.unused,
            sorted(internal_imports),
            sorted(all_builtin_circuitpython_imports),
            external_imports,
        )


@dataclass(frozen=True, kw_only=True)
class ModuleComparison:
    """Represents the differences between two collections of CircuitPython modules."""

    same: Sequence[ModuleWithVersion]
    """Modules with the same version in both collections."""

    newer: Sequence[ModuleWithVersion]
    """Modules in the first collection with higher versions than those in the second collection."""

    older: Sequence[ModuleWithVersion]
    """Modules in the first collection with lower versions than those in the second collection."""

    group1_only: Sequence[ModuleWithVersion]
    """Modules only in the first collection."""

    group2_only: Sequence[ModuleWithVersion]
    """Modules only in the second collection."""


@dataclass(frozen=True, kw_only=True)
class FileTreeComparison:
    """Groups files by their ages when comparing two file trees."""

    same: Sequence[FileWithAge]
    """Files with the same age in both trees."""

    newer: Sequence[FileWithAge]
    """Newer files in tree1."""

    older: Sequence[FileWithAge]
    """Older files in tree1."""

    tree1_only: Sequence[FileWithAge]
    """Files only in tree1."""

    tree2_only: Sequence[FileWithAge]
    """Files only in tree2."""


@dataclass(frozen=True, kw_only=True)
class SnsrDeviceComparison:
    """Represents the differences between two SnsrDeviceSnapshots."""

    runtime: SnsrDeviceSnapshot
    """This package's sensor_node snapshot."""

    device: SnsrDeviceSnapshot
    """The device's sensor_node snapshot used in the comparison."""

    file_changes: FileTreeComparison
    """The differences between their file trees."""

    required_modules_changes: ModuleComparison
    """The differences between their required CircuitPython modules."""

    installed_modules_changes: ModuleComparison
    """The differences between their installed CircuitPython modules."""

    @functools.cached_property
    def runtime_is_newer(self) -> bool:
        """True when this package's SnsrDeviceSnapshot is newer than the device's."""
        if self.runtime.snsr_runtime > self.device.snsr_runtime:
            return True
        return self.runtime.snsr_timestamp > self.device.snsr_timestamp

    @functools.cached_property
    def runtime_versions_match(self) -> bool:
        """True when the runtime versions of both this package and the sensor_node match."""
        return (
            self.runtime.snsr_runtime == self.device.snsr_runtime
            and self.runtime.snsr_timestamp == self.device.snsr_timestamp
        )

    @functools.cached_property
    def runtime_age_days(self) -> float:
        """The age difference in days between this package's runtime and the device's runtime."""
        age_difference = (self.runtime.snsr_timestamp - self.device.snsr_timestamp).total_seconds() / (3600.0 * 24)
        return age_difference

    @functools.cached_property
    def apps_in_runtime(self) -> Sequence[str]:
        """The names of the apps in this package's runtime."""
        runtime_apps = [app.path.stem for app in self.runtime.files.relative_runtime_apps]
        return runtime_apps

    @functools.cached_property
    def apps_in_device(self) -> Sequence[str]:
        """The names of the apps in the device."""
        device_apps = [app.path.stem for app in self.device.files.relative_runtime_apps]
        return device_apps

    @functools.cached_property
    def missing_apps(self) -> Sequence[str]:
        """The names of the apps that are missing on the device."""
        runtime_only_apps = sorted(set(self.apps_in_runtime) - set(self.apps_in_device))
        return runtime_only_apps

    @functools.cached_property
    def missing_files(self) -> Sequence[pathlib.Path]:
        """The runtime files that are missing on the device."""
        missing_runtime_files = [
            file.path
            for file in self.file_changes.tree1_only
            if not (file.path.is_relative_to("lib") or file.path.is_relative_to(SnsrPath.apps))
        ]
        return missing_runtime_files

    @functools.cached_property
    def missing_modules(self) -> Sequence[str]:
        """The dependencies that are missing on the device."""
        required_runtime_module_names = {m.name for m in self.runtime.required_modules}
        required_device_module_names = {m.name for m in self.device.required_modules}
        already_installed_modules = {m.name for m in self.device.installed_modules}
        missing_dependencies = tuple(
            sorted(required_runtime_module_names.union(required_device_module_names) - already_installed_modules)
        )
        return missing_dependencies

    @classmethod
    def between_runtime_and_device(
        cls,
        runtime: SnsrDeviceSnapshot,
        device: SnsrDeviceSnapshot,
    ) -> "SnsrDeviceComparison":
        """Compare the two SnsrDeviceSnapshots and return a new SnsrDeviceComparison."""
        file_report = _compare_snsr_file_trees(runtime.files, device.files)
        required_report = _compare_modules(runtime.required_modules, device.required_modules)
        installed_report = _compare_modules(runtime.installed_modules, device.installed_modules)
        return cls(
            runtime=runtime,
            device=device,
            file_changes=file_report,
            required_modules_changes=required_report,
            installed_modules_changes=installed_report,
        )


@dataclass(frozen=True, kw_only=True)
class EquipSnsrPlan:
    """Represents the details and requirements for installing components on a QT Py Datalogger sensor_node."""

    class Goal(StrEnum):
        """Describes the goal for the EquipSnsrPlan's outcome."""

        Force = "Force"
        Install = "Install"
        Repair = "Repair"
        SkipFiles = "SkipFiles"
        SkipVersion = "SkipVersion"
        UpgradeFiles = "UpgradeFiles"
        UpgradeSnapshot = "UpgradeSnapshot"
        UpgradeVersion = "UpgradeVersion"

    goal: Goal
    """The goal for the plan's outcome."""

    runtime_root: pathlib.Path
    """The path to the root of this package's runtime."""

    old_runtime_version: Version
    """The version of runtime on the device before installing."""

    new_runtime_version: Version
    """The version of runtime on the device after installing."""

    runtime_age_days: float
    """The age difference in days between the device's runtime and this package's runtime."""

    device_root: pathlib.Path
    """The path to the root of the device."""

    device_board_id: str
    """The CircuitPython board ID of the device."""

    device_circuitpython: Version
    """The version of the CircuitPython on the device."""

    copy_files: Sequence[pathlib.Path]
    """The runtime files to copy onto the device."""

    delete_files: Sequence[pathlib.Path]
    """The runtime files to delete from the device."""

    copy_apps: Sequence[pathlib.Path]
    """The app files to copy onto the device."""

    modules_to_install: Sequence[str]
    """The CircuitPython modules to install on the device."""

    @functools.cached_property
    def is_empty(self) -> bool:
        """True when the plan has nothing to install."""
        return (
            self.goal in (EquipSnsrPlan.Goal.SkipFiles, EquipSnsrPlan.Goal.SkipVersion) and not self.modules_to_install
        )


class CircupTool:
    """A facade for accessing CircuitPython devices and using the circup tool."""

    @staticmethod
    def get_circuitpython_platform(boot_out_file: pathlib.Path) -> tuple[str, Version]:
        """Return the device's board ID and CircuitPython version."""
        lines = boot_out_file.read_text().splitlines()
        logger.debug(f"Parsed '{boot_out_file}' with contents")
        for line in lines:
            logger.debug(line)
        circuitpy_version_line = lines[0]
        circuitpy_version_string = circuitpy_version_line.split(";")[0].split(" ")[-3]
        circuitpy_version = Version(circuitpy_version_string)
        board_id_line = lines[1]
        board_id = board_id_line.split(":")[-1]
        return board_id, circuitpy_version

    @staticmethod
    def get_snsr_notice(notice_file: pathlib.Path) -> SnsrNotice:
        """Return the SnsrNotice from the device."""
        file_contents = notice_file.read_text()
        logger.debug(f"Parsed '{notice_file}' with contents")
        for line in file_contents.splitlines():
            logger.debug(line)
        snsr_notice_toml = toml.loads(file_contents)
        snsr_notice = SnsrNotice(**snsr_notice_toml)
        return snsr_notice

    @staticmethod
    @functools.cache
    def load_circuitpython_module_catalog(circuitpy_version: Version) -> CircupModuleCatalog:
        """Load the available CircuitPython modules for the specified circuitpy_version."""
        # Adapted from circup.commands.install()
        bundle_tags = None
        device_platform = f"{circuitpy_version.major}mpy"
        available_modules = circup.get_bundle_versions(
            circup.get_bundles_list(bundle_tags, device_platform),
            avoid_download=True,
        )
        if not available_modules:
            available_modules = circup.get_bundle_versions(
                circup.get_bundles_list(bundle_tags, device_platform),
            )
        module_catalog = {
            str(module).replace(".py", "").lower(): metadata
            for module, metadata in sorted(available_modules.items())
            if isinstance(metadata, LazyMetadata)
        }
        return module_catalog  # ty: ignore[unsound-return-statement] -- the 'if isinstance' is sufficient

    @staticmethod
    def query_required_modules(
        circuitpy_version: Version,
        circuitpython_imports: Sequence[str],
    ) -> Sequence[ModuleWithVersion]:
        """Use circup to identify the CircuitPython modules that support the specified circuitpython_imports on circuitpy_version."""
        module_catalog = CircupTool.load_circuitpython_module_catalog(circuitpy_version)
        requested_installs = set(circuitpython_imports)
        all_installs = circup.get_dependencies(requested_installs, mod_names=module_catalog)
        modules_with_version = {
            ModuleWithVersion(mod_name, Version(module_catalog[mod_name].deferred_data["__version__"]))
            for mod_name in all_installs
        }
        return tuple(sorted(modules_with_version))

    @staticmethod
    def query_installed_modules(main_folder: pathlib.Path) -> Sequence[ModuleWithVersion]:
        """Use circup to detect the installed CircuitPython modules and versions found in the specified folder."""
        circup_backend = circup.DiskBackend(str(main_folder), circup_logger)
        installed_cp_modules = circup_backend.get_device_versions()
        modules_with_version = tuple(
            ModuleWithVersion(name, Version(details["__version__"]))
            for name, details in sorted(installed_cp_modules.items())
        )
        return modules_with_version

    @staticmethod
    def equip_modules(
        device_root: pathlib.Path,
        device_board_id: str,
        device_circuitpython: Version,
        modules_to_install: Sequence[str],
    ) -> int:
        """Use circup to install the specified CircuitPython modules."""
        if not modules_to_install:
            return ExitCode.Success

        circup_install_command = [
            "circup",
            "--path",
            str(device_root),
            "--board-id",
            device_board_id,
            "--cpy-version",
            str(device_circuitpython),
            "install",
            "--upgrade",
            *modules_to_install,
        ]
        logger.info(f"  Invoking '{' '.join(circup_install_command)}'")
        logger.info("")
        result = subprocess.run(circup_install_command, stdout=sys.stdout, stderr=subprocess.STDOUT, check=False)  # noqa: S603 -- command is well-formed and user cannot execute arbitrary code
        return_code = result.returncode
        return return_code

    """Handle the equip CLI command."""
    logger.debug(f"behavior: '{behavior}', root: '{root}', secrets: '{secrets}'")

    secrets_file = None
    if secrets == SecretsBehavior.Noop.as_full_name():
        secrets_behavior = SecretsBehavior.Noop
    elif secrets == SecretsBehavior.Analyze.as_full_name():
        secrets_behavior = SecretsBehavior.Analyze
    else:
        secrets_behavior = SecretsBehavior.Update
        if secrets == "-":
            pass
        else:
            secrets_file = pathlib.Path(secrets)
            if not (secrets_file.is_file() and secrets_file.exists()):
                logger.error(f"Cannot open secrets file '{secrets_file!s}'.")
                raise SystemExit(ExitCode.Secrets_File_Missing)

    this_file = pathlib.Path(__file__)
    this_folder = this_file.parent
    this_sensor_node_root = this_folder.joinpath("sensor_node")
    this_bundle = _detect_snsr_bundle(this_sensor_node_root)

    if behavior == Behavior.Describe:
        self_description = _format_bundle_description(this_bundle)
        _ = [logger.info(line) for line in self_description]
        raise SystemExit(ExitCode.Success)

    if not root:
        qtpy_device, communication_transport = discovery.discover_and_select_qtpy(
            group_id="",
            transport=ConnectionTransport.UART_Serial,
        )
        if not qtpy_device:
            logger.error("No QT Py devices found!")
            raise SystemExit(ExitCode.Discovery_Failure)
        if not isinstance(communication_transport, ConnectionTransport):
            logger.error(
                f"Cannot compare or equip '{qtpy_device.node_id}' with MQTT connection. Please connect with USB."
            )
            raise SystemExit(ExitCode.Equip_Without_USB_Failure)
        root = pathlib.Path(qtpy_device.drive_root).resolve()

    device_bundle = _detect_snsr_bundle(root)
    comparison_information = {
        "device bundle": device_bundle,
        "runtime bundle": this_bundle,
    }

    if secrets_behavior == SecretsBehavior.Analyze:
        node_secrets = _detect_node_secrets(device_bundle.device_files[0])
        secrets_description = _format_secrets_description(node_secrets)
        _ = [logger.info(line) for line in secrets_description]

    if behavior == Behavior.Compare:
        runtime_freshness = _compare_file_trees(
            this_bundle.device_files,
            device_bundle.device_files,
            _EQUIP_IGNORE_PATTERNS,
        )
        comparison_report = _format_bundle_comparison(comparison_information, runtime_freshness)
        _ = [logger.info(line) for line in comparison_report]
        raise SystemExit(ExitCode.Success)

    should_install, skip_reason = _should_install(behavior, comparison_information)

    match secrets_behavior:
        case SecretsBehavior.Noop:
            pass
        case SecretsBehavior.Analyze:
            pass
        case SecretsBehavior.Update:
            logger.info("Updating sensor_node secrets")
            _update_secrets(secrets_file, device_bundle.device_files[0])
            logger.info("Secrets updated")

    if should_install:
        _equip_snsr_node(behavior, comparison_information)
    else:
        logger.info(f"Skipping installation: {skip_reason}")


def _detect_snsr_bundle(main_folder: pathlib.Path) -> SnsrNodeBundle:
    """Build and return a SnsrNodeBundle by probing the specified folder."""
    # Begin with default sentinel values
    snsr_notice = SnsrNotice(
        comment="(uninitialized)",
        version="(missing)",
        commit="(missing)",
        timestamp=dt.datetime.fromisoformat("0001-01-01T01:01:01+00:00"),
    )
    device_files = []
    circuitpy_version = "9.2.1"
    board_id = "adafruit_qtpy_esp32s3_nopsram"
    circuitpy_dependencies = []
    installed_circuitpy_modules = []

    # Are we detecting a device or ourselves?
    this_file = pathlib.Path(__file__)
    this_folder_parent = this_file.parent
    main_folder_parent = main_folder.parent
    detecting_self = this_folder_parent == main_folder_parent

    notice_file = main_folder.joinpath(SnsrPath.notice)

    detect_message = f"Probing for sensor_node at '{main_folder}'"
    if detecting_self:
        snsr_notice = SnsrNotice.get_package_notice_info(allow_dev_version=True)
        detect_message = ""
    elif notice_file.exists():
        file_contents = notice_file.read_text()
        snsr_notice_toml = toml.loads(file_contents)
        snsr_notice = SnsrNotice(**snsr_notice_toml)

    # We only want to print information about the device, not ourselves
    should_log_info_messages = len(detect_message) > 0
    if should_log_info_messages or logger.isEnabledFor(logging.DEBUG):
        logger.info(detect_message)
        logger.info(f" - version    {snsr_notice.version}")
        logger.info(f" - timestamp  {snsr_notice.timestamp.strftime('%Y.%m.%d  %H:%M:%S')}")

    device_files = _recursive_folder_scan(main_folder)

    boot_out_file = main_folder.joinpath("boot_out.txt")
    if boot_out_file.exists():
        lines = boot_out_file.read_text().splitlines()
        logger.debug(f"Parsing '{boot_out_file}' with contents")
        _ = [logger.debug(line) for line in lines]
        circuitpy_version_line = lines[0]
        board_id_line = lines[1]
        circuitpy_version = circuitpy_version_line.split(";")[0].split(" ")[-3]
        board_id = board_id_line.split(":")[-1]

    circuitpy_dependencies = _get_circuitpython_dependencies(device_files, board_id, should_log_info_messages)
    installed_circuitpy_modules = _query_modules_from_circup(main_folder, should_log_info_messages)

    snsr_bundle = SnsrNodeBundle(
        snsr_notice,
        device_files,
        circuitpy_version,
        board_id,
        circuitpy_dependencies,
        installed_circuitpy_modules,
    )
    return snsr_bundle


def _format_bundle_description(bundle: SnsrNodeBundle) -> list[str]:
    """Format and return a list of lines that describes this package's sensor_node bundle."""
    report_contents = textwrap.dedent(
        f"""
        QT Py Data Logger Sensor Node
          Version:    {bundle.notice.version}  ({bundle.notice.commit})
          Timestamp:  {bundle.notice.timestamp.strftime("%Y.%m.%d  %H:%M:%S")}
          Homepage:   {Links.Homepage}

        Dependencies
          CircuitPython module           PC package name
          ====================   -{"-" * 31}-
        """
    ).splitlines()
    for circuitpy_library in bundle.circuitpy_dependencies:
        library_stub = "adafruit-circuitpython-{}".format(circuitpy_library.replace("adafruit_", ""))
        report_contents.append(f"  {circuitpy_library:>19}    {library_stub:>32}")
    return report_contents


def _format_bundle_comparison(
    comparison_information: dict[str, SnsrNodeBundle],
    file_freshness: dict[pathlib.Path, str],
) -> list[str]:
    """Format and return a list of lines that compares the specified sensor_node bundles."""
    device_bundle = comparison_information["device bundle"]
    this_bundle = comparison_information["runtime bundle"]

    newer_mark = "(newer)"
    older_mark = "       "
    same_mark = "(same) "
    try:
        device_version = packaging.version.Version(device_bundle.notice.version)
    except packaging.version.InvalidVersion:
        device_version = packaging.version.Version("0")
    device_timestamp = device_bundle.notice.timestamp
    self_version = packaging.version.Version(this_bundle.notice.version)
    self_timestamp = this_bundle.notice.timestamp

    self_is_newer = self_version > device_version
    if self_version == device_version:
        self_is_newer = self_timestamp > device_timestamp

    device_mark = older_mark if self_is_newer else newer_mark
    self_mark = newer_mark if self_is_newer else older_mark
    if self_version == device_version and self_timestamp == device_timestamp:
        device_mark = same_mark
        self_mark = same_mark

    report_contents = textwrap.dedent(
        f"""
        Comparing sensor_node device with this package
            Trait        Device {device_mark}                              Self {self_mark}
         ===========  -{"-" * 40}-  ----------------------
          Version      {device_version!s:<40}    {self_version!s}
          Timestamp    {device_timestamp.strftime("%Y.%m.%d  %H:%M:%S"):<40}    {self_timestamp.strftime("%Y.%m.%d  %H:%M:%S")}
          CircuitPy    {device_bundle.circuitpy_version:<40}    (PC host)
          Board ID     {device_bundle.board_id:<40}    (PC host)
          Location     {device_bundle.device_files[0]!s:<40}    (builtin)
        """
    )
    report_lines = report_contents.splitlines()

    newer_files = set()
    for path, freshness in sorted(file_freshness.items()):
        full_path = this_bundle.device_files[0].joinpath(path)
        if not full_path.is_file():
            continue
        if freshness == "newer":
            newer_files.add(path)
            continue
    if newer_files:
        newer_file_lines = ["\n", "Newer files"]
        newer_file_lines.extend([f"  * {file!s}\n" for file in sorted(newer_files)])
        report_lines.extend(newer_file_lines)
    return report_lines


def _should_install(behavior: Behavior, comparison_information: dict[str, SnsrNodeBundle]) -> tuple[bool, str]:
    """
    Use the comparison_information to decide whether to install or upgrade the sensor_node bundle.

    Returns a tuple with
    - a bool indicating whether the bundle should be installed
    - a string message explaining why the bundle should not be installed
    """
    this_bundle = comparison_information["runtime bundle"]
    device_bundle = comparison_information["device bundle"]

    my_version = packaging.version.Version(this_bundle.notice.version)
    should_install = False

    # Do the first lines from the device's code.py and our code.py match?
    device_main_folder = device_bundle.device_files[0]
    device_codepy_file = device_main_folder.joinpath("code.py")
    device_codepy_is_snsr_node = False
    if device_codepy_file.exists():
        device_first_line = device_codepy_file.read_text().splitlines()[0]
        snsr_codepy_first_line = this_bundle.device_files[0].joinpath("code.py").read_text().splitlines()[0]
        device_codepy_is_snsr_node = device_first_line == snsr_codepy_first_line

    skip_reason = ""
    if device_codepy_is_snsr_node:
        device_snsr_version = packaging.version.Version(device_bundle.notice.version)
        device_snsr_timestamp = device_bundle.notice.timestamp
        my_timestamp = this_bundle.notice.timestamp

        if behavior == Behavior.NewerFilesOnly:
            logger.info("Forcing installation of newer files")
            should_install = True
        elif my_version > device_snsr_version:
            logger.info("Upgrading version")
            logger.info(f"  Device is version  '{device_snsr_version}'")
            logger.info(f"  Runtime is version '{my_version}'")
            should_install = True
        elif my_timestamp > device_snsr_timestamp:
            logger.info("Upgrading snapshot")
            logger.info(f"  Device has timestamp  '{device_snsr_timestamp}'")
            logger.info(f"  Runtime has timestamp '{my_timestamp}'")
            should_install = True
        elif behavior == Behavior.Force:
            logger.info("Forcing installation")
            should_install = True
        else:
            skip_reason = "not an upgrade, use '--force' to override"
    else:
        logger.info("Initializing new QT Py Sensor Node")
        should_install = True

    return should_install, skip_reason


def _equip_snsr_node(behavior: Behavior, comparison_information: dict[str, SnsrNodeBundle]) -> None:
    """Install the sensor_node bundle and its CircuitPython dependencies."""
    device_bundle = comparison_information["device bundle"]
    device_main_folder = device_bundle.device_files[0]
    this_bundle = comparison_information["runtime bundle"]

    logger.info(f"Installing sensor_node v{this_bundle.notice.version} to '{device_main_folder}'")
    my_main_folder = this_bundle.device_files[0]
    device_snsr_root = device_main_folder.joinpath(SnsrPath.root)

    ignore_patterns = set(_EQUIP_IGNORE_PATTERNS)
    if behavior == Behavior.NewerFilesOnly:
        runtime_freshness = _compare_file_trees(
            this_bundle.device_files,
            device_bundle.device_files,
            frozenset(ignore_patterns),
        )
        older_files = set()
        newer_files = set()
        for path, freshness in sorted(runtime_freshness.items()):
            full_path = this_bundle.device_files[0].joinpath(path)
            if not full_path.is_file():
                continue
            if freshness == "newer":
                logger.info(f"  Newer: {path}")
                newer_files.add(path.name)
                continue
            older_files.add(path.name)
        if not newer_files:
            logger.info("All files up to date with the host")
            return
        ignored_files = older_files - newer_files
        ignore_patterns.update(ignored_files)
    elif device_snsr_root.exists():
        logger.info("  Copying snsr bundle")
        shutil.rmtree(device_snsr_root)

    shutil.copytree(
        src=my_main_folder,
        dst=device_main_folder,
        ignore=shutil.ignore_patterns(*ignore_patterns),
        dirs_exist_ok=True,
    )

    notice_file = device_main_folder.joinpath(SnsrPath.notice)
    notice_contents = _create_notice_file_contents(allow_dev_version=True)
    notice_file.write_text(notice_contents)

    if behavior == Behavior.NewerFilesOnly:
        logger.info("Bundle files updated")
        return

    circup_packages = this_bundle.circuitpy_dependencies
    return_code = ExitCode.Success
    if circup_packages:
        circup_install_command = [
            "circup",
            "--path",
            str(device_main_folder),
            "--board-id",
            device_bundle.board_id,
            "--cpy-version",
            device_bundle.circuitpy_version,
            "install",
            "--upgrade",
        ]
        circup_install_command.extend(circup_packages)
        logger.info("  Installing external dependencies with circup")
        logger.info(f"  Invoking '{' '.join(circup_install_command)}'")
        logger.info("")
        result = subprocess.run(circup_install_command, stdout=sys.stdout, stderr=subprocess.STDOUT, check=False)  # noqa: S603 -- command is well-formed and user cannot execute arbitrary code
        logger.info("")
        return_code = result.returncode

    if return_code == ExitCode.Success:
        device_main_folder.joinpath("code.py").touch()  # Restart the node
        logger.info("Installation complete")
    else:
        logger.error(f"circup exited with code '{return_code}'")


def _create_notice_file_contents(allow_dev_version: bool) -> str:
    """Format the notice.toml file for the package."""
    snsr_notice = SnsrNotice.get_package_notice_info(allow_dev_version)
    file_contents = str(toml.dumps(snsr_notice._asdict()))
    return file_contents


def _get_plugins(folder_list: list[pathlib.Path]) -> list[str]:
    """Return a list of the installed sensor_node plugins."""
    main_folder = folder_list[0]
    snsr_root = main_folder.joinpath(SnsrPath.root)
    plugins = [entry for entry in folder_list if entry.is_relative_to(snsr_root) and entry.is_dir()]
    return [entry.name for entry in plugins[1:]]


def _recursive_folder_scan(main_folder: pathlib.Path) -> list[pathlib.Path]:
    """Return a sorted list of all the files and folders under the specified folder."""
    logger.debug(f"Scanning folder '{main_folder}'")

    full_list = [main_folder]
    full_list.extend(_collect_file_list(main_folder))
    return full_list


def _collect_file_list(folder: pathlib.Path) -> list[pathlib.Path]:
    """Recursively collect the files and folders under the specified folder and return a sorted list."""
    if folder.is_dir():
        folder_contents = sorted(folder.iterdir())
        subfolders = [entry for entry in folder_contents if entry.is_dir()]
        for subfolder in subfolders:
            subfolder_list = _collect_file_list(subfolder)
            folder_contents.extend(subfolder_list)
        return sorted(folder_contents)
    return [folder]


def _compare_file_trees(
    tree1: list[pathlib.Path],
    tree2: list[pathlib.Path],
    ignore_list: frozenset[str],
) -> dict[pathlib.Path, str]:
    """Compare two lists of paths, identifying newer. A value of "newer" means tree1's file is newer than tree2's file."""
    set1 = {path.relative_to(tree1[0]) for path in tree1 if all(pattern not in str(path) for pattern in ignore_list)}
    set2 = {path.relative_to(tree2[0]) for path in tree2 if all(pattern not in str(path) for pattern in ignore_list)}
    shared_in_both = set1 & set2
    tree1_file_ages = {}
    for path in shared_in_both:
        modification_time1 = tree1[0].joinpath(path).stat().st_mtime
        modification_time2 = tree2[0].joinpath(path).stat().st_mtime
        age = "equal"
        if modification_time1 > modification_time2:
            age = "newer"
        if modification_time1 < modification_time2:
            age = "older"
        tree1_file_ages[path] = age
    for path in set1 - set2:
        tree1_file_ages[path] = "newer"
    return tree1_file_ages


def _get_circuitpython_dependencies(device_files: list[pathlib.Path], device_id: str, log_info: bool) -> list[str]:
    """Scan the sensor_node files for Python dependencies and return a list of external module imports."""
    # Get the folder and file names under the snsr folder
    main_folder = device_files[0]
    snsr_folder = main_folder.joinpath(SnsrPath.root)
    snsr_node_listing = [entry for entry in device_files if entry.is_relative_to(snsr_folder)]
    snsr_node_folders = [entry for entry in snsr_node_listing if entry.is_dir()]
    snsr_node_files = [entry for entry in snsr_node_listing if entry.is_file() and str(entry).endswith(".py")]

    # Collect the used and unused imports from each file
    all_used_imports = []
    all_unused_imports = []
    for file in snsr_node_files:
        used_imports, unused_imports = findimports.find_imports_and_track_names(str(file))
        all_used_imports.extend(used_imports)
        all_unused_imports.extend(unused_imports)
    all_import_names = sorted({module.name for module in all_used_imports})
    _ = [logger.debug(f" * {name}") for name in all_import_names]
    all_base_imports = sorted({name.split(".", maxsplit=1)[0] for name in all_import_names} - {*_PC_ONLY_IMPORTS})
    if all_unused_imports:
        logger.warning("Detected unused imports")
        _ = [logger.warning(f" * {module.name}") for module in all_unused_imports]

    # Group the internal module names
    internal_folders = [folder.name for folder in snsr_node_folders]
    internal_files = [file.stem for file in snsr_node_files]
    internal_modules = {*internal_folders, *internal_files}
    internal_modules.discard("__init__")
    internal_modules.discard("__pycache__")

    # Group the builtin CircuitPython module names
    this_file = pathlib.Path(__file__)
    builtin_circuitpython_modules_file = this_file.with_name("builtin_circuitpython_modules.toml")
    builtin_circuitpython_modules = toml.load(builtin_circuitpython_modules_file)
    stdlib_module_names = builtin_circuitpython_modules["standard_library"]
    builtin_module_names = builtin_circuitpython_modules.get(device_id, [])
    if not builtin_module_names:
        logger.warning(f"Missing information for builtin modules on CircuitPython device '{device_id}'")
        logger.warning(f"  Visit '{Links.Board_Support_Matrix}' and find your BOARD NAME")
        logger.warning(
            "  Then use 'qtpy-datalogger --list-builtin-modules \"BOARD NAME\" -' to get the builtin modules"
        )
        logger.warning(f"  And create a new Issue with this information at '{Links.New_Bug}'")
    all_builtin_circuitpython_modules = {*stdlib_module_names, *builtin_module_names}
    name_collisions = all_builtin_circuitpython_modules & internal_modules
    if name_collisions:
        logger.warning("Detected module name collisions")
        _ = [logger.warning(f" * {module}") for module in name_collisions]

    # The external CircuitPython module names remain after we remove the internal names and the builtin names
    external_module_names = {*all_base_imports} - internal_modules - all_builtin_circuitpython_modules

    # Show an import report
    if all_base_imports and (log_info or logger.isEnabledFor(logging.DEBUG)):

        def get_module_mark(module_name: str) -> str:
            if module_name in external_module_names:
                return "*"
            if module_name in all_builtin_circuitpython_modules:
                return "."
            return "~"

        grouped_by_source = sorted([f"{get_module_mark(module):>2} {module}" for module in all_base_imports])
        logger.info(f"Found {len(all_base_imports)} total module references   * external   . builtin   ~ internal")
        _ = [logger.info(line) for line in grouped_by_source]
    return sorted(external_module_names)


def _query_modules_from_circup(main_folder: pathlib.Path, log_info: bool) -> list[tuple[str, str]]:
    """Use circup to detect the installed CircuitPython modules and versions found in the specified folder."""
    if main_folder.joinpath("lib").exists() and (log_info or logger.isEnabledFor(logging.DEBUG)):
        logger.info("Detecting installed external CircuitPython modules")

    circup_logger = logger
    if not logger.isEnabledFor(logging.DEBUG):
        muted_logger = logging.getLogger("muted")
        muted_logger.setLevel(logging.CRITICAL)
        circup_logger = muted_logger
    circup_backend = circup.DiskBackend(str(main_folder), circup_logger)
    installed_cp_modules = circup_backend.get_device_versions()
    if installed_cp_modules and (log_info or logger.isEnabledFor(logging.DEBUG)):
        _ = [
            logger.info(f" * {name:<20} {details['__version__']}")
            for name, details in sorted(installed_cp_modules.items())
        ]
    modules_with_version = [
        (str(name), str(details["__version__"])) for name, details in sorted(installed_cp_modules.items())
    ]
    return modules_with_version


def _detect_node_secrets(main_folder: pathlib.Path) -> dict[str, bool]:
    """Parse the settings.toml file in the main_folder and return a dictionary of detected secrets."""
    expected_secrets = dict.fromkeys(_SNSR_NODE_SECRET_KEY_NAMES, False)
    settings_file = main_folder.joinpath(SnsrPath.settings_toml)
    if not settings_file.exists():
        return expected_secrets
    device_settings = toml.load(settings_file)
    detected_secrets = {
        secret: secret in device_settings
        for secret in sorted(expected_secrets)
    }  # fmt: skip
    return detected_secrets


def _print_secrets_description(node_secrets: dict[str, bool]) -> None:
    """Format and print a summary that describes node_secrets."""
    secrets_report = []
    secrets_report.append("Detected secrets")
    for secret_name, is_defined in node_secrets.items():
        message = "ok" if is_defined else click.style("MISSING", "yellow")
        secrets_report.append(f" * {secret_name:<24}  {message}")
    for line in secrets_report:
        logger.info(line)


def _update_secrets(new_secrets_file: pathlib.Path | None, main_folder: pathlib.Path) -> None:
    """Update the settings.toml file in the main_folder."""
    secrets_file = main_folder.joinpath(SnsrPath.settings_toml)
    if new_secrets_file:
        shutil.copy(new_secrets_file, secrets_file)
        return

    click.echo()
    click.echo(f"Set a new value or press {click.style('<Enter>', 'bright_cyan')} to skip")
    new_secrets = {}
    detected_secrets = _detect_node_secrets(main_folder)
    for secret in detected_secrets:
        user_input = click.prompt(
            text=f"  {click.style(secret, 'bright_green')}",
            default="",
            hide_input=True,
            type=str,
            show_default=False,
        )
        if user_input:
            new_secrets[secret] = user_input
    click.echo()

    final_secrets = new_secrets.copy()
    if secrets_file.exists():
        old_secrets = toml.load(secrets_file)
        final_secrets.update(old_secrets)  # Retain unrelated toml entries
        final_secrets.update(new_secrets)  # Overlay the new secrets
    with secrets_file.open("w") as secrets_fd:
        toml.dump(final_secrets, secrets_fd)


def _handle_generate_notice() -> str:
    """Handle the CLI option '--generate-notice'."""
    # We do not allow dev versions because we use this to stamp the version at release build time
    return _create_notice_file_contents(allow_dev_version=False)


def _handle_list_builtin_modules(board_id: str) -> str:
    """Handle the CLI option '--list-builtin-modules'."""

    # We define these as functions to reclaim their memory usage from parsing the HTML contents, which can be very large
    def fetch_find_extract_builtin_modules_for_board_id(reference_url: str, board_id: str) -> tuple[str, list[str]]:
        page_request = urllib.request.Request(reference_url, headers={"User-agent": "Mozilla/5.0"})  # noqa: S310 -- URL is hardcoded to https
        live_html_bytes = urllib.request.urlopen(page_request).read()  # noqa: S310 -- URL is hardcoded to https
        live_html = live_html_bytes.decode("UTF-8")
        soup = bs4.BeautifulSoup(live_html, "html.parser")
        if not isinstance(soup.title, bs4.Tag):
            logger.error(f"Missing page title for {reference_url}")
            raise SystemExit(ExitCode.Board_Lookup_Failure)
        page_title = soup.title.text.split("-")[0].strip()
        reference_version = soup.title.text.split("—")[-1].strip()
        logger.info(f"Loaded '{page_title}' from '{reference_version}'")

        def row_matches_board_id(tag: bs4.Tag) -> bool:
            if tag.name != "tr":
                return False
            if not isinstance(tag.td, bs4.Tag):
                return False
            if not isinstance(tag.td.p, bs4.Tag):
                return False
            return tag.td.p.text == board_id

        the_table = soup.find("table", class_="support-matrix-table")
        if not isinstance(the_table, bs4.Tag):
            logger.error(f"Cannot find 'support-matrix-table' on {reference_url}")
            raise SystemExit(ExitCode.Board_Lookup_Failure)
        the_row = the_table.find(name=row_matches_board_id)
        if not isinstance(the_row, bs4.Tag):
            logger.error(f"Cannot find CircuitPython board with name '{board_id}'!")
            logger.error(f"Confirm spelling from '{reference_url}'")
            raise SystemExit(ExitCode.Board_Lookup_Failure)
        row_cells = the_row.find_all("td")
        modules_cell = row_cells[-1]
        builtin_module_names = [entry.text for entry in modules_cell.find_all("span", class_="pre")]
        return reference_version, builtin_module_names

    def fetch_find_extract_standard_library_modules(reference_url: str) -> list[str]:
        page_request = urllib.request.Request(reference_url, headers={"User-agent": "Mozilla/5.0"})  # noqa: S310 -- URL is hardcoded to https
        live_html_bytes = urllib.request.urlopen(page_request).read()  # noqa: S310 -- URL is hardcoded to https
        live_html = live_html_bytes.decode("UTF-8")
        soup = bs4.BeautifulSoup(live_html, "html.parser")
        the_stdlib_section = soup.find(id="python-standard-libraries")
        if not isinstance(the_stdlib_section, bs4.Tag):
            logger.error(f"Cannot find 'python-standard-libraries' on {reference_url}")
            raise SystemExit(ExitCode.Board_Lookup_Failure)
        list_items = the_stdlib_section.select("li a span")
        stdlib_module_names = [entry.text for entry in list_items]
        return stdlib_module_names

    logger.info(f"Parsing builtin modules for '{board_id}'")
    standard_library_page = "https://docs.circuitpython.org/en/stable/docs/library/index.html"

    reference_version, builtin_module_names = fetch_find_extract_builtin_modules_for_board_id(
        Links.Board_Support_Matrix,
        board_id,
    )
    stdlib_module_names = fetch_find_extract_standard_library_modules(standard_library_page)

    full_contents = {
        "reference": reference_version,
        "urls": [Links.Board_Support_Matrix.value, standard_library_page],
        "standard_library": stdlib_module_names,
        board_id: builtin_module_names,
    }
    return str(toml.dumps(full_contents))
