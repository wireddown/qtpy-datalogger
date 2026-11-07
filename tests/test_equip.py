"""Acceptance tests for the equip module."""

import contextlib
import logging
import pathlib
import re
import shutil
import tempfile
from collections.abc import Generator

import click
import pytest
import toml
from test_discovery import one_mqtt_qtpy_device

from qtpy_datalogger import discovery, equip
from qtpy_datalogger.datatypes import ExitCode, SnsrNotice, SnsrPath


@pytest.fixture(scope="module")
def reference_snsr() -> Generator[pathlib.Path, None, None]:
    """Install the package's sensor node runtime into a temporary folder."""
    with tempfile.TemporaryDirectory(prefix="qtpy_", suffix="_snsr_clone") as folder_string:
        snsr_root = pathlib.Path(folder_string)
        with contextlib.suppress(SystemExit):
            equip.handle_equip(
                behavior=equip.Behavior.Upgrade,
                with_apps=(),
                root=snsr_root,
                secrets=equip.SecretsBehavior.Noop.as_full_name(),
            )
        yield snsr_root


def clone_test_device_into_folder(reference_device: pathlib.Path, folder: pathlib.Path) -> None:
    """
    Make folder into a sensor_node.

    Use the 'reference_snsr' fixture in your tests as the reference_device.
    """
    shutil.copytree(src=reference_device, dst=folder, dirs_exist_ok=True)


def prepare_uninitialized_device(folder: pathlib.Path) -> pathlib.Path:
    """Create and return a folder that represents a new QT Py device without any runtime installed."""
    node_subfolder = folder.joinpath("test_node")
    node_subfolder.mkdir()
    return node_subfolder


def prepare_initialized_device_with_options(
    reference_device: pathlib.Path,
    folder: pathlib.Path,
    version: str | None = None,
    user_app_contents: str | None = None,
) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    """
    Make folder into a sensor_node with an optional version or existing user app contents.

    Returns a tuple of paths
      - test_node_subfolder -- the root of the initialized device
      - unrelated_app_path  -- an extra unrelated app used as an incorrect deletion detector
      - user_app_path       -- a preinstalled user app with the specified contents

    """
    test_node_subfolder = prepare_uninitialized_device(folder)
    clone_test_device_into_folder(reference_device, test_node_subfolder)

    if not isinstance(user_app_contents, str):
        user_app_contents = "# See prepare_initialized_device_with_options()"
    user_app_path = create_empty_file_in_folder("existing_app.py", test_node_subfolder.joinpath(SnsrPath.apps))
    user_app_path.write_text(user_app_contents)

    unrelated_app_path = create_empty_file_in_folder("unrelated_app.py", test_node_subfolder.joinpath(SnsrPath.apps))

    if isinstance(version, str):
        device_toml = get_device_notice(test_node_subfolder)
        new_version_toml = SnsrNotice(
            comment=device_toml.comment,
            version=version,
            commit=device_toml.commit,
            timestamp=device_toml.timestamp,
        )
        set_device_notice(new_version_toml, test_node_subfolder)

    return test_node_subfolder, unrelated_app_path, user_app_path


def prepare_user_app(folder: pathlib.Path, user_app_name: str, user_app_contents: str) -> pathlib.Path:
    """Create an app in the folder with the specified user_app_name and user_app_contents and return its path."""
    user_app_folder = folder.joinpath("test_app")
    user_app_path = create_empty_file_in_folder(user_app_name, user_app_folder)
    user_app_path.write_text(user_app_contents)
    return user_app_path


def read_and_replace_runtime_file(snsr_file: pathlib.Path, downversion_contents: str) -> str:
    """Return the original first line from the snsr_file and replace the whole file with downversion_contents."""
    with snsr_file.open("r") as file:
        original_first_line = file.readline().strip()
    snsr_file.write_text(downversion_contents)
    return original_first_line


def assert_safe_exit(excinfo: pytest.ExceptionInfo) -> None:  # ty: ignore[missing-type-argument] -- this function accepts all exception types
    """Assert that the Exception information indicates a safe execution exit."""
    assert_exit_code(excinfo, ExitCode.Success)


def assert_exit_code(excinfo: pytest.ExceptionInfo, expected_code: int) -> None:  # ty: ignore[missing-type-argument] -- this function accepts all exception types
    """Assert that the Exception information indicates a normal exit with the expected_code."""
    exception = excinfo.value
    assert type(exception) is SystemExit
    assert exception.code == expected_code


