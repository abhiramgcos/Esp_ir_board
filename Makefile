# Shortcuts for scripts/esp.sh. Run "make help" for the list.
ESP := ./scripts/esp.sh

.PHONY: help install open sch pcb 3d render3d copper gerbers render check bom fab rebuild clean

help:    ; @$(ESP) help
install: ; ./setup/install.sh
open:    ; @$(ESP) open
sch:     ; @$(ESP) sch
pcb:     ; @$(ESP) pcb
3d:      ; @$(ESP) 3d
render3d: ; @$(ESP) render3d
copper:  ; @./scripts/copper_views.sh
gerbers: ; @$(ESP) gerbers
render:  ; @$(ESP) render
check:   ; @$(ESP) check
bom:     ; @$(ESP) bom
fab:     ; @$(ESP) fab
rebuild: ; @$(ESP) rebuild
clean:   ; rm -rf build/
