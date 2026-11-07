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
from typing import NamedTuple, TypeVar

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
MatchedKeyType = TypeVar("MatchedKeyType", str, pathlib.Path)

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


def _print_runtime_description(device: SnsrDeviceSnapshot) -> None:
    """Print a description of this package's sensor_node runtime."""
    import_column_width = 30
    package_name_width = 44
    report_contents = textwrap.dedent(
        f"""\
        QT Py Datalogger Sensor Node
          Version                {device.snsr_runtime}  ({device.snsr_commit})
          Timestamp              {device.snsr_timestamp.strftime("%Y.%m.%d  %H:%M:%S")}
          Homepage               {Links.Homepage}
        """
    ).splitlines()
    report_contents.append("Apps")
    for app in device.apps:
        report_contents.append(f"  {app.name:<20}   {app.description}")
    report_contents.append("Dependencies")
    report_contents.append(f"  CircuitPython import {' ' * (import_column_width - 20)}  PyPI package name")
    report_contents.append(f"  {'=' * import_column_width}   {'-' * package_name_width}")
    for circuitpy_import in [m.name for m in device.required_modules]:
        package_name = "adafruit-circuitpython-{}".format(circuitpy_import.replace("adafruit_", "").replace("_", ""))
        report_contents.append(f"  {circuitpy_import:>{import_column_width}}   {package_name:<{package_name_width}}")
    for line in report_contents:
        logger.info(line)


