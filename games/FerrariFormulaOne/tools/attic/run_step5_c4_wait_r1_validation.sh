set -e
. tmp/dev/amiga/env.sh
C1_VARIANT=native C4_HEAVY_FRAMES=300 python3 tmp/dev/tools/capture_step5_c4_wait_r1_start_grid_center.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-start_grid_center-native-fps.log 2>&1
C1_VARIANT=native C4_HEAVY_FRAMES=300 python3 tmp/dev/tools/capture_step5_c4_wait_r1_heavy_v2.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-heavy_v2-native-fps.log 2>&1
C1_VARIANT=baseline-render python3 tmp/dev/tools/capture_step5_c4_wait_r1_ab_images.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-ab-baseline-render-images.log 2>&1
C1_VARIANT=candidate python3 tmp/dev/tools/capture_step5_c4_wait_r1_ab_images.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-ab-candidate-images.log 2>&1
C1_VARIANT=baseline-render python3 tmp/dev/tools/capture_step5_c4_wait_r1_start_grid_center_images.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-start_grid_center-baseline-render-images.log 2>&1
C1_VARIANT=candidate python3 tmp/dev/tools/capture_step5_c4_wait_r1_start_grid_center_images.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-start_grid_center-candidate-images.log 2>&1
C1_VARIANT=baseline-render python3 tmp/dev/tools/capture_step5_c4_wait_r1_heavy_v2_images.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-heavy_v2-baseline-render-images.log 2>&1
C1_VARIANT=candidate python3 tmp/dev/tools/capture_step5_c4_wait_r1_heavy_v2_images.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-heavy_v2-candidate-images.log 2>&1
python3 tmp/dev/tools/capture_step5_c4_wait_r1_exit.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-exit.log 2>&1
python3 tmp/dev/tools/test_step5_c4_wait_r1_default.py > tmp/dev/tmp/step5/c4-wait-r1-v2-default.log 2>&1
C1_VARIANT=baseline-render FIELDS=100 python3 tmp/dev/tools/capture_step5_c4_wait_r1_fullloop.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-baseline-render-run.log 2>&1
python3 tmp/dev/tools/analyze_step5_profile.py c4-wait-r1-v2-fullloop-a500-baseline-render > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-baseline-render-analyze_step5_profile.log 2>&1
python3 tmp/dev/tools/percar_step5_profile.py c4-wait-r1-v2-fullloop-a500-baseline-render 0 0 > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-baseline-render-percar_step5_profile.log 2>&1
python3 tmp/dev/tools/classify_step5_profile.py c4-wait-r1-v2-fullloop-a500-baseline-render 0 0 > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-baseline-render-classify_step5_profile.log 2>&1
python3 tmp/dev/tools/audit_step5_c4_heavy_profile.py c4-wait-r1-v2-fullloop-a500-baseline-render > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-baseline-render-audit_step5_c4_heavy_profile.log 2>&1
python3 tmp/dev/tools/archive_profile_traces.py c4-wait-r1-v2-fullloop-a500-baseline-render > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-baseline-render-archive_profile_traces.log 2>&1
C1_VARIANT=candidate FIELDS=100 python3 tmp/dev/tools/capture_step5_c4_wait_r1_fullloop.py a500 > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-candidate-run.log 2>&1
python3 tmp/dev/tools/analyze_step5_profile.py c4-wait-r1-v2-fullloop-a500-candidate > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-candidate-analyze_step5_profile.log 2>&1
python3 tmp/dev/tools/percar_step5_profile.py c4-wait-r1-v2-fullloop-a500-candidate 0 0 > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-candidate-percar_step5_profile.log 2>&1
python3 tmp/dev/tools/classify_step5_profile.py c4-wait-r1-v2-fullloop-a500-candidate 0 0 > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-candidate-classify_step5_profile.log 2>&1
python3 tmp/dev/tools/audit_step5_c4_heavy_profile.py c4-wait-r1-v2-fullloop-a500-candidate > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-candidate-audit_step5_c4_heavy_profile.log 2>&1
python3 tmp/dev/tools/archive_profile_traces.py c4-wait-r1-v2-fullloop-a500-candidate > tmp/dev/tmp/step5/c4-wait-r1-v2-fullloop-a500-candidate-archive_profile_traces.log 2>&1
