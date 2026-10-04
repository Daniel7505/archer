# Chapter 2 resume state (for an interrupted agent)
- Renders: `nohup ./run_queue.sh &` (reads queue.txt, skips modes with "<mode> DONE" in done.txt, render_frames resumes per frame).
  Check it's alive: `pgrep -f run_queue.sh`. If dead and done.txt lacks modes, relaunch it (remove FAIL lines first).
- Queue: loot 216, mount 176, ride 231 (+hero still), city 197, establish 120, ride1 84 (reframed ride shot 1; hud_ch2 uses frames_ride1 for ride f1-84).
- Stills (vendor_*.png, dusk_skyline.png) DONE in stills/. Exports DONE in exports/.
- Post: comp_loot, comp_mount, comp_montage DONE. Remaining: python3 hud_ch2.py ride establish city
  python3 make_sfx_ch2.py ; python3 stitch_ch2.py
- Then: visual check, README, copy to /workspace/panda_repo/blender_chapter2, commit+push, gh release create film-v2.
- 22:55:51 ride DONE (1969 s) + hero still DONE. city rendering; then establish, ride1.
- 23:22:52 city DONE + comp_city DONE
- 23:37:21 establish DONE + comp_establish DONE; ride1 rendering
- 23:48:40 all renders DONE, comp_ride DONE; next: stitch
- 23:50:07 stitch DONE: chapter2.mp4 56.71 s, full_film_v2.mp4 112.67 s; next: commit/release