def _print_snapshot_comparison(report: SnsrDeviceComparison) -> None:  # noqa: PLR0912, PLR0915 -- allow oversized function because it prints a report to the console
    """Print a summary that compares the specified sensor_node snapshots."""
    self_is_newer = report.runtime_is_newer
    self_is_older = not (report.runtime_versions_match or report.runtime_is_newer)
    self_version = report.runtime.snsr_runtime
    self_timestamp = report.runtime.snsr_timestamp
    device_version = report.device.snsr_runtime
    device_timestamp = report.device.snsr_timestamp
    newer_files = [file.path for file in report.file_changes.newer]
    # Ignore report.file_changes.tree1_only because these are reclassified as missing
    apps_in_both = sorted(set(report.apps_in_runtime).intersection(set(report.apps_in_device)))
    custom_apps = sorted(set(report.apps_in_device) - set(report.apps_in_runtime))
    missing_snsr_apps = report.missing_apps
    missing_snsr_files = report.missing_files
    missing_dependencies = report.missing_modules

    extra_color_chars = 9
    newer_mark = "(newer)"
    older_mark = "       "
    same_mark = "(same) "
    device_mark = older_mark if self_is_newer else newer_mark
    self_mark = newer_mark if self_is_newer else older_mark
    if self_version == device_version:
        if self_timestamp == device_timestamp:
            device_mark = same_mark
            self_mark = same_mark
        elif self_is_newer:
            self_mark = f" ({abs(report.runtime_age_days):.1f} days newer)"
        else:
            self_mark = f" ({abs(report.runtime_age_days):.1f} days older)"
    assumed_mark = "" if report.device.is_circuitpython_device else click.style("(assumed)", "yellow")
    extra_assumed_chars = 0 if report.device.is_circuitpython_device else extra_color_chars
    circuitpy_version = f"{report.device.circuitpython!s}  {assumed_mark}"
    board_id = f"{report.device.board_id}  {assumed_mark}"

    first_column_width = 40
    location = str(report.device.files.root)
    if len(location) > first_column_width:
        location = f"...{location[(-first_column_width + 3) :]}"
    report_header = textwrap.dedent(
        f"""
        Comparing sensor_node device with this package
          Trait         Device {device_mark}                              Self {self_mark}
          ===========   {"-" * first_column_width}    -------------------------
          Version       {device_version!s:<{first_column_width}}    {self_version!s}
          Timestamp     {device_timestamp.strftime("%Y.%m.%d  %H:%M:%S"):<{first_column_width}}    {self_timestamp.strftime("%Y.%m.%d  %H:%M:%S")}
          CircuitPy     {circuitpy_version:<{first_column_width + extra_assumed_chars}}    (PC host)
          Board ID      {board_id:<{first_column_width + extra_assumed_chars}}   (PC host)
          Location      {location:<{first_column_width}}    (builtin)
        """
    )
    header_lines = report_header.splitlines()
    for line in header_lines:
        logger.info(line)

    logger.info("  Apps")
    yellow_missing = click.style("MISSING", "yellow")
    for app in apps_in_both:
        logger.info(f"                {app:<{first_column_width}}    {app}")
    for app in missing_snsr_apps:
        logger.info(f"                {click.style(app, 'yellow'):<{first_column_width + extra_color_chars}}    {app}")
    for app in custom_apps:
        logger.info(f"                {app:<{first_column_width}}    (none)")

    logger.info("  Modules")
    for module in [m.name for m in report.required_modules_changes.same]:
        logger.info(f"                {module:<{first_column_width}}    {module}")
    for module in missing_dependencies:
        self_module_mark = module if module in [m.name for m in report.runtime.required_modules] else "(none)"
        logger.info(
            f"                {click.style(module, 'yellow'):<{first_column_width + extra_color_chars}}    {self_module_mark}"
        )
    for module in report.required_modules_changes.group2_only:
        if module.name in missing_dependencies:
            continue
        logger.info(f"                {module.name:<{first_column_width}}    (none)")

    logger.info("")
    if not report.device.is_sensor_node:
        logger.info("The device is not a QT Py Datalogger Sensor Node")
    elif self_is_older:
        logger.info("The sensor_node is newer than this package's version")
    elif self_is_newer:
        logger.info("The sensor_node is older than this package's version")
    elif newer_files:
        logger.info("The sensor_node matches this package's version")
        logger.info("Newer files in runtime")
        for newer_file in newer_files:
            logger.info(f"  * {newer_file!s}")
    else:
        logger.info(click.style("The sensor_node matches this package's version", "green"))

    equip_command = click.style("qtpy-datalogger equip", "green")
    if report.device.is_sensor_node:
        if (self_is_newer or newer_files) and not (missing_dependencies or missing_snsr_files or missing_snsr_apps):
            logger.info(f"Use '{equip_command}' to update the sensor_node to match")
        elif missing_dependencies or missing_snsr_files or missing_snsr_apps:
            warnings = []
            if missing_snsr_apps:
                warnings.append(click.style("The sensor_node is MISSING builtin apps", "yellow"))
                warnings.extend(f"  ! {yellow_missing} {missing}" for missing in missing_snsr_apps)
            if missing_dependencies:
                warnings.append(click.style("The sensor_node is MISSING CircuitPython modules", "yellow"))
                warnings.extend(f"  ! {yellow_missing} {missing}" for missing in missing_dependencies)
            if missing_snsr_files:
                warnings.append(click.style("The sensor_node is MISSING runtime files", "yellow"))
                warnings.extend(f"  ! {yellow_missing} {missing}" for missing in missing_snsr_files)
            for warning in warnings:
                logger.warning(warning)
            logger.warning("")
            logger.warning(f"Use '{equip_command}' to repair them")
    else:
        logger.info(f"Use '{equip_command}' to install the runtime onto it")


