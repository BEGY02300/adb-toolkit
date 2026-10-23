# ADB Toolkit

Petit menu interactif en Python pour utiliser Android Debug Bridge (ADB) sans
retenir toutes ses commandes. Il permet de gérer les appareils connectés en USB
ou en Wi-Fi, les fichiers, les APK et quelques sauvegardes courantes.

## Prérequis

- Python 3.9 ou plus récent
- [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools)
- La commande `adb` doit être accessible depuis le `PATH`
- Le débogage USB doit être activé et l'appareil autorisé sur le téléphone

Aucune dépendance Python supplémentaire n'est nécessaire.

## Installation et démarrage

Téléchargez ou clonez le projet, ouvrez un terminal dans le dossier du script,
puis lancez :

```powershell
python adb_toolkit.py
```

Sur certaines installations de Windows, utilisez plutôt `py` :

```powershell
py adb_toolkit.py
```

Pour afficher l'aide ou la version :

```powershell
python adb_toolkit.py --help
python adb_toolkit.py --version
```

L'option `--no-clear` empêche le script d'effacer le terminal entre les
affichages du menu :

```powershell
python adb_toolkit.py --no-clear
```

## Fonctionnalités

### Appareil

- Connecter un appareil ADB par Wi-Fi à partir d'une adresse `IP:PORT`
- Lister les appareils détectés, y compris ceux qui ne sont pas encore prêts
- Choisir un appareil actif pour les actions suivantes
- Ouvrir un shell Android interactif (`exit` pour revenir au menu)
- Afficher le modèle, le fabricant, la version Android, le niveau SDK et le
  correctif de sécurité
- Afficher l'espace disque Android
- Redémarrer le serveur ADB ou déconnecter les appareils connectés en Wi-Fi

Pour plusieurs appareils, le toolkit demande lequel utiliser lorsqu'aucun
appareil actif n'a été choisi. Le choix actif reste valable pendant la session
du programme.

### Fichiers et applications

- Installer un fichier `.apk` existant
- Installer tous les `.apk` présents dans un dossier (sans parcourir ses
  sous-dossiers)
- Envoyer un fichier ou un dossier vers Android (`push`)
- Récupérer un fichier ou un dossier depuis Android (`pull`)
- Copier vers l'ordinateur le contenu de `DCIM`, `Download` ou `WhatsApp`

L'installation des APK utilise les options ADB `-r` et `-g` : elle réinstalle
l'application en conservant ses données si possible et demande l'octroi des
permissions d'exécution. N'installez que des APK auxquels vous faites
confiance.

## Connexion Wi-Fi

Choisissez l'option **Connecter un appareil Wi-Fi** et saisissez l'adresse
`IP:PORT` de l'appareil. Le téléphone et l'ordinateur doivent pouvoir
communiquer sur le réseau, et le débogage sans fil doit être configuré pour
accepter la connexion ADB. La procédure de configuration et le port dépendent
de la version Android et de l'appareil.

## Configuration mémorisée

Le script enregistre les dossiers utilisés pour les installations groupées et
les sauvegardes, afin de les proposer lors de la prochaine utilisation.

- Windows : `%APPDATA%\ADBToolkit\config.json`
- Autres systèmes : `~/.config/ADBToolkit/config.json`

Ces préférences sont facultatives et le fichier est créé automatiquement au
premier enregistrement.

## Dépannage

- **ADB est introuvable** : installez Android Platform-Tools, puis ajoutez le
  dossier contenant `adb` au `PATH`. Fermez et rouvrez le terminal.
- **Aucun appareil autorisé** : vérifiez le câble ou le réseau, activez le
  débogage sur le téléphone et acceptez la demande d'autorisation affichée.
- **Connexion Wi-Fi refusée** : vérifiez l'adresse et le port ADB ainsi que la
  configuration du débogage sans fil.
- **Échec de transfert ou de sauvegarde** : vérifiez le chemin saisi, l'espace
  disponible et les autorisations d'accès sur l'appareil.

## Notes

- Le script est autonome : il n'a pas besoin de fichier ou de paquet Python
  supplémentaire.
- Les commandes ADB sont exécutées sans passer par un shell système.
- Les chemins locaux copiés depuis l'Explorateur Windows peuvent être saisis
  avec leurs guillemets.
