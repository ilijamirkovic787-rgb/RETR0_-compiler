#!/usr/bin/env python3
import sys, os, time, random, shutil
from retr0_compiler import compile_source, VM, decompile

WATCHDOGS_ASCII = r"""
                /\
               /  \
              / /\ \
             / /  \ \
            /_/____\_\
             \ \  / /
              \ \/ /
               \  /
                \/
"""

RETR0_ASCII = r"""
██████╗ ███████╗████████╗██████╗  ██████╗ 
██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═████╗
██████╔╝█████╗     ██║   ██████╔╝██║██╔██║
██╔══██╗██╔══╝     ██║   ██╔══██╗████╔╝██║
██║  ██║███████╗   ██║   ██║  ██║╚██████╔╝
╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ 
"""

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
RED = "\033[31m"

def term_width():
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80

def color(txt, c, use_color=True):
    if not use_color:
        return txt
    return f"{c}{txt}{RESET}"

def render_banner(right_logo: str, main_banner: str, use_color: bool):
    w = term_width()
    logo_lines = right_logo.strip("\n").splitlines()
    banner_lines = main_banner.strip("\n").splitlines()
    max_lines = max(len(logo_lines), len(banner_lines))
    logo_lines += [""] * (max_lines - len(logo_lines))
    banner_lines += [""] * (max_lines - len(banner_lines))
    out = []
    for bl, ll in zip(banner_lines, logo_lines):
        pad = ""
        try:
            pad = ll.rjust(max(0, w - len(bl)))
        except:
            pad = ll
        out.append(color(bl, CYAN, use_color) + pad)
    return "\n".join(out)

def glitch_frames(banner: str, frames: int = 8, intensity: float = 0.12):
    lines = banner.splitlines()
    chars = list("▓▒░█@#%&?<>/\\|0123456789")
    for _ in range(frames):
        new_lines = []
        for L in lines:
            Ls = list(L)
            for i in range(len(Ls)):
                if Ls[i] != " " and random.random() < intensity:
                    Ls[i] = random.choice(chars)
            new_lines.append("".join(Ls))
        yield "\n".join(new_lines)

def animate_glitch(full: str, use_color: bool, total: float = 0.7):
    frames = max(4, int(total / 0.06))
    delay = total / frames
    for f in glitch_frames(full, frames=frames, intensity=0.14):
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.write(color(f + "\n", MAGENTA, use_color))
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(color(full + "\n", GREEN, use_color))
    sys.stdout.flush()

def print_banner(use_color=True, glitch=True):
    full = render_banner(WATCHDOGS_ASCII, RETR0_ASCII, use_color)
    if glitch:
        animate_glitch(full, use_color)
    else:
        print(color(full, GREEN, use_color))

def show_help():
    help_text = """
RETR0 - mini language
Usage: retr0.py [file.retr0] [--no-color] [--no-glitch]
Commands:
  PRINT <expr>
  LET <var> = <expr>
  ASK <var> "prompt"
  REPEAT <count>
    ...
  END
  IF <expr>
    ...
  ELSE
    ...
  END
  FUNC name [params...]
    ...
  END
  CALL name [args...]
  RETURN <expr>
"""
    print(help_text)

def run_file(path: str, use_color=True, glitch=True):
    if not os.path.exists(path):
        print(color("File non trovato: " + path, RED, use_color))
        return
    with open(path, encoding="utf-8") as f:
        src = f.read()
    run_src(src, use_color, glitch)

def run_src(src: str, use_color=True, glitch=True):
    print_banner(use_color, glitch)
    try:
        instrs, consts = compile_source(src)
    except Exception as e:
        print(color("Compile error: " + str(e), RED, use_color))
        return
    print(color("\n--- Decompiled RETR0 bytecode ---\n", YELLOW, use_color))
    try:
        print(color(decompile(instrs), BOLD, use_color))
    except Exception:
        pass
    print(color("\n--- VM RUN ---\n", YELLOW, use_color))
    try:
        vm = VM(instrs, consts)
        vm.run()
    except Exception as e:
        print(color("VM error: " + str(e), RED, use_color))

def parse_args(argv):
    use_color = True
    glitch = True
    path = None
    for a in argv[1:]:
        if a in ("--no-color","--nocolor"):
            use_color = False
        elif a in ("--no-glitch","--noglitch"):
            glitch = False
        elif a in ("-h","--help"):
            show_help(); sys.exit(0)
        else:
            if path is None:
                path = a
    return path, use_color, glitch

def demo():
    src = '''
PRINT "RETR0 SYSTEM ONLINE"
LET x = 5
PRINT x
FUNC greet name
    PRINT "Hello,"
    PRINT name
END
CALL greet "World"
REPEAT 3
    PRINT "LOOP!"
END
IF 1 == 1
    PRINT "IF TRUE"
ELSE
    PRINT "IF FALSE"
END
'''
    run_src(src, use_color=True, glitch=True)

def main():
    path, use_color, glitch = parse_args(sys.argv)
    if path is None:
        demo()
    else:
        run_file(path, use_color, glitch)

if __name__ == "__main__":
    main()
