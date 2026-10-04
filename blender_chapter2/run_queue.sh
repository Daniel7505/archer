#!/bin/bash
# resumable render queue: lines in queue.txt = "<mode> <expected_frames> [extra args]". Re-read every pass.
cd /workspace/archer_scene/chapter2
B=/workspace/blender/blender-4.2.23-linux-x64/blender
touch done.txt
while [ ! -f queue_stop ]; do
  ran=0
  while read -r mode n extra; do
    [ -z "$mode" ] && continue
    grep -q "^$mode DONE" done.txt && continue
    fails=$(grep -c "^$mode FAIL" done.txt)
    [ "$fails" -ge 2 ] && continue
    ran=1
    echo "$(date '+%F %T') queue: start $mode" >> render_log.txt
    $B -b ../scene.blend -P chapter2_scene.py -- mode=$mode anim volume=0 samples=6 $extra > tmp/log_$mode.txt 2>&1
    have=$(find frames_$mode -name 'f_*.png' -size +0 2>/dev/null | wc -l)
    if [ "$have" -ge "$n" ]; then echo "$mode DONE" >> done.txt; echo "$(date '+%F %T') queue: $mode DONE ($have frames)" >> render_log.txt
    else echo "$mode FAIL" >> done.txt; echo "$(date '+%F %T') queue: $mode incomplete ($have/$n) see tmp/log_$mode.txt" >> render_log.txt; fi
    break
  done < queue.txt
  [ $ran -eq 0 ] && sleep 20
done
