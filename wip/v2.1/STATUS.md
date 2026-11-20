# v2.1 "optimized" board: work in progress (handed off from the cloud session)

## Done
* **Compact placement** in `gen/placement.py`: 68 × 48 mm, down from 76 × 56 (−23 % area).
* **Router upgrades** in `gen/router.py`:
  * 45° (octilinear) traces.
  * Power nets routed first.
  * Higher via cost.
  * Rip-up with order jitter (`ROUTER_ROUNDS`, default 40).
  * Tight clearance margin allowed only within 1 mm of the USB-C pins (`fine_zone`).
* **Antenna:** no tracks or pour under the antenna strip on either layer (`gen/zones.py keepout`).
* **This folder** holds the last fully routed v2.1 board (made *before* the `fine_zone` change):
  * Every net is routed.
  * Track length is 1634 mm (v2.0: 1733 mm).
  * Vias: 79 stitching + routing.
  * DRC: **7 clearance errors of 0.18–0.19 mm** (VBUS next to J1 A1/B12 GND, USB_DN next to U4 pin 14).
    The `fine_zone` change is meant to fix these.
* **3D renderer:** `tools/render3d.py` (`make render3d`). Sample renders of v2.0 are in `docs/img/v2.0_3d_*.png`.

## To finish
1. Rebuild with the current generators: `cd gen && ./build.sh ../build` (the router takes about 5 min).
2. Get to DRC = 0 errors. If it fails, re-run, or nudge parts in `placement.py`.
3. Copy `build/` into `hardware/`, run `make fab`, `make render`, `make render3d`, `make check`.
4. Update `silk.py` positions for the smaller board (its edge limits are still hard-coded for 76 × 56). Then
   update README / BUILD_LOG (step 6), merge to `main`.