def _print_snapshot_report(comparison: SnsrDeviceComparison) -> None:  # noqa: PLR0912, PLR0915 -- allow oversized function because it prints a report to the console
    """Print a description of the detected device's platform details and sensor_node runtime."""
    device = comparison.device
    if device.is_circuitpython_device:
        board_id = device.board_id
        circuitpy_version = device.circuitpython
    else:
        board_id = _UNKNOWN_QTPY_BOARD_ID
        circuitpy_version = UNKNOWN_VERSION

    # Sensor node report
    if device.is_sensor_node:
        logger.info(f"Found a QT Py Datalogger Sensor Node at '{device.root}'")
    else:
        logger.info(f"The folder '{device.root}' is not a QT Py Datalogger Sensor Node")
    logger.info(f" * {'Runtime version':<30} {device.snsr_runtime!s}")
    logger.info(f" * {'Version timestamp':<30} {device.snsr_timestamp.strftime('%Y.%m.%d  %H:%M:%S')}")
    logger.info(f" * {'QT Py device':<30} {board_id}")
    logger.info(f" * {'CircuitPython version':<30} {circuitpy_version!s}")

    # Device support warnings
    if not device.is_circuitpython_device:
        logger.warning(click.style(f"The folder '{device.root}' is not a CircuitPython device", "yellow"))
        fallback_version = click.style(f"CircuitPython {_FALLBACK_CPY_VERSION!s}", "magenta")
        logger.warning(f" ! Assuming device uses {fallback_version}")
    if board_id not in _load_builtin_import_data():
        logger.warning(
            click.style(f"Missing information for builtin modules on CircuitPython device '{board_id}'", "yellow")
        )
        logger.warning(f" ! Visit '{Links.Board_Support_Matrix}' and find your BOARD NAME")
        logger.warning(
            " ! Then use 'qtpy-datalogger --list-builtin-modules \"BOARD NAME\" -' to get the builtin modules"
        )
        logger.warning(f" ! And create a new Issue with this information at '{Links.New_Bug}'")
        fallback_board = click.style(f"{_FALLBACK_QTPY_BOARD_ID!s}", "magenta")
        logger.warning(f" ! Assuming device is {fallback_board}")

    # Runtime warnings
    if device.is_sensor_node:
        missing_snsr_files = comparison.missing_files
        missing_snsr_apps = comparison.missing_apps
        missing_circuitpython_dependencies = comparison.missing_modules
        if any((missing_snsr_files, missing_snsr_apps, missing_circuitpython_dependencies)):
            logger.warning(click.style("Detected MISSING sensor_node runtime components", "yellow"))
        if missing_snsr_files:
            for file in missing_snsr_files:
                logger.warning(f" ! File:    {file!s}")
        if missing_snsr_apps:
            for app in missing_snsr_apps:
                logger.warning(f" ! App:     {app}")
        if missing_circuitpython_dependencies:
            for dependency in missing_circuitpython_dependencies:
                logger.warning(f" ! Module:  {dependency}")

    # Import warnings
    name_collisions = device.builtin_imports.intersection(device.snsr_imports)
    if name_collisions:
        logger.warning(click.style("Detected snsr runtime import name collisions!", "yellow"))
        for collision in name_collisions:
            logger.warning(f" ! {collision}")
        logger.warning(" ! These names are reserved by CircuitPython!")
    if device.unused_imports:
        logger.warning(click.style("Detected unused imports", "yellow"))
        for unused_import in device.unused_imports:
            logger.warning(ImportUsage.format_reference(unused_import))

    # Module report
    logger.debug("Required external CircuitPython modules")
    for name, version in device.required_modules:
        logger.debug(f" * {name:<30} {version}")
    if device.installed_modules:
        logger.debug("Detected installed external CircuitPython modules")
        for name, version in device.installed_modules:
            logger.debug(f" * {name:<30} {version}")
    else:
        logger.debug("No CircuitPython modules installed")

    # Module warnings
    unused_modules = {m.name for m in device.installed_modules} - {m.name for m in device.required_modules}
    if unused_modules:
        logger.warning(click.style("Detected unused CircuitPython modules", "yellow"))
        for module in unused_modules:
            logger.warning(f" ! {module}")

    # Apps report
    if device.files.relative_runtime_apps:
        logger.debug("Detected apps")
        for app in device.files.relative_runtime_apps:
            logger.debug(f" * {app.path.stem}")


