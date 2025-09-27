"""
Tkinter GUI for the Fixed-Partition Memory Allocation Simulator.
This GUI calls run_simulation() from main.py and presents metrics for
First-Fit and Best-Fit strategies.
"""

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict, Any
import main


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fixed Partition Memory Simulator")
        self.geometry("900x650")
        self._build_ui()

    def _build_ui(self):
        # Controls
        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(controls, text="Allocation Strategy:").pack(side=tk.LEFT)
        self.strategy_var = tk.StringVar(value="First Fit")
        self.strategy_combo = ttk.Combobox(controls, textvariable=self.strategy_var, state="readonly",
                                           values=["First Fit", "Best Fit"])
        self.strategy_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(controls, text="Run", command=self.run_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Run Both (Compare)", command=self.run_both).pack(side=tk.LEFT, padx=5)

        # Results area (robust layout for macOS): two frames side-by-side
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(container)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = ttk.Frame(container)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Metrics text
        ttk.Label(left, text="Metrics").pack(anchor=tk.W)
        self.metrics_text = ScrolledText(left, height=20, wrap=tk.WORD)
        self.metrics_text.pack(fill=tk.BOTH, expand=True)
        # Initial instructions so the window isn't blank
        self.metrics_text.insert(tk.END, "Choose a strategy and click 'Run', or click 'Run Both (Compare)' to compare metrics.\n")

        # Memory block visualization
        ttk.Label(left, text="Final Memory Blocks").pack(anchor=tk.W, pady=(10, 0))
        self.blocks_canvas = tk.Canvas(left, height=220, bg="#f7f7f7")
        self.blocks_canvas.pack(fill=tk.X, expand=False)

        # Explanations
        ttk.Label(right, text="Explanations (c)-(f)").pack(anchor=tk.W)
        self.explain_text = ScrolledText(right, height=30, wrap=tk.WORD)
        self.explain_text.pack(fill=tk.BOTH, expand=True)
        self._populate_explanations()

    def _populate_explanations(self):
        text = (
            "(c) FCFS conflict handling: Jobs that cannot be allocated immediately are placed in a FIFO waiting queue.\n"
            "New jobs join the tail; when a partition becomes available, the head of the queue is served first if it fits.\n\n"
            "(d) Clocks: Each running job maintains a remaining-time counter decremented per time unit.\n"
            "Wait clock per job equals the time from arrival to allocation (arrival is t=0 here).\n\n"
            "(e) Events: At t=0 and whenever a job completes (frees a partition), the allocator attempts to place waiting jobs\n"
            "according to the selected strategy.\n\n"
            "(f) Compare First-Fit vs Best-Fit by running both. Examine throughput, average/max queue length, average wait time,\n"
            "and internal fragmentation. Best-Fit often reduces internal fragmentation, while First-Fit may provide faster allocations\n"
            "depending on the workload and partition layout.\n"
        )
        self.explain_text.delete("1.0", tk.END)
        self.explain_text.insert(tk.END, text)

    def run_selected(self):
        strategy = self.strategy_var.get()
        results = main.run_simulation(strategy=strategy)
        self._show_results(results, title=f"Results: {strategy}")

    def run_both(self):
        res_ff = main.run_simulation(strategy="First Fit")
        res_bf = main.run_simulation(strategy="Best Fit")
        # Present a side-by-side textual comparison
        lines = []
        def summarize(tag: str, r: Dict[str, Any]):
            return [
                f"[{tag}] Strategy: {r['strategy']}",
                f"[{tag}] Total Time: {r['total_time']}",
                f"[{tag}] Jobs Completed: {r['jobs_completed']}",
                f"[{tag}] Throughput: {r['throughput']:.3f}",
                f"[{tag}] Avg Queue Length: {r['avg_queue_length']:.3f}",
                f"[{tag}] Max Queue Length: {r['max_queue_length']}",
                f"[{tag}] Avg Wait Time: {r['avg_wait_time']:.3f}",
                f"[{tag}] Avg Internal Fragmentation: {r['avg_internal_fragmentation']:.2f}",
                f"[{tag}] Never Used Partitions: {r['never_used_partitions_pct']:.1f}%",
                f"[{tag}] Heavily Used Partitions: {r['heavily_used_partitions_pct']:.1f}%",
                ""
            ]
        lines.extend(summarize("First-Fit", res_ff))
        lines.extend(summarize("Best-Fit", res_bf))
        self.metrics_text.delete("1.0", tk.END)
        self.metrics_text.insert(tk.END, "\n".join(lines))
        # Draw blocks from Best-Fit by default for visualization
        self._draw_blocks(res_bf['final_blocks'])

    def _show_results(self, results: Dict[str, Any], title: str):
        r = results
        text = [
            title,
            f"Total Time: {r['total_time']}",
            f"Jobs Completed: {r['jobs_completed']}",
            f"Throughput: {r['throughput']:.3f}",
            f"Avg Queue Length: {r['avg_queue_length']:.3f}",
            f"Max Queue Length: {r['max_queue_length']}",
            f"Avg Wait Time: {r['avg_wait_time']:.3f}",
            f"Avg Internal Fragmentation: {r['avg_internal_fragmentation']:.2f}",
            f"Never Used Partitions: {r['never_used_partitions_pct']:.1f}%",
            f"Heavily Used Partitions: {r['heavily_used_partitions_pct']:.1f}%",
        ]
        self.metrics_text.delete("1.0", tk.END)
        self.metrics_text.insert(tk.END, "\n".join(text))
        self._draw_blocks(r['final_blocks'])

    def _draw_blocks(self, blocks):
        self.blocks_canvas.delete("all")
        # Draw blocks in order. Color free=lightgray, occupied=tomato
        x, y = 10, 10
        w, h = 120, 60
        pad = 10
        for b in blocks:
            color = "lightgray" if b['status'] == 'free' else "tomato"
            self.blocks_canvas.create_rectangle(x, y, x + w, y + h, fill=color, outline="black")
            label = f"Block {b['block']}\nSize={b['size']}\n{b['status']}\nIF={b['internal_fragmentation']}"
            self.blocks_canvas.create_text(x + w/2, y + h/2, text=label)
            x += w + pad
            if x + w + pad > self.blocks_canvas.winfo_width():
                x = 10
                y += h + pad


if __name__ == "__main__":
    app = App()
    app.mainloop()