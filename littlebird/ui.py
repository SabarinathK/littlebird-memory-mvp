import sys

from .config import log


def run_tray(agent):
    """
    Runs a system tray icon with right-click menu.
    Falls back to a simple console REPL if pystray is unavailable.
    """

    try:
        import tkinter as tk
        from tkinter import messagebox, simpledialog

        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        log.warning("pystray/Pillow/tkinter not available - running in console mode")
        run_console(agent)
        return

    def make_icon():
        img = Image.new("RGB", (64, 64), color=(30, 120, 80))
        drawer = ImageDraw.Draw(img)
        drawer.ellipse([16, 16, 48, 48], fill=(255, 255, 255))
        return img

    def ask_question(icon, item):
        root = tk.Tk()
        root.withdraw()
        question = simpledialog.askstring(
            "Littlebird", "Ask about your work:", parent=root
        )
        root.destroy()
        if question:
            answer = agent.ask(question)
            response_root = tk.Tk()
            response_root.withdraw()
            messagebox.showinfo("Littlebird Answer", answer, parent=response_root)
            response_root.destroy()

    def toggle_pause(icon, item):
        if agent.paused:
            agent.resume()
            icon.title = "Littlebird (active)"
        else:
            agent.pause()
            icon.title = "Littlebird (paused)"

    def view_memory(icon, item):
        summary = agent.recent_summary()
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Recent Memory", summary)
        root.destroy()

    def quit_agent(icon, item):
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Ask a question", ask_question),
        pystray.MenuItem("Pause / Resume", toggle_pause),
        pystray.MenuItem("Recent memory", view_memory),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_agent),
    )

    icon = pystray.Icon("littlebird", make_icon(), "Littlebird (active)", menu)
    log.info("Tray icon running - right-click to interact")
    icon.run()


def run_console(agent):
    """
    Simple console REPL fallback when tray UI is unavailable.
    """

    print("\n" + "=" * 50)
    print("  Littlebird Console Mode")
    print("  Commands: ask / recent / pause / resume / quit")
    print("=" * 50 + "\n")

    while True:
        try:
            cmd = input("littlebird> ").strip().lower()
            if cmd.startswith("ask"):
                question = input("Question: ").strip()
                print("\n" + agent.ask(question) + "\n")
            elif cmd == "recent":
                print("\n" + agent.recent_summary() + "\n")
            elif cmd == "pause":
                agent.pause()
                print("Paused.")
            elif cmd == "resume":
                agent.resume()
                print("Resumed.")
            elif cmd in ("quit", "exit", "q"):
                print("Goodbye.")
                sys.exit(0)
            else:
                print("Commands: ask / recent / pause / resume / quit")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            sys.exit(0)