def _make_equip_plan(behavior: Behavior, comparison: SnsrDeviceComparison, user_apps: AppImportUsage) -> EquipSnsrPlan:
    """Return a plan that updates the target sensor_node device to support the runtime and user_apps."""
    internal_imports = comparison.runtime.snsr_imports
    builtin_imports = comparison.runtime.builtin_imports
    installed_modules = [m.name for m in comparison.device.installed_modules]
    required_app_modules = set(user_apps.imports.base) - internal_imports - builtin_imports - set(installed_modules)
    app_freshness = _separate_apps_by_freshness(user_apps.files, comparison.device.files.relative_runtime_apps)

    # Delete paths are extra files in the device's runtime that are not in the package's runtime iow: comparison.file_changes.tree2_only
    # NB: There is no way for the runtime to delete **apps** with this approach. Instead, they must be removed by code because
    # we treat unknown apps as user apps.
    copy_runtime_files: set[pathlib.Path] = set()
    copy_user_apps: set[pathlib.Path] = set()
    install_modules: set[str] = set()
    delete_runtime_files: set[pathlib.Path] = set()
    if behavior == Behavior.Force:
        copy_runtime_files.update(entry.path for entry in comparison.runtime.files.relative_tree)
        copy_user_apps.update(user_apps.files)
        install_modules.update(m.name for m in comparison.runtime.required_modules)
        install_modules.update(m.name for m in comparison.device.required_modules)
        install_modules.update(user_apps.imports.base)
    else:
        # Create a baseline profile that repairs missing files, adds new files, and updates newer files
        copy_runtime_files.update(entry.path for entry in comparison.file_changes.tree1_only)
        copy_runtime_files.update(entry.path for entry in comparison.file_changes.newer)
        copy_runtime_files.update(comparison.missing_files)
        copy_user_apps.update(app.path for app in app_freshness.tree1_only)
        copy_user_apps.update(app.path for app in app_freshness.newer)
        install_modules.update(comparison.missing_modules)
        install_modules.update(required_app_modules)

    if behavior == Behavior.Force:
        runtime_goal = EquipSnsrPlan.Goal.Force
    elif comparison.device.is_sensor_node:
        if comparison.runtime.snsr_runtime < comparison.device.snsr_runtime:
            runtime_goal = EquipSnsrPlan.Goal.SkipVersion
        elif comparison.runtime.snsr_runtime > comparison.device.snsr_runtime:
            runtime_goal = EquipSnsrPlan.Goal.UpgradeVersion
            # Refresh the runtime files for new versions
            copy_runtime_files.update(entry.path for entry in comparison.runtime.files.relative_tree)
        elif comparison.runtime.snsr_timestamp > comparison.device.snsr_timestamp:
            runtime_goal = EquipSnsrPlan.Goal.UpgradeSnapshot
        elif comparison.missing_files or comparison.missing_apps or comparison.missing_modules:
            runtime_goal = EquipSnsrPlan.Goal.Repair
        elif copy_runtime_files or copy_user_apps or install_modules:
            runtime_goal = EquipSnsrPlan.Goal.UpgradeFiles
        else:
            runtime_goal = EquipSnsrPlan.Goal.SkipFiles
    else:
        runtime_goal = EquipSnsrPlan.Goal.Install

    return EquipSnsrPlan(
        goal=runtime_goal,
        runtime_root=comparison.runtime.root,
        old_runtime_version=comparison.device.snsr_runtime,
        new_runtime_version=comparison.runtime.snsr_runtime,
        runtime_age_days=comparison.runtime_age_days,
        device_root=comparison.device.root,
        device_board_id=comparison.device.board_id,
        device_circuitpython=comparison.device.circuitpython,
        copy_files=tuple(sorted(copy_runtime_files)),
        delete_files=tuple(sorted(delete_runtime_files)),
        copy_apps=tuple(sorted(copy_user_apps)),
        modules_to_install=tuple(sorted(install_modules)),
    )


