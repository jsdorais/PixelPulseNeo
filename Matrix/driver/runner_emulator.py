
import sys, time, importlib, inspect
from PIL import Image
from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions

def load_cmd(cmd_name):
    mod = importlib.import_module(f"Matrix.driver.commands.{cmd_name}_cmd")
    # only classes defined in the module (ignore imported bases)
    candidates = [obj for name, obj in inspect.getmembers(mod, inspect.isclass)
                  if name.endswith("Cmd") and obj.__module__ == mod.__name__]
    if not candidates:
        raise RuntimeError(f"No *Cmd class defined in module {mod.__name__}")
    exact = [c for c in candidates if c.__name__.lower() == f"{cmd_name}cmd"]
    return exact[0] if exact else candidates[0]

def main():
    if len(sys.argv) < 3:
        print("usage: python -m Matrix.driver.runner_emulator <command> <duration_sec> [fps]")
        sys.exit(1)
    cmd_name   = sys.argv[1]
    duration   = float(sys.argv[2])
    fps        = float(sys.argv[3]) if len(sys.argv) > 3 else 12.0

    # Force 5x chain (320x64)
    opts = RGBMatrixOptions()
    opts.rows = 64
    opts.cols = 64
    opts.chain_length = 5
    matrix = RGBMatrix(options=opts)
    expected_w = opts.cols * opts.chain_length
    expected_h = opts.rows

    CmdCls = load_cmd(cmd_name)
    cmd = CmdCls()
    cmd.update()

    end = time.time() + duration
    delay = 1.0 / fps
    while time.time() < end:
        img = cmd.generate_image()
        # Auto-resize to 320x64 if the command produced 64x64 or anything else
        if img.size != (expected_w, expected_h):
            img = img.resize((expected_w, expected_h), Image.NEAREST)
        matrix.SetImage(img)
        time.sleep(delay)

if __name__ == "__main__":
    main()
