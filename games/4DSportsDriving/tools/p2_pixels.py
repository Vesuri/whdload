import runpy,sys
sys.argv += ["--calls","4"]
runpy.run_path("tools/draw_pixels.py",run_name="__main__")
