# -*- coding: utf-8 -*-
from __future__ import annotations

from collections.abc import Callable
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request

from .catalog import VoiceCatalog, VoicePackage


ProgressCallback = Callable[[int | None, str], None]

_verifiedPackageCache: dict[str, tuple[int, int]] = {}


def _default_config_path() -> Path:
	try:
		import globalVars  # type: ignore

		configPath = getattr(getattr(globalVars, "appArgs", None), "configPath", None)
		if configPath:
			return Path(configPath)
	except Exception:
		pass
	return Path(tempfile.gettempdir()) / "googleTtsForNvda"


def data_root() -> Path:
	root = _default_config_path() / "googleTtsForNvda"
	root.mkdir(parents=True, exist_ok=True)
	return root


def voice_dir() -> Path:
	path = data_root() / "voices"
	path.mkdir(parents=True, exist_ok=True)
	return path


def package_file(package: VoicePackage) -> Path:
	return voice_dir() / package.fileName


def sha256(path: Path) -> str:
	digest = hashlib.sha256()
	with path.open("rb") as stream:
		for chunk in iter(lambda: stream.read(1024 * 1024), b""):
			digest.update(chunk)
	return digest.hexdigest()


def is_package_installed(package: VoicePackage) -> bool:
	path = package_file(package)
	if not path.is_file():
		_verifiedPackageCache.pop(package.id, None)
		return False
	stat = path.stat()
	cacheKey = (stat.st_size, stat.st_mtime_ns)
	if package.compressedSize and stat.st_size != package.compressedSize:
		_verifiedPackageCache.pop(package.id, None)
		return False
	if _verifiedPackageCache.get(package.id) == cacheKey:
		return True
	if package.sha256Checksum and sha256(path).lower() != package.sha256Checksum.lower():
		_verifiedPackageCache.pop(package.id, None)
		return False
	_verifiedPackageCache[package.id] = cacheKey
	return True


def installed_packages(catalog: VoiceCatalog) -> list[VoicePackage]:
	return [package for package in catalog.packages if is_package_installed(package)]


def remove_package(package: VoicePackage) -> None:
	_verifiedPackageCache.pop(package.id, None)
	path = package_file(package)
	try:
		path.unlink()
	except FileNotFoundError:
		pass


def download_package(package: VoicePackage, progress: ProgressCallback | None = None) -> Path:
	if is_package_installed(package):
		if progress:
			progress(100, f"{package.id} is already installed.")
		return package_file(package)
	if not package.url:
		raise RuntimeError(f"No download URL is available for {package.id}.")
	target = package_file(package)
	target.parent.mkdir(parents=True, exist_ok=True)
	tmp = target.with_suffix(".download")
	try:
		tmp.unlink()
	except FileNotFoundError:
		pass
	if progress:
		progress(0, f"Downloading {package.id}.")
	request = urllib.request.Request(package.url, headers={"User-Agent": "NVDA Google TTS"})
	with urllib.request.urlopen(request, timeout=120) as response, tmp.open("wb") as output:
		total = int(response.headers.get("Content-Length") or package.compressedSize or 0)
		downloaded = 0
		for chunk in iter(lambda: response.read(1024 * 256), b""):
			if not chunk:
				break
			output.write(chunk)
			downloaded += len(chunk)
			if progress and total:
				progress(min(99, int(downloaded * 100 / total)), f"Downloading {package.id}.")
	if package.compressedSize and tmp.stat().st_size != package.compressedSize:
		tmp.unlink(missing_ok=True)
		raise RuntimeError(f"Downloaded size mismatch for {package.id}.")
	if package.sha256Checksum:
		actualHash = sha256(tmp)
		if actualHash.lower() != package.sha256Checksum.lower():
			tmp.unlink(missing_ok=True)
			raise RuntimeError(f"Downloaded checksum mismatch for {package.id}.")
	os.replace(tmp, target)
	_verifiedPackageCache.pop(package.id, None)
	if progress:
		progress(100, f"Installed {package.id}.")
	return target


def copy_existing_package(source: Path, package: VoicePackage) -> Path:
	target = package_file(package)
	target.parent.mkdir(parents=True, exist_ok=True)
	shutil.copy2(source, target)
	_verifiedPackageCache.pop(package.id, None)
	if not is_package_installed(package):
		target.unlink(missing_ok=True)
		raise RuntimeError(f"Copied package did not pass verification: {package.id}.")
	return target
