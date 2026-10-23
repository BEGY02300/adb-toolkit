#!/usr/bin/env python3
"""ADB Toolkit -- interface interactive pour Android Debug Bridge.

Documentation intégrée
======================
Prérequis : Python 3.9+ et Android Platform Tools (la commande ``adb`` doit
être accessible depuis le PATH). Activez et autorisez le débogage USB sur le
téléphone, puis lancez ``python adb_toolkit.py``. Aucun paquet Python ni aucun
fichier n'est requis à côté de ce script. Les préférences optionnelles sont
rangées dans %APPDATA%\\ADBToolkit, en dehors de ce dossier.

Options : ``python adb_toolkit.py --help`` ou ``--no-clear``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

APP_NAME = "ADB Toolkit"
VERSION = "2.1.0"
CONFIG_PATH = Path(os.environ.get("APPDATA") or Path.home() / ".config") / "ADBToolkit" / "config.json"
BACKUP_SOURCES = {
    "1": ("Photos et vidéos (DCIM)", "/sdcard/DCIM/"),
    "2": ("Téléchargements", "/sdcard/Download/"),
    "3": ("WhatsApp", "/sdcard/WhatsApp/"),
}


@dataclass
class CommandResult:
    code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def output(self) -> str:
        return "\n".join(item for item in (self.stdout, self.stderr) if item).strip()


def say(text: str = "", kind: str = "info") -> None:
    """Print a short status message without requiring third-party packages."""
    prefix = {"ok": "✓", "error": "Erreur:", "warn": "Attention:", "info": ""}.get(kind, "")
    print(f"{prefix} {text}".strip())


def clean_path(value: str) -> Path:
    """Accept a Windows Explorer path pasted with surrounding quotes."""
    return Path(value.strip().strip('"').strip("'"))


def load_config() -> dict[str, str]:
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as error:
        say(f"Configuration ignorée ({error}).", "warn")
        return {}


def save_config(config: dict[str, str]) -> bool:
    """Store preferences outside this one-file project."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w", encoding="utf-8") as file:
            json.dump(config, file, ensure_ascii=False, indent=2)
        return True
    except OSError as error:
        say(f"Impossible d'enregistrer la configuration : {error}", "error")
        return False


def run(command: list[str], timeout: Optional[int] = None) -> CommandResult:
    """Execute a command safely, never through a shell."""
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False,
        )
        return CommandResult(completed.returncode, completed.stdout.strip(), completed.stderr.strip())
    except FileNotFoundError:
        return CommandResult(127, "", "La commande adb est introuvable dans le PATH.")
    except subprocess.TimeoutExpired:
        return CommandResult(124, "", "La commande a expiré.")
    except OSError as error:
        return CommandResult(1, "", str(error))


def adb(args: Iterable[str], serial: Optional[str] = None, timeout: Optional[int] = None) -> CommandResult:
    command = ["adb"] + (["-s", serial] if serial else []) + list(args)
    return run(command, timeout)


def show_result(result: CommandResult, success: Optional[str] = None) -> bool:
    if result.ok:
        say(success or result.output or "Commande terminée.", "ok")
        return True
    say(result.output or "La commande a échoué.", "error")
    return False


def check_adb() -> bool:
    if not shutil.which("adb"):
        say("ADB est introuvable. Installe Android Platform Tools puis ajoute-le au PATH.", "error")
        return False
    return show_result(adb(["version"], timeout=10), "ADB est prêt.")


def devices(include_unavailable: bool = False) -> list[tuple[str, str]]:
    result = adb(["devices"])
    if not result.ok:
        say(result.output or "Impossible de lister les appareils.", "error")
        return []
    entries = []
    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and (include_unavailable or fields[1] == "device"):
            entries.append((fields[0], fields[1]))
    return entries


def choose_device(current: Optional[str] = None) -> Optional[str]:
    available = devices()
    serials = [serial for serial, _ in available]
    if not available:
        say("Aucun appareil autorisé n'est connecté.", "error")
        return None
    if current in serials:
        return current
    if len(available) == 1:
        return available[0][0]
    print("\nAppareils disponibles :")
    for number, (serial, _) in enumerate(available, 1):
        print(f"  {number}. {serial}")
    while True:
        answer = input("Numéro de l'appareil (Entrée pour annuler) : ").strip()
        if not answer:
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(available):
            return available[int(answer) - 1][0]
        say("Choix invalide.", "error")


def pause() -> None:
    input("\nAppuyez sur Entrée pour continuer...")


def prompt_folder(label: str, default: str = "", create: bool = False) -> Optional[Path]:
    suffix = f" [{default}]" if default else ""
    raw = input(f"{label}{suffix} : ").strip()
    folder = clean_path(raw) if raw else (Path(default) if default else None)
    if not folder:
        return None
    try:
        if create:
            folder.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        say(f"Impossible de créer le dossier : {error}", "error")
        return None
    if not folder.is_dir():
        say("Dossier introuvable.", "error")
        return None
    return folder


