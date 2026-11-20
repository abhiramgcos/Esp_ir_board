# Local toolchain setup

```bash
cd ~/Desktop/projects/Esp_ir_board
bash setup/install.sh            # asks for your sudo password once
bash setup/install.sh --conda    # optional: also build the conda env "esp-ir"
```

`install.sh` is safe to re-run. It does four things:

1. **Installs system packages.** It detects `pacman`, `apt` or `dnf`, then installs KiCad (8+ preferred),
   gerbv, librsvg (`rsvg-convert`), git, Python and xdg-utils. Packages you already have are skipped.
   On Ubuntu it adds the official `kicad-9.0-releases` PPA when your KiCad is older than 8.
2. **Creates `.venv`** at the repo root with `--system-site-packages`, then installs `setup/requirements.txt`
   (kiutils, numpy, scipy, pillow, scikit-image, pygerber 2.4).
3. **Creates the conda env** `esp-ir` from `setup/environment.yml`, only if you pass `--conda`. It finds conda
   in PATH or `~/miniconda3`.
4. **Runs a self-test:**
   * `kicad-cli version` and the Python imports.
   * The Gerber connectivity check (0 shorts, 0 opens, 162/162 pins).
   * The schematic netlist check (0 problems).

Use `--no-system` to skip step 1 (no sudo needed).

## Why a venv, and what conda is for

KiCad's `pcbnew` Python module is compiled against your **system** Python and installed into its
site-packages. It can't be pip- or conda-installed. So:

* **`.venv` (system Python + inherited site-packages)** runs everything:
  * the generators in `gen/` (`pcb.py`, `router.py`, `zones.py`, `silk.py`, `drc.py`, `build.sh`)
  * the checks in `tools/`
* **The conda env `esp-ir`** is a different Python. It can run `tools/gerber_connectivity.py`, image
  viewing, and `gen/erc.py` / `gen/sch.py` (which need only kiutils). It **cannot** import `pcbnew`.

## Troubleshooting

* **`pcbnew NOT importable from .venv`**
  * The venv was built from a different Python, for example conda's `python3` shadowing `/usr/bin/python3`.
    Run `conda deactivate`, then:
    `rm -rf .venv && /usr/bin/python3 -m venv --system-site-packages .venv && bash setup/install.sh --no-system`
  * Check that KiCad itself is installed: `python3 -c "import pcbnew; print(pcbnew.Version())"` with
    `/usr/bin/python3`.
  * After a big Python upgrade (Arch / CachyOS rolling updates), delete `.venv` and re-run the script.
* **`kicad-cli sch erc` / `kicad-cli pcb drc` not found:** these commands need **KiCad 8+**.
  * `gen/drc.py` uses the Python API and works on KiCad 7 too.
  * `gen/erc.py` checks the exported netlist, which also works on KiCad 7.
* **gerbv on Wayland:** gerbv is a GTK2/X11 app. On GNOME/KDE Wayland it runs through XWayland
  automatically. If the window doesn't open, try `GDK_BACKEND=x11 gerbv ...`, or view the Gerbers in KiCad's
  own **Gerber Viewer** (`gerbview`).
* **Ubuntu PPA failed** (proxy or offline): the script falls back to the distro's KiCad. Everything except
  `kicad-cli erc/drc` still works.
* **pip SSL / proxy errors:** set `PIP_INDEX_URL` / `HTTPS_PROXY`, then re-run with `--no-system`.

## 3D renders (`make render3d`, `tools/render3d.py`)

`tools/render3d.py` draws offscreen 3D PNGs: top isometric, bottom isometric and straight-down top. It
exists because KiCad 7/8 have no `kicad-cli pcb render`. On KiCad 9+, `make 3d` uses KiCad's own renderer.

* **Python packages:** `trimesh`, `shapely`, `mapbox_earcut`, `pyrender`, `PyOpenGL==3.1.7`. They are in
  `requirements.txt`, and `install.sh` installs them into `.venv`.
* **OpenGL backend:** the script picks it automatically.
  * It uses **OSMesa** (pure software, no display needed) if `libOSMesa` is found. Install it with
    apt `libosmesa6` on Ubuntu up to 24.04; Mesa ≥ 25.1 has dropped OSMesa.
  * Otherwise it uses **EGL**, which works on any desktop with a GPU driver (NVIDIA, AMD, Intel).
  * To force one: `PYOPENGL_PLATFORM=egl make render3d` or `PYOPENGL_PLATFORM=osmesa make render3d`.
* **Part models:** KiCad's VRML (`.wrl`) 3D models are read from `$KICAD9_3DMODEL_DIR` (and the
  8/7/6 versions), `/usr/share/kicad/3dmodels`, or a folder given with `MODELS3D=/path/to/3dmodels make render3d`.
  Install them with:
  * Ubuntu/Debian: `sudo apt install kicad-packages3d` (big, ≈5 GB)
  * Arch: `sudo pacman -S kicad-library-3d`
  * Fedora: `sudo dnf install kicad-packages3d`

  Footprints whose model is missing are drawn as plain boxes; the script prints which ones. The USB-C
  receptacle (HRO TYPE-C-31-M-12) has no KiCad model, so a simple metal receptacle is drawn for it.
* **Options:** `MASK=green|blue|black make render3d` sets the solder-mask colour (default black).
