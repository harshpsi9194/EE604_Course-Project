"""Local target-clicking demo; measures task outcomes, not gaze accuracy/latency."""
import csv
from datetime import datetime
import math
from pathlib import Path
import random
import time
import tkinter as tk


def main():
    root = tk.Tk()
    root.title("iMouse - target practice")
    root.geometry("1000x700")
    root.configure(bg="#101827")
    label = tk.Label(root, text="iMouse target practice - press SPACE to start",
                     bg="#101827", fg="white", font=("Arial", 17))
    label.pack(pady=15)
    canvas = tk.Canvas(root, bg="#101827", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    instructions = tk.Label(root, text="Click the green target. Hold your mouth open to pause iMouse. ESC closes this window.",
                            bg="#101827", fg="#b4c3dc", font=("Arial",11))
    instructions.pack(pady=12)
    rng = random.Random(604)
    state = {"running":False, "hits":0, "misses":0, "target":(0,0), "shown":0}
    rows = []
    radius = 38
    output = Path("results") / (datetime.now().strftime("session_targets_%Y%m%d_%H%M%S_%f") + ".csv")

    def save():
        if rows:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w",newline="",encoding="utf-8") as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)

    def target():
        canvas.delete("all")
        w,h=max(canvas.winfo_width(),200),max(canvas.winfo_height(),200)
        x,y=rng.randint(60,w-60),rng.randint(60,h-60)
        state.update(target=(x,y),shown=time.perf_counter())
        canvas.create_oval(x-radius,y-radius,x+radius,y+radius,fill="#43d9a3",outline="")
        canvas.create_text(x,y,text=str(state["hits"]+1),font=("Arial",18,"bold"),fill="#101827")
        label.configure(text=f"Targets: {state['hits']}/10 | Misses: {state['misses']}")

    def start(event=None):
        if not state["running"] and state["hits"] == 0:
            state["running"] = True
            target()

    def click(event):
        if not state["running"]:
            return
        x,y=state["target"]
        hit=math.hypot(event.x-x,event.y-y) <= radius
        rows.append({"target":state["hits"]+1,"hit":int(hit),"target_x":x,"target_y":y,
                     "click_x":event.x,"click_y":event.y,
                     "seconds_since_target_shown":time.perf_counter()-state["shown"]})
        if hit:
            state["hits"] += 1
            if state["hits"] == 10:
                state["running"] = False
                save()
                canvas.delete("all")
                label.configure(text=f"Complete: 10 targets | {state['misses']} misses | Results saved")
                canvas.create_text(canvas.winfo_width()//2,canvas.winfo_height()//2,
                    text="Hands-free target practice complete",fill="#43d9a3",font=("Arial",22))
            else:
                target()
        else:
            state["misses"] += 1
            label.configure(text=f"Targets: {state['hits']}/10 | Misses: {state['misses']}")

    def close(event=None):
        save()
        root.destroy()

    canvas.bind("<Button-1>",click)
    root.bind("<space>",start)
    root.bind("<Escape>",close)
    root.protocol("WM_DELETE_WINDOW",close)
    root.mainloop()


if __name__ == "__main__":
    main()
