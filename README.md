# LASIGE – Summer of Research

Research work for the **LASIGE Summer of Research 2025**, built on the **Blossom** social robot platform.

---

## Project Structure

```
blossom-lasige-research/
├── start.py                  # Application entry point
├── requirements.txt          # Runtime dependencies
├── build_appimage.sh         # AppImage build script
├── AppRun                    # AppImage entry point
├── blossom.desktop           # AppImage desktop entry
├── src/                      # Main application (PyQt6 GUI)
│   ├── main_window.py
│   ├── main_window.ui
│   ├── settings_dialog.py
│   ├── blossom.png           # Application icon
│   ├── resources.qrc
│   ├── resources_rc.py       # Compiled Qt resources (do not edit)
│   └── threads/
├── mimetic/                  # MediaPipe pose/face tracking module
├── dancer/                   # Motion/dance generation module
├── blossom_public/           # Blossom robot HTTP server (submodule)
└── .github/workflows/        # CI – builds and publishes AppImage
```

---

## Development Setup

Requires **Linux** (Ubuntu 22.04+ recommended) and **Python 3.11**.

### 1. Clone

```bash
git clone --recurse-submodules git@github.com:DiogoSaraiva/blossom-lasige-research.git
cd blossom-lasige-research
```

### 2. Python environment

Using [pyenv](https://github.com/pyenv/pyenv):

```bash
pyenv install 3.11.13
pyenv virtualenv 3.11.13 blossom-py3.11
pyenv activate blossom-py3.11
pip install -r requirements.txt
```

### 3. Run in dev mode

```bash
python3 start.py
```

---

## Building the AppImage

The AppImage bundles Python 3.11 and all dependencies into a single portable executable.

```bash
bash build_appimage.sh
```

Output: `dist/Blossom_LASIGE-x86_64.AppImage`

> Requires `rsync` and `appimagetool` (downloaded automatically on first run).

---

## Releases

Pushing a tag triggers GitHub Actions to build the AppImage and publish it as a GitHub Release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The release will include `Blossom_LASIGE-x86_64.AppImage` as a downloadable asset.

---

## Regenerating Qt Resources

If `src/blossom.png` is changed, regenerate `src/resources_rc.py`:

```bash
pip install pyside6  # only needed for the rcc tool
cd src && pyside6-rcc resources.qrc -o resources_rc.py && sed -i 's/from PySide6/from PyQt6/' resources_rc.py
```

---

## SSH Authentication

To push using SSH instead of HTTPS:

```bash
git remote set-url origin git@github.com:DiogoSaraiva/blossom-lasige-research.git

cd blossom_public
git remote set-url origin git@github.com:DiogoSaraiva/blossom-public.git
```

---

## License

Inherits the license from [blossom-public](https://github.com/hrc2/blossom-public). Additional work may follow additional licensing.