def _execute_equip_plan(plan: EquipSnsrPlan) -> int:  # noqa: PLR0912, PLR0915 -- allow oversized function because it executes the procedure that changes the contents of a device
    """Use the specified plan to equip the sensor_node."""
    if plan.is_empty:
        return ExitCode.Success

    if plan.goal == EquipSnsrPlan.Goal.Install:
        logger.info("Initializing new QT Py Datalogger Sensor Node")
        logger.info(f"  Location:  {plan.device_root!s}")
        logger.info(f"  Version :  {plan.new_runtime_version!s}")
    elif plan.goal == EquipSnsrPlan.Goal.Repair:
        logger.info("Repairing missing sensor_node runtime components")
    elif plan.goal == EquipSnsrPlan.Goal.UpgradeVersion:
        logger.info("Upgrading version")
        logger.info(f"  From  {plan.old_runtime_version!s}  to  {plan.new_runtime_version!s}")
    elif plan.goal == EquipSnsrPlan.Goal.UpgradeFiles:
        logger.info("Applying updates")
    elif plan.goal == EquipSnsrPlan.Goal.UpgradeSnapshot:
        logger.info("Upgrading snapshot")
        logger.info(
            f"  Both are version  {plan.new_runtime_version}  but the device is  {abs(plan.runtime_age_days):.1f}  days older"
        )
    elif plan.goal == EquipSnsrPlan.Goal.Force:
        logger.info("Forcing installation")
    else:
        raise ValueError(plan.goal)

    if plan.copy_files or plan.modules_to_install:
        logger.info("  Installing sensor_node runtime components")

    if plan.copy_files:
        for file in plan.copy_files:
            source = plan.runtime_root.joinpath(file)
            if source.is_dir():
                continue
            destination = plan.device_root.joinpath(file)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if plan.goal == EquipSnsrPlan.Goal.UpgradeFiles:
                logger.info(f"  * Newer:  {file!s}")
            logger.debug(f"- {file!s:<30}  :::  {source!s}  -->  {destination!s}")
            shutil.copy2(src=source, dst=destination)

    if plan.copy_files or plan.goal == EquipSnsrPlan.Goal.UpgradeSnapshot:
        notice_file = plan.device_root.joinpath(SnsrPath.notice_toml)
        notice_contents = _create_notice_file_contents(allow_dev_version=True)
        notice_file.write_text(notice_contents)
        logger.debug(f"Wrote {notice_file!s}")

    if plan.copy_apps:
        logger.info("Installing apps")
        for user_app in plan.copy_apps:
            destination = plan.device_root.joinpath(SnsrPath.apps, user_app.name)
            logger.info(f"  * {user_app.stem}")
            logger.debug(f"- {user_app.name:<15}  :::  {user_app!s}  -->  {destination!s}")
            shutil.copy2(src=user_app, dst=destination)

    return_code = ExitCode.Success
    if plan.modules_to_install:
        logger.info("Installing external dependencies with circup")
        return_code = CircupTool.equip_modules(
            plan.device_root,
            plan.device_board_id,
            plan.device_circuitpython,
            plan.modules_to_install,
        )
        logger.info("")
    else:
        logger.info("Skipping circup: external dependencies already installed")

    if return_code == ExitCode.Success:
        plan.device_root.joinpath(SnsrPath.code_py).touch()  # Restart the node
        logger.info(click.style("Installation complete", "green"))
    else:
        logger.error(f"circup exited with code '{click.style(return_code, 'red')}'")
    return return_code