def assert_device_matches_self(  # noqa: PLR0913, PLR0917 -- allow oversized functions for assert helpers
    reference_folder: pathlib.Path,
    device_path: pathlib.Path,
    extra_expected_apps: list[pathlib.Path] | None = None,
    expected_version: str | None = None,
    extra_expected_imports: list[str] | None = None,
    extra_expected_modules: list[str] | None = None,
) -> None:
    """
    Assert that the version and dependency information matches the reference.

    Optionally use the 'reference_snsr' fixture in your tests as the reference_folder.
    """
    reference = equip.SnsrDeviceSnapshot.from_folder(reference_folder)
    device = equip.SnsrDeviceSnapshot.from_folder(device_path)

    extra_expected_apps = extra_expected_apps or []
    expected_version = expected_version or str(reference.snsr_runtime)
    extra_expected_imports = extra_expected_imports or []
    extra_expected_modules = extra_expected_modules or []

    assert str(device.snsr_runtime) == expected_version
    assert device.board_id == reference.board_id
    assert device.circuitpython == reference.circuitpython

    assert set(device.external_imports) == {*reference.external_imports, *extra_expected_imports}
    assert {m.name for m in device.installed_modules} == {
        *[m.name for m in reference.installed_modules],
        *extra_expected_modules,
    }
    assert {m.name for m in device.required_modules} == {
        *[m.name for m in reference.required_modules],
        *extra_expected_modules,
    }
    device.files.root.joinpath("lib").exists()

    # Skip comparing the full file lists

    for app in extra_expected_apps:
        assert device_path.joinpath(SnsrPath.apps, app.name).exists()


def assert_new_installation_succeeded(captured_log: pytest.LogCaptureFixture) -> None:
    """Assert that the captured_log indicates a successful installation of a new uninitialized sensor_node."""
    assert "is not a QT Py Datalogger Sensor Node" in captured_log.text
    assert "Initializing new QT Py Datalogger Sensor Node" in captured_log.text
    assert "Installing sensor_node runtime" in captured_log.text
    assert "Installing external dependencies with circup" in captured_log.text
    assert "Installation complete" in captured_log.text
    assert "Detected MISSING sensor_node runtime components" not in captured_log.text


def assert_compare_snsr_node_succeeded(captured_log: pytest.LogCaptureFixture) -> None:
    """Assert that the capture_log indicates a successful comparison of a sensor_node."""
    assert "Comparing sensor_node device with this package" in captured_log.text
    assert re.search(r"echo\s+echo", captured_log.text)
    assert re.search(r"qtpycmd\s+qtpycmd", captured_log.text)
    assert re.search(r"adafruit_minimqtt\s+adafruit_minimqtt", captured_log.text)


