# scripts/

`scripts/esp.sh` is the single entry point. `make <target>` does the same thing. The script activates
`.venv` automatically if `setup/install.sh` created it.

| Command | `make` | What it does |
|---|---|---|
| `scripts/esp.sh open` | `make open` | Opens the KiCad project manager on `hardware/esp_ir_board.kicad_pro` |
| `scripts/esp.sh sch` | `make sch` | Opens the schematic editor |
| `scripts/esp.sh pcb` | `make pcb` | Opens the PCB editor |
| `scripts/esp.sh 3d` | `make 3d` | Opens the PCB editor (View → 3D Viewer, Alt+3). On KiCad 9+ it also renders 3D PNGs to `build/render/` |
| `scripts/esp.sh gerbers` | `make gerbers` | Shows `fab/gerbers` in gerbv, the way the fab will see them |
| `scripts/esp.sh render` | `make render` | Writes schematic, top, bottom-copper and back-silk PNGs to `build/render/` |
| `scripts/esp.sh check` | `make check` | Runs the netlist-vs-design ERC, KiCad ERC/DRC (KiCad 8+, else the pcbnew DRC) and the independent Gerber connectivity check, then prints PASS/FAIL |
| `scripts/esp.sh bom` | `make bom` | Prints `fab/BOM_full.csv` as a table |
| `scripts/esp.sh fab` | `make fab` | Regenerates Gerbers, drills, BOMs, the JLC CPL, the Gerber zip and the PDFs |
| `scripts/esp.sh rebuild` | `make rebuild` | Regenerates the whole board from `gen/` into `build/`. Takes a few minutes and makes new UUIDs; `hardware/` is not touched |
| — | `make install` | Runs `setup/install.sh` |
| — | `make clean` | Deletes `build/` |

If a tool is missing, the script names it and points you to `./setup/install.sh`.