def connect() -> None:
    address = input("Adresse IP:PORT (ex. 192.168.1.50:5555) : ").strip()
    if not address:
        return
    if not re.fullmatch(r"[^\s:]+:\d{1,5}", address):
        say("Format attendu : adresse-ip:port.", "error")
        return
    show_result(adb(["connect", address]), "Connexion ADB établie.")


def list_devices() -> None:
    found = devices(include_unavailable=True)
    if not found:
        say("Aucun appareil ADB détecté.", "warn")
        return
    print("\nAppareils ADB :")
    for serial, state in found:
        print(f"  - {serial} ({'prêt' if state == 'device' else state})")


def open_shell(selected: Optional[str]) -> None:
    serial = choose_device(selected)
    if serial:
        say("Shell Android ouvert. Tapez 'exit' pour revenir au menu.")
        try:
            subprocess.run(["adb", "-s", serial, "shell"], check=False)
        except OSError as error:
            say(str(error), "error")


def device_info(selected: Optional[str]) -> None:
    serial = choose_device(selected)
    if not serial:
        return
    properties = {
        "Modèle": "ro.product.model", "Fabricant": "ro.product.manufacturer",
        "Android": "ro.build.version.release", "SDK": "ro.build.version.sdk",
        "Correctif": "ro.build.version.security_patch",
    }
    print(f"\nInformations — {serial}")
    for label, property_name in properties.items():
        result = adb(["shell", "getprop", property_name], serial)
        print(f"  {label}: {result.stdout or 'inconnu'}")


def install_apk(selected: Optional[str]) -> None:
    serial = choose_device(selected)
    if not serial:
        return
    raw = input("Chemin de l'APK : ").strip()
    if not raw:
        return
    apk = clean_path(raw)
    if not apk.is_file() or apk.suffix.lower() != ".apk":
        say("Sélectionnez un fichier .apk existant.", "error")
        return
    show_result(adb(["install", "-r", "-g", str(apk)], serial, timeout=600), f"{apk.name} a été installé.")


def install_folder(selected: Optional[str], config: dict[str, str]) -> None:
    serial = choose_device(selected)
    if not serial:
        return
    folder = prompt_folder("Dossier contenant les APK", config.get("apk_dir", ""))
    if not folder:
        return
    apks = sorted(item for item in folder.iterdir() if item.is_file() and item.suffix.lower() == ".apk")
    if not apks:
        say("Aucun fichier .apk trouvé.", "warn")
        return
    config["apk_dir"] = str(folder)
    save_config(config)
    failures = 0
    for index, apk in enumerate(apks, 1):
        print(f"[{index}/{len(apks)}] {apk.name}")
        result = adb(["install", "-r", "-g", str(apk)], serial, timeout=600)
        if result.ok:
            say("Installé.", "ok")
        else:
            failures += 1
            say(result.output or "Échec de l'installation.", "error")
    say("Installation terminée." if not failures else f"Terminé avec {failures} échec(s).", "ok" if not failures else "warn")


def push_file(selected: Optional[str]) -> None:
    serial = choose_device(selected)
    if not serial:
        return
    raw = input("Fichier ou dossier local : ").strip()
    if not raw:
        return
    local = clean_path(raw)
    if not local.exists():
        say("Chemin local introuvable.", "error")
        return
    remote = input("Destination Android [/sdcard/Download/] : ").strip() or "/sdcard/Download/"
    show_result(adb(["push", str(local), remote], serial, timeout=1800), "Transfert vers Android terminé.")


def pull_file(selected: Optional[str]) -> None:
    serial = choose_device(selected)
    if not serial:
        return
    remote = input("Chemin Android (ex. /sdcard/photo.jpg) : ").strip()
    if not remote:
        return
    destination = prompt_folder("Dossier de destination local", "Sauvegarde_Android", create=True)
    if destination:
        show_result(adb(["pull", remote, str(destination)], serial, timeout=1800), "Récupération terminée.")


def backup(selected: Optional[str], config: dict[str, str]) -> None:
    serial = choose_device(selected)
    if not serial:
        return
    print("\nÀ sauvegarder :")
    for key, (label, _) in BACKUP_SOURCES.items():
        print(f"  {key}. {label}")
    choice = input("Choix : ").strip()
    if choice not in BACKUP_SOURCES:
        say("Choix invalide.", "error")
        return
    label, source = BACKUP_SOURCES[choice]
    default = config.get("backup_dir", str(Path.cwd() / "Sauvegarde_Android"))
    destination = prompt_folder("Dossier de destination", default, create=True)
    if not destination:
        return
    config["backup_dir"] = str(destination)
    save_config(config)
    show_result(adb(["pull", source, str(destination)], serial, timeout=3600), f"Sauvegarde « {label} » terminée.")