def assert_equip_operation_succeeded(  # noqa: PLR0912, PLR0913, PLR0915, PLR0917 -- allow oversized functions for assert helpers
    captured_log: pytest.LogCaptureFixture,
    expect_new_version: bool = False,
    expect_repair: bool = False,
    expected_new_apps: list[pathlib.Path] | None = None,
    expected_new_files: list[pathlib.Path] | None = None,
    expect_circup: bool = False,
    expect_forced: bool = False,
) -> None:
    """Assert that the capture_log indicates a successful equip operation on an initialized sensor_node."""
    expected_new_apps = expected_new_apps or []
    expect_new_apps = len(expected_new_apps) > 0
    expected_new_files = expected_new_files or []
    expect_install_any = any(
        [expect_new_version, expect_repair, expect_new_apps, len(expected_new_files) > 0, expect_circup, expect_forced]
    )
    expect_install_snsr_files = any([expect_new_version, expect_repair, len(expected_new_files) > 0, expect_forced])
    expect_circup = any([expect_circup, expect_forced])

    if not expect_install_any:
        assert "Skipping installation: not an upgrade" in captured_log.text
        return

    if expect_install_snsr_files:
        assert "Installing sensor_node runtime" in captured_log.text
        assert "All runtime files and CircuitPython modules up to date with the host" not in captured_log.text

    if expect_new_apps:
        assert "Installing apps" in captured_log.text
        assert "All runtime files and CircuitPython modules up to date with the host" not in captured_log.text

    if not (expect_install_snsr_files or expect_new_apps):
        assert "Installing sensor_node runtime" not in captured_log.text
        assert "Installing apps" not in captured_log.text
        assert "All runtime files and CircuitPython modules up to date with the host" in captured_log.text

    assert "Upgrading snapshot" not in captured_log.text
    if expect_new_version:
        assert "Upgrading version" in captured_log.text
        assert "Repairing missing sensor_node runtime components" not in captured_log.text
        assert "Forcing installation" not in captured_log.text
    elif expect_repair:
        assert "Upgrading version" not in captured_log.text
        assert "Repairing missing sensor_node runtime components" in captured_log.text
        assert "Forcing installation" not in captured_log.text
    elif expect_forced:
        assert "Upgrading version" not in captured_log.text
        assert "Repairing missing sensor_node runtime components" not in captured_log.text
        assert "Forcing installation" in captured_log.text
    else:
        assert "Upgrading version" not in captured_log.text
        assert "Repairing missing sensor_node runtime components" not in captured_log.text
        assert "Forcing installation" not in captured_log.text

    if expected_new_apps:
        assert "Installing apps" in captured_log.text
    else:
        assert "Installing apps" not in captured_log.text
    for expected_app in expected_new_apps:
        assert f" * {expected_app.stem}" in captured_log.text

    for expected_file in expected_new_files:
        assert re.search(f"Newer: .*{expected_file.name}", captured_log.text)
    if not expected_new_files:
        assert not re.search(r"Newer:  .*\.py", captured_log.text)

    if expect_circup:
        assert "Installing external dependencies with circup" in captured_log.text
        assert "Skipping circup: external dependencies already installed" not in captured_log.text
    else:
        assert "Installing external dependencies with circup" not in captured_log.text
        assert "Skipping circup: external dependencies already installed" in captured_log.text

    assert "Installation complete" in captured_log.text


def assert_user_app_matches_contents(test_device_folder: pathlib.Path, user_app_name: str, contents: str) -> None:
    """Assert that sensor_node app matches the contents."""
    assert test_device_folder.joinpath(SnsrPath.apps, user_app_name).exists()
    assert test_device_folder.joinpath(SnsrPath.apps, user_app_name).read_text() == contents


def get_device_notice(device_path: pathlib.Path) -> SnsrNotice:
    """Get the SnsrNotice information from the sensor_node at the specified path."""
    device_notice = device_path.joinpath(SnsrPath.notice_toml)
    device_toml = SnsrNotice(**toml.load(device_notice))
    return device_toml


def set_device_notice(notice: SnsrNotice, device_path: pathlib.Path) -> None:
    """Set the SnsrNotice information on the sensor_node at the specified path."""
    device_notice = device_path.joinpath(SnsrPath.notice_toml)
    notice_text = toml.dumps(notice._asdict())
    device_notice.write_text(notice_text)


def create_empty_file_in_folder(file_name: str, folder: pathlib.Path) -> pathlib.Path:
    """Create a file named 'file_name' in folder and return its path."""
    folder.mkdir(exist_ok=True)
    file_path = folder.joinpath(file_name)
    file_path.touch()
    return file_path


def skip_secrets(text: str, default: str, hide_input: bool, type: type, show_default: bool) -> str:  # noqa: A002 -- we must hide 'type' to match the click API
    """Return the user input that skips setting a secret."""
    return ""


def merge_secrets(text: str, default: str, hide_input: bool, type: type, show_default: bool) -> str:  # noqa: A002 -- we must hide 'type' to match the click API
    """Return user input that only sets a subset of secrets."""
    if "QTPY_BROKER_IP_ADDRESS" in text:
        return "1.2.3.4"
    if "QTPY_NODE_NAME" in text:
        return "node_name"
    return ""


def test_describe(tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture) -> None:
    """Does it exit successfully after describing?"""
    with caplog.at_level(logging.INFO), pytest.raises(SystemExit) as excinfo:
        equip.handle_equip(
            behavior=equip.Behavior.Describe,
            with_apps=(),
            root=tmp_path,
            secrets=equip.SecretsBehavior.Noop.as_full_name(),
        )

    assert_safe_exit(excinfo)
    assert "QT Py Datalogger Sensor Node" in caplog.text
    assert "echo" in caplog.text
    assert "qtpycmd" in caplog.text
    assert "__init__" not in caplog.text
    assert "adafruit_ticks" in caplog.text


def test_snsr_runtime_fixture(reference_snsr: pathlib.Path) -> None:
    """Does the fixture successfully create the cloneable sensor node runtime?"""
    assert reference_snsr.is_dir()
    assert reference_snsr.joinpath("lib").exists()