def _validate_user_apps(candidates: Sequence[pathlib.Path], runtime_snapshot: SnsrDeviceSnapshot) -> AppImportUsage:
    """Inspect the specified candidates and return the valid apps and their imports."""
    user_apps = []
    for app in candidates:
        if app.stem in runtime_snapshot.files.reserved_app_names:
            logger.warning(f"Skipping '{app}': cannot overwrite builtin app")
            continue
        if app.suffix not in _ALLOWED_USER_APP_FILE_TYPES:
            logger.warning(f"Skipping '{app}': not an allowed app file")
            continue
        user_apps.append(app)
    import_usage = AppImportUsage.from_files(user_apps)
    if import_usage.imports.unused:
        logger.warning(click.style("Detected app with unused imports", "yellow"))
        for unused_import in import_usage.imports.unused:
            logger.warning(ImportUsage.format_reference(unused_import))
    return import_usage


def _compare_modules(
    runtime_modules: Sequence[ModuleWithVersion],
    device_modules: Sequence[ModuleWithVersion],
) -> ModuleComparison:
    """Compare the collections of CircuitPython modules and return a ModuleComparison."""
    runtime_module_map = dict(runtime_modules)
    device_module_map = dict(device_modules)
    runtime_module_names = set(runtime_module_map.keys())
    device_module_names = set(device_module_map.keys())
    matching_modules_names = runtime_module_names.intersection(device_module_names)
    runtime_only_modules = {
        ModuleWithVersion(name, runtime_module_map[name]) for name in runtime_module_names - device_module_names
    }
    device_only_modules = {
        ModuleWithVersion(name, device_module_map[name]) for name in device_module_names - runtime_module_names
    }
    newer_runtime_modules = set()
    older_runtime_modules = set()
    matching_modules = set()
    for name in matching_modules_names:
        matching_entry = ModuleWithVersion(name, runtime_module_map[name])
        if runtime_module_map[name] > device_module_map[name]:
            newer_runtime_modules.add(matching_entry)
        elif runtime_module_map[name] < device_module_map[name]:
            older_runtime_modules.add(matching_entry)
        else:
            matching_modules.add(matching_entry)
    return ModuleComparison(
        same=tuple(sorted(matching_modules)),
        newer=tuple(sorted(newer_runtime_modules)),
        older=tuple(sorted(older_runtime_modules)),
        group1_only=tuple(sorted(runtime_only_modules)),
        group2_only=tuple(sorted(device_only_modules)),
    )


def _separate_apps_by_freshness(
    user_apps: Sequence[pathlib.Path],
    device_apps: Sequence[FileWithAge],
) -> FileTreeComparison:
    """Compare the user_apps with those in the device and return a FileComparisonReport."""
    device_app_age_map = dict(device_apps)
    device_app_file_map = {file.name: file for file in device_app_age_map}
    user_app_age_map = dict(FileWithAge.from_path(app) for app in user_apps)
    user_app_file_map = {file.name: file for file in user_app_age_map}
    return _build_file_comparison(
        candidate_file_map=user_app_file_map,
        candidate_age_map=user_app_age_map,
        baseline_file_map=device_app_file_map,
        baseline_age_map=device_app_age_map,
    )


def _compare_snsr_file_trees(runtime: SnsrFileTree, device: SnsrFileTree) -> FileTreeComparison:
    """Compare the SnsrFileTrees and return a FileTreeComparison."""
    relative_self_age_map = dict(
        entry for entry in runtime.relative_tree if runtime.root.joinpath(entry.path).is_file()
    )
    relative_self_file_map = {entry: entry for entry in relative_self_age_map}
    relative_other_age_map = dict(entry for entry in device.relative_tree if device.root.joinpath(entry.path).is_file())
    relative_other_file_map = {entry: entry for entry in relative_other_age_map}
    return _build_file_comparison(
        candidate_file_map=relative_self_file_map,
        candidate_age_map=relative_self_age_map,
        baseline_file_map=relative_other_file_map,
        baseline_age_map=relative_other_age_map,
    )