def disk_usage(selected: Optional[str]) -> None:
    serial = choose_device(selected)
    if not serial:
        return
    result = adb(["shell", "df", "-h"], serial)
    if result.ok:
        print("\nEspace disque :\n" + result.stdout)
    else:
        show_result(result)


def restart_adb() -> None:
    stopped, started = adb(["kill-server"]), adb(["start-server"])
    if stopped.ok and started.ok:
        say("Serveur ADB redémarré.", "ok")
    else:
        show_result(started)


def disconnect() -> None:
    address = input("Adresse à déconnecter (Entrée = toutes les connexions TCP/IP) : ").strip()
    show_result(adb(["disconnect", address] if address else ["disconnect"]), "Connexion(s) ADB déconnectée(s).")


def configure(config: dict[str, str]) -> None:
    print(f"\nConfiguration : {CONFIG_PATH}")
    print(f"Dossier APK : {config.get('apk_dir', 'non défini')}")
    print(f"Dossier sauvegarde : {config.get('backup_dir', 'non défini')}")
    if input("Modifier le dossier APK ? [o/N] : ").strip().lower() in {"o", "oui", "y", "yes"}:
        folder = prompt_folder("Nouveau dossier APK")
        if folder:
            config["apk_dir"] = str(folder)
    if input("Modifier le dossier de sauvegarde ? [o/N] : ").strip().lower() in {"o", "oui", "y", "yes"}:
        raw = input("Nouveau dossier de sauvegarde : ").strip()
        if raw:
            config["backup_dir"] = str(clean_path(raw))
    save_config(config)
    say("Configuration enregistrée.", "ok")


MENU = (
    ("APPAREIL", (
        ("1", "Connecter un appareil Wi-Fi (IP:PORT)"),
        ("2", "Lister les appareils ADB"),
        ("3", "Ouvrir un shell Android"),
        ("4", "Afficher les informations de l'appareil"),
        ("10", "Afficher l'espace disque Android"),
        ("11", "Redémarrer le serveur ADB"),
        ("12", "Déconnecter une connexion ADB Wi-Fi"),
        ("14", "Choisir l'appareil actif"),
    )),
    ("FICHIERS ET APPLICATIONS", (
        ("5", "Installer un APK"),
        ("6", "Installer tous les APK d'un dossier"),
        ("7", "Envoyer un fichier/dossier vers Android (push)"),
        ("8", "Récupérer un fichier/dossier depuis Android (pull)"),
        ("9", "Sauvegarder DCIM, téléchargements ou WhatsApp"),
    )),
    ("PREFERENCES", (
        ("13", "Configurer les dossiers mémorisés"),
        ("0", "Quitter"),
    )),
)


def print_menu(clear_screen: bool, selected: Optional[str] = None) -> None:
    if clear_screen:
        os.system("cls" if os.name == "nt" else "clear")
    title = f"{APP_NAME} v{VERSION}"
    subtitle = "Gestion simple de votre appareil Android"
    status = f"Appareil actif : {selected or 'détection automatique'}"
    entries = [f"  {key:>2}  {label}" for _, group in MENU for key, label in group]
    width = max(map(len, [title, subtitle, status, *entries])) + 2
    border = "+" + "-" * (width + 2) + "+"

    def print_line(text: str = "") -> None:
        print(f"| {text:<{width}} |")

    print(border)
    print_line(title.center(width))
    print_line(subtitle.center(width))
    print(border)
    print_line(status)
    print(border)
    for heading, group in MENU:
        print_line(heading)
        for key, label in group:
            print_line(f"  {key:>2}  {label}")
        print_line()
    print(border)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interface interactive, sans dépendance Python, pour Android Debug Bridge.",
        epilog="La documentation et les prérequis sont aussi en tête du script.",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    parser.add_argument("--no-clear", action="store_true", help="ne pas effacer le terminal entre les menus")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not check_adb():
        return 1
    config = load_config()
    selected: Optional[str] = None
    actions = {
        "1": connect, "2": list_devices, "3": lambda: open_shell(selected),
        "4": lambda: device_info(selected), "5": lambda: install_apk(selected),
        "6": lambda: install_folder(selected, config), "7": lambda: push_file(selected),
        "8": lambda: pull_file(selected), "9": lambda: backup(selected, config),
        "10": lambda: disk_usage(selected), "11": restart_adb, "12": disconnect,
        "13": lambda: configure(config),
    }
    try:
        while True:
            print_menu(not args.no_clear, selected)
            choice = input("\nVotre choix : ").strip()
            if choice == "0":
                say("Fermeture du toolkit. À bientôt !")
                return 0
            if choice == "14":
                device = choose_device()
                if device:
                    selected = device
                    say(f"Appareil actif : {selected}", "ok")
                pause()
                continue
            action = actions.get(choice)
            if not action:
                say("Choix invalide.", "error")
            else:
                action()
            if choice != "3":
                pause()
    except (KeyboardInterrupt, EOFError):
        print()
        say("Fermeture du toolkit.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