def test_compare(reference_snsr: pathlib.Path, tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture) -> None:
    """Does it exit successfully after comparing?"""
    clone_test_device_into_folder(reference_snsr, tmp_path)

    with caplog.at_level(logging.INFO), pytest.raises(SystemExit) as excinfo:
        equip.handle_equip(
            behavior=equip.Behavior.Compare,
            with_apps=(),
            root=tmp_path,
            secrets=equip.SecretsBehavior.Noop.as_full_name(),
        )

    assert_safe_exit(excinfo)
    assert_compare_snsr_node_succeeded(caplog)
    assert "The sensor_node matches this package's version" in caplog.text


def test_compare_detects_missing_snsr_file(
    reference_snsr: pathlib.Path,
    tmp_path: pathlib.Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Does it report that a snsr runtime file is missing when comparing?"""
    clone_test_device_into_folder(reference_snsr, tmp_path)
    snsr_file_path = tmp_path.joinpath(SnsrPath.root, "core.py")
    snsr_file_path.unlink()

    with caplog.at_level(logging.INFO), pytest.raises(SystemExit) as excinfo:
        equip.handle_equip(
            behavior=equip.Behavior.Compare,
            with_apps=(),
            root=tmp_path,
            secrets=equip.SecretsBehavior.Noop.as_full_name(),
        )

    assert_safe_exit(excinfo)
    assert_compare_snsr_node_succeeded(caplog)
    assert "The sensor_node is MISSING runtime files" in caplog.text
    assert f"  ! MISSING {snsr_file_path.relative_to(tmp_path)!s}" in caplog.text


def test_compare_detects_missing_builtin_app(
    reference_snsr: pathlib.Path,
    tmp_path: pathlib.Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Does it report that a builtin app is missing when comparing?"""
    clone_test_device_into_folder(reference_snsr, tmp_path)
    qtpycmd_app_path = tmp_path.joinpath(SnsrPath.apps, "qtpycmd.py")
    qtpycmd_app_path.unlink()

    with caplog.at_level(logging.INFO), pytest.raises(SystemExit) as excinfo:
        equip.handle_equip(
            behavior=equip.Behavior.Compare,
            with_apps=(),
            root=tmp_path,
            secrets=equip.SecretsBehavior.Noop.as_full_name(),
        )

    assert_safe_exit(excinfo)
    assert_compare_snsr_node_succeeded(caplog)
    assert "The sensor_node is MISSING builtin apps" in caplog.text
    assert f"  ! MISSING {qtpycmd_app_path.stem}" in caplog.text


def test_compare_detects_missing_circuitpython_module(
    reference_snsr: pathlib.Path,
    tmp_path: pathlib.Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Does it report that a required CircuitPython module is missing when comparing?"""
    clone_test_device_into_folder(reference_snsr, tmp_path)
    adafruit_ticks_path = tmp_path.joinpath("lib", "adafruit_ticks.mpy")
    adafruit_ticks_path.unlink()

    with caplog.at_level(logging.INFO), pytest.raises(SystemExit) as excinfo:
        equip.handle_equip(
            behavior=equip.Behavior.Compare,
            with_apps=(),
            root=tmp_path,
            secrets=equip.SecretsBehavior.Noop.as_full_name(),
        )

    assert_safe_exit(excinfo)
    assert_compare_snsr_node_succeeded(caplog)
    assert "The sensor_node is MISSING CircuitPython modules" in caplog.text
    assert f"  ! MISSING {adafruit_ticks_path.stem}" in caplog.text


def test_compare_detects_user_app(
    reference_snsr: pathlib.Path,
    tmp_path: pathlib.Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Does it list a pre-installed user app when comparing without user apps?"""
    test_device_folder, unrelated_app, existing_app = prepare_initialized_device_with_options(reference_snsr, tmp_path)

    with caplog.at_level(logging.INFO), pytest.raises(SystemExit) as excinfo:
        equip.handle_equip(
            behavior=equip.Behavior.Compare,
            with_apps=(),
            root=test_device_folder,
            secrets=equip.SecretsBehavior.Noop.as_full_name(),
        )

    assert_safe_exit(excinfo)
    assert_compare_snsr_node_succeeded(caplog)
    assert_device_matches_self(reference_snsr, test_device_folder, extra_expected_apps=[unrelated_app, existing_app])
    assert re.search(f"{existing_app.stem}\\s+\\(none\\)", caplog.text)
    assert re.search(f"{unrelated_app.stem}\\s+\\(none\\)", caplog.text)
    assert "The sensor_node matches this package's version" in caplog.text


def test_cannot_install_with_mqtt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Does it exit with error when the device only has MQTT transport?"""
    monkeypatch.setattr(discovery, "discover_qtpy_devices", one_mqtt_qtpy_device)

    with pytest.raises(SystemExit) as excinfo:
        equip.handle_equip(
            behavior=equip.Behavior.Upgrade, root=None, secrets=equip.SecretsBehavior.Noop.as_full_name()
        )

    exception = excinfo.value
    exception_type = type(exception)
    assert exception_type is SystemExit
    assert exception.code == ExitCode.Equip_Without_USB_Failure


def test_install_new(tmp_path: pathlib.Path) -> None:
    """Does it install when the device isn't a sensor node?"""
    equip.handle_equip(
        behavior=equip.Behavior.Upgrade, root=tmp_path, secrets=equip.SecretsBehavior.Noop.as_full_name()
    )

    comparison_results = get_bundle_comparison(tmp_path)
    assert_device_matches_self(comparison_results)
    assert tmp_path.joinpath("lib").exists()


def test_upgrade(tmp_path: pathlib.Path) -> None:
    """Does it upgrade when the device is an older sensor node?"""
    create_test_device_folder(tmp_path)
    device_toml = get_device_notice(tmp_path)
    downversion_toml = equip.SnsrNotice(
        comment=device_toml.comment,
        version="0.0.1",
        commit=device_toml.commit,
        timestamp=device_toml.timestamp,
    )
    set_device_notice(downversion_toml, tmp_path)

    equip.handle_equip(
        behavior=equip.Behavior.Upgrade, root=tmp_path, secrets=equip.SecretsBehavior.Noop.as_full_name()
    )

    comparison_results = get_bundle_comparison(tmp_path)
    assert_device_matches_self(comparison_results)
    assert tmp_path.joinpath("lib").exists()


def test_skip_upgrade(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Does it skip upgrading when the device is a newer version?"""

    def throw_on_call(behavior: equip.Behavior, comparison_information: dict[str, equip.SnsrNodeBundle]) -> None:
        message = "qtpy_datalogger incorrectly tried to upgrade"
        raise RuntimeError(message)

    monkeypatch.setattr(equip, "_equip_snsr_node", throw_on_call)
    create_test_device_folder(tmp_path)
    device_toml = get_device_notice(tmp_path)
    upversion_toml = equip.SnsrNotice(
        comment=device_toml.comment,
        version="100.0.0",
        commit=device_toml.commit,
        timestamp=device_toml.timestamp,
    )
    set_device_notice(upversion_toml, tmp_path)

    equip.handle_equip(
        behavior=equip.Behavior.Upgrade, root=tmp_path, secrets=equip.SecretsBehavior.Noop.as_full_name()
    )
    assert not tmp_path.joinpath("lib").exists()


def test_force_install(tmp_path: pathlib.Path) -> None:
    """Does it install when forced?"""
    create_test_device_folder(tmp_path)
    device_toml = get_device_notice(tmp_path)
    upversion_toml = equip.SnsrNotice(
        comment=device_toml.comment,
        version="100.0.0",
        commit=device_toml.commit,
        timestamp=device_toml.timestamp,
    )
    set_device_notice(upversion_toml, tmp_path)

    equip.handle_equip(behavior=equip.Behavior.Force, root=tmp_path, secrets=equip.SecretsBehavior.Noop.as_full_name())

    comparison_results = get_bundle_comparison(tmp_path)
    assert_device_matches_self(comparison_results)
    assert tmp_path.joinpath("lib").exists()


def test_only_newer_files(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Does it skip circup packages for Behavior.OnlyNewerFiles?"""
    create_test_device_folder(tmp_path)
    newer_files: list[pathlib.Path] = []

    def override_file_freshness(
        tree1: list[pathlib.Path],
        tree2: list[pathlib.Path],
        ignore_list: set[str],
        newer_files: list[pathlib.Path] = newer_files,
    ) -> dict[pathlib.Path, str]:
        """Override equip._compare_file_trees() to make the bundle newer than than device."""
        set1 = {path.relative_to(tree1[0]) for path in tree1}
        set2 = {path.relative_to(tree2[0]) for path in tree2}
        shared_in_both = sorted(f for f in set1 & set2 if tree1[0].joinpath(f).is_file())
        equal_file = shared_in_both[0]
        older_file = shared_in_both[1]
        newer_file = shared_in_both[2]
        novel_file = tree1[0] / "PYTEST_NEWFILE.py"
        novel_file.touch()
        tree1_file_ages = {
            equal_file: "equal",
            older_file: "older",
            newer_file: "newer",
            novel_file: "newer",
        }
        newer_files.append(newer_file)
        newer_files.append(novel_file)
        return tree1_file_ages

    monkeypatch.setattr(equip, "_compare_file_trees", override_file_freshness)

    with caplog.at_level(logging.INFO):
        equip.handle_equip(
            behavior=equip.Behavior.NewerFilesOnly, root=tmp_path, secrets=equip.SecretsBehavior.Noop.as_full_name()
        )

    comparison_results = get_bundle_comparison(tmp_path)
    assert_device_matches_self(comparison_results)
    assert not tmp_path.joinpath("lib").exists()
    updated_file = newer_files[0]
    copied_file = newer_files[1]
    copied_file.unlink()
    assert f"Newer: {updated_file!s}" in caplog.text
    assert f"Newer: {copied_file!s}" in caplog.text


def test_detect_missing_secrets(tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture) -> None:
    """Does it detect missing secrets with '--secrets'?"""
    with caplog.at_level(logging.INFO):
        equip.handle_equip(
            behavior=equip.Behavior.Upgrade, root=tmp_path, secrets=equip.SecretsBehavior.Analyze.as_full_name()
        )

    assert "Detecting secrets" in caplog.text
    assert " MISSING" in caplog.text


def test_prompt_for_secrets(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Does it prompt the user for secrets with '--secrets -'?"""
    create_test_device_folder(tmp_path)  # Pre-install so equip doesn't invoke circup which fails with capsys
    monkeypatch.setattr(click, "prompt", skip_secrets)

    with caplog.at_level(logging.INFO):
        equip.handle_equip(behavior=equip.Behavior.Upgrade, root=tmp_path, secrets="-")

    assert "Updating sensor_node secrets" in caplog.text
    assert "Set a new value or press <Enter> to skip" in capsys.readouterr().out
    assert "Secrets updated" in caplog.text
    assert tmp_path.joinpath(SnsrPath.settings).exists()


def test_merge_secrets(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Does it correctly merge unrelated, old, and new secrets with '--secrets -'?"""
    create_test_device_folder(tmp_path)  # Pre-install so equip doesn't invoke circup which fails with capsys
    secrets_file = tmp_path.joinpath(SnsrPath.settings)
    old_secrets = {
        "CIRCUITPY_WIFI_SSID": "old ssid",
        "CIRCUITPY_WIFI_PASSWORD": "old password",
        "QTPY_BROKER_IP_ADDRESS": "old broker ip",
        "QTPY_NODE_GROUP": "old node group",
        "QTPY_NODE_NAME": "old node name",
        "UNRELATED_SECRET": "unrelated secret",
    }
    with secrets_file.open("w") as settings_fd:
        toml.dump(old_secrets, settings_fd)
    monkeypatch.setattr(click, "prompt", merge_secrets)

    with caplog.at_level(logging.INFO):
        equip.handle_equip(behavior=equip.Behavior.Upgrade, root=tmp_path, secrets="-")

    assert "Updating sensor_node secrets" in caplog.text
    assert "Set a new value or press <Enter> to skip" in capsys.readouterr().out
    assert "Secrets updated" in caplog.text
    assert secrets_file.exists()
    updated_secrets = toml.load(secrets_file)
    assert updated_secrets["CIRCUITPY_WIFI_SSID"] == "old ssid"
    assert updated_secrets["CIRCUITPY_WIFI_PASSWORD"] == "old password"  # noqa: S105 -- this is not a secret
    assert updated_secrets["QTPY_BROKER_IP_ADDRESS"] == "1.2.3.4"  # (Updated)
    assert updated_secrets["QTPY_NODE_GROUP"] == "old node group"
    assert updated_secrets["QTPY_NODE_NAME"] == "node_name"  # (Updated)
    assert updated_secrets["UNRELATED_SECRET"] == "unrelated secret"  # noqa: S105 -- this is not a secret (Preserved)