def _build_file_comparison(
    candidate_file_map: dict[MatchedKeyType, pathlib.Path],
    candidate_age_map: dict[pathlib.Path, dt.datetime],
    baseline_file_map: dict[MatchedKeyType, pathlib.Path],
    baseline_age_map: dict[pathlib.Path, dt.datetime],
) -> FileTreeComparison:
    """
    Use the candidate and baseline file maps to group files by their ages.

    The file_map dictionaries must use the same type for their keys because this
    function compares them against each other to detect shared and unique entries.

    Further, this function uses the dictionary values stored by the file_map parameters
    as the keys for the age_map dictionaries.

    """
    equal_files = []
    updated_files = []
    older_files = []
    candidate_only_files = []
    other_only_files = []

    shared_file_keys = set(candidate_file_map.keys()).intersection(set(baseline_file_map.keys()))
    for file_key in shared_file_keys:
        candidate_file = candidate_file_map[file_key]
        candidate_age = candidate_age_map[candidate_file]
        baseline_file = baseline_file_map[file_key]
        baseline_age = baseline_age_map[baseline_file]
        sorted_candidate_file = FileWithAge(candidate_file, candidate_age)
        if candidate_age > baseline_age:
            updated_files.append(sorted_candidate_file)
            continue
        if candidate_age < baseline_age:
            older_files.append(sorted_candidate_file)
            continue
        equal_files.append(sorted_candidate_file)

    candidate_only_file_keys = candidate_file_map.keys() - baseline_file_map.keys()
    for file_key in candidate_only_file_keys:
        file = candidate_file_map[file_key]
        age = candidate_age_map[file]
        candidate_only_files.append(FileWithAge(file, age))

    baseline_only_file_keys = baseline_file_map.keys() - candidate_file_map.keys()
    for file_key in baseline_only_file_keys:
        file = baseline_file_map[file_key]
        age = baseline_age_map[file]
        other_only_files.append(FileWithAge(file, age))

    comparison_report = FileTreeComparison(
        same=tuple(sorted(equal_files)),
        newer=tuple(sorted(updated_files)),
        older=tuple(sorted(older_files)),
        tree1_only=tuple(sorted(candidate_only_files)),
        tree2_only=tuple(sorted(other_only_files)),
    )
    return comparison_report


def _collect_relative_folder_details(main_folder: pathlib.Path) -> Sequence[FileWithAge]:
    """Return a relative list of all the folders and files under the specified folder."""

    def recursive_folder_scan(folder: pathlib.Path, root: pathlib.Path) -> Sequence[FileWithAge]:
        """Recursively collect the folder and files and return their relative paths from the root."""
        folder_details = [FileWithAge.make_relative(folder, root)]
        folder_listing = list(folder.iterdir())
        subfolders = [entry for entry in folder_listing if entry.is_dir()]
        subfiles = [
            entry
            for entry in folder_listing
            if entry.is_file() and all(pattern not in str(entry) for pattern in _EQUIP_IGNORE_PATTERNS)
        ]
        for subfolder in subfolders:
            subfolder_details = recursive_folder_scan(subfolder, root)
            folder_details.extend(subfolder_details)
        for entry in subfiles:
            folder_details.append(FileWithAge.make_relative(entry, root))
        return tuple(folder_details)

    logger.debug(f"Collecting files from '{main_folder}'")
    details = recursive_folder_scan(main_folder, root=main_folder)
    return tuple(sorted(details))


@functools.cache
def _load_builtin_import_data() -> dict[str, Sequence[str]]:
    """Load the builtin CircuitPython module data."""
    this_file = pathlib.Path(__file__)
    builtin_circuitpython_imports_file = this_file.with_name("builtin_circuitpython_modules.toml")
    builtin_circuitpython_imports = toml.load(builtin_circuitpython_imports_file)
    return builtin_circuitpython_imports  # ty: ignore[unsound-return-statement] -- runtime type checking doesn't help in this case for some reason


def _create_notice_file_contents(allow_dev_version: bool) -> str:
    """Format the notice.toml file for the package."""
    snsr_notice = SnsrNotice.get_package_notice_info(allow_dev_version)
    file_contents = str(toml.dumps(snsr_notice._asdict()))
    return file_contents


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
