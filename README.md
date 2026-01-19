# firelink

Personal project for sharing files and other utilities via Peer to Peer and Chunking.
Used by me and my friends

# Versions

- Python : **`3.14.2`**

# Developer mode

### Installing the dependencies

In the **`src`** folder

```bash
pip install -r requirements.txt
```

### Launch the app

In the **`src`** folder

```bash
python main.py
```

### Create an exe file to share

Windows

```bash
pyinstaller --noconsole --onefile --icon=img/fire.ico --add-data "img;img" --name="Firelink" main.py
```

Mac

```bash
pyinstaller --noconsole --onefile --icon=img/fire.ico --add-data "img:img" --name="Firelink" main.py
```

or run it directly through python

```bash
python -m PyInstaller --noconsole --onefile --icon=img/fire.ico --add-data "img;img" --name="Firelink" main.py
```

- Find it at `dist/Firelink.exe`
