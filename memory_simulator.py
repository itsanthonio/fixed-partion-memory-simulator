import sys
import copy
from queue import Queue
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                            QComboBox, QTableWidget, QTableWidgetItem, QTextEdit,
                            QListWidget, QSlider, QGroupBox, QProgressBar,
                            QSplitter, QFrame, QScrollArea)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QBrush, QPen
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class MemoryBlock(QFrame):
    def __init__(self, block_data):
        super().__init__()
        self.block_data = block_data
        self.setFixedHeight(75)  
        self.setFixedWidth(400)
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(2)
        self.update_display()
    
    def update_display(self):
        # background color based on status
        if self.block_data['status'] == 'free':
            self.setStyleSheet("""
                QFrame {
                    background-color: #90EE90;
                    border: 2px solid #228B22;
                    border-radius: 5px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #FFB6C1;
                    border: 2px solid #DC143C;
                    border-radius: 5px;
                }
            """)
        
        # Clear existing layout
        if self.layout():
            QWidget().setLayout(self.layout())
        
        layout = QVBoxLayout()
        
        # Block info 
        block_info = QLabel(f"Block {self.block_data['block']}: {self.block_data['size']:,} bytes")
        block_info.setFont(QFont("Arial", 10, QFont.Bold)) 
        block_info.setAlignment(Qt.AlignCenter)
        block_info.setStyleSheet("color: #000000; background-color: transparent;")  
        layout.addWidget(block_info)
        
        if self.block_data['status'] == 'occupied':
            job = self.block_data.get('job', {})
            job_id = job.get('stream', 'Unknown')
            job_size = job.get('size', 0)
            remaining_time = job.get('remaining_time', 0)
            job_info = QLabel(f"Job {job_id} | Size: {job_size:,}\n"
                            f"Remaining: {remaining_time} | "
                            f"Frag: {self.block_data['internal_fragmentation']:,}")
            job_info.setWordWrap(True)
            job_info.setFont(QFont("Arial", 9))  
            job_info.setAlignment(Qt.AlignCenter)
            job_info.setStyleSheet("color: #000000; background-color: transparent;")  
            layout.addWidget(job_info)
        else:
            status_info = QLabel("FREE")
            status_info.setFont(QFont("Arial", 10, QFont.Bold)) 
            status_info.setAlignment(Qt.AlignCenter)
            status_info.setStyleSheet("color: #000000; background-color: transparent;")  
            layout.addWidget(status_info)
        
        self.setLayout(layout)

class MemoryCanvas(FigureCanvas):
    def __init__(self):
        self.figure = Figure(figsize=(6, 4))  
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.setMinimumSize(400, 200)  
    
    def update_chart(self, memory_blocks, algorithm):
        self.axes.clear()
        
        blocks = [f"Block {b['block']}" for b in memory_blocks]
        used_memory = []
        fragmentation = []
        free_memory = []
        
        for block in memory_blocks:
            if block['status'] == 'occupied':
                used = block['size'] - block['internal_fragmentation']
                used_memory.append(used)
                fragmentation.append(block['internal_fragmentation'])
                free_memory.append(0)
            else:
                used_memory.append(0)
                fragmentation.append(0)
                free_memory.append(block['size'])
        
        width = 0.6
        x_pos = np.arange(len(blocks))
        
        p1 = self.axes.bar(x_pos, used_memory, width, label='Used Memory', color='#FF6B6B')
        p2 = self.axes.bar(x_pos, fragmentation, width, bottom=used_memory, label='Fragmentation', color='#FFE66D')
        p3 = self.axes.bar(x_pos, free_memory, width, label='Free Memory', color='#4ECDC4')
        
        self.axes.set_xlabel('Memory Blocks')
        self.axes.set_ylabel('Size (bytes)')
        self.axes.set_title(f'Memory Allocation - {algorithm} Algorithm')
        self.axes.set_xticks(x_pos)
        self.axes.set_xticklabels(blocks, rotation=45)
        self.axes.legend()
        self.axes.grid(True, alpha=0.3)
        
        self.axes.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.1f}K'))
        
        self.figure.tight_layout()
        self.draw()

class SimulationWorker(QThread):
    update_signal = pyqtSignal()
    finished_signal = pyqtSignal()
    
    def __init__(self, simulator):
        super().__init__()
        self.simulator = simulator
        self.running = False
        self.speed = 1.0
    
    def run(self):
        self.running = True
        while (self.running and 
               (len(self.simulator.completed_jobs) < len(self.simulator.original_jobs) or
                not self.simulator.waiting_queue.empty() or
                any(job['status'] == 'running' for job in self.simulator.jobs))):
            
            self.simulator.simulate_step()
            self.update_signal.emit()
            self.msleep(int(1000 / self.speed))
        
        self.running = False
        self.finished_signal.emit()
    
    def stop(self):
        self.running = False

class MemorySimulator:
    def __init__(self):
        from backend import MemoryAllocator
        
        # Initialize jobs with remaining time set to their total time
        self.original_jobs = [
            {'stream': 1, 'time': 5, 'size': 5760, 'arrival_time': 0, 'status': 'waiting', 'remaining_time': 5},
            {'stream': 2, 'time': 4, 'size': 4190, 'arrival_time': 1, 'status': 'waiting', 'remaining_time': 4},
            {'stream': 3, 'time': 8, 'size': 3290, 'arrival_time': 2, 'status': 'waiting', 'remaining_time': 8},
            {'stream': 4, 'time': 2, 'size': 2030, 'arrival_time': 3, 'status': 'waiting', 'remaining_time': 2},
            {'stream': 5, 'time': 2, 'size': 2550, 'arrival_time': 4, 'status': 'waiting', 'remaining_time': 2},
            {'stream': 6, 'time': 6, 'size': 6990, 'arrival_time': 5, 'status': 'waiting', 'remaining_time': 6},
            {'stream': 7, 'time': 8, 'size': 8940, 'arrival_time': 6, 'status': 'waiting', 'remaining_time': 8},
            {'stream': 8, 'time': 10, 'size': 740, 'arrival_time': 7, 'status': 'waiting', 'remaining_time': 10},
            {'stream': 9, 'time': 7, 'size': 3930, 'arrival_time': 8, 'status': 'waiting', 'remaining_time': 7},
            {'stream': 10, 'time': 6, 'size': 6890, 'arrival_time': 9, 'status': 'waiting', 'remaining_time': 6},
            {'stream': 11, 'time': 5, 'size': 6580, 'arrival_time': 10, 'status': 'waiting', 'remaining_time': 5},
            {'stream': 12, 'time': 8, 'size': 3820, 'arrival_time': 11, 'status': 'waiting', 'remaining_time': 8},
            {'stream': 13, 'time': 9, 'size': 9140, 'arrival_time': 12, 'status': 'waiting', 'remaining_time': 9},
            {'stream': 14, 'time': 10, 'size': 420, 'arrival_time': 13, 'status': 'waiting', 'remaining_time': 10},
            {'stream': 15, 'time': 10, 'size': 220, 'arrival_time': 14, 'status': 'waiting', 'remaining_time': 10},
            {'stream': 16, 'time': 7, 'size': 7540, 'arrival_time': 15, 'status': 'waiting', 'remaining_time': 7},
            {'stream': 17, 'time': 3, 'size': 3210, 'arrival_time': 16, 'status': 'waiting', 'remaining_time': 3},
            {'stream': 18, 'time': 1, 'size': 1380, 'arrival_time': 17, 'status': 'waiting', 'remaining_time': 1},
            {'stream': 19, 'time': 9, 'size': 9850, 'arrival_time': 18, 'status': 'waiting', 'remaining_time': 9},
            {'stream': 20, 'time': 3, 'size': 3610, 'arrival_time': 19, 'status': 'waiting', 'remaining_time': 3},
            {'stream': 21, 'time': 7, 'size': 7540, 'arrival_time': 20, 'status': 'waiting', 'remaining_time': 7},
            {'stream': 22, 'time': 2, 'size': 2710, 'arrival_time': 21, 'status': 'waiting', 'remaining_time': 2},
            {'stream': 23, 'time': 8, 'size': 8390, 'arrival_time': 22, 'status': 'waiting', 'remaining_time': 8},
            {'stream': 24, 'time': 5, 'size': 5950, 'arrival_time': 23, 'status': 'waiting', 'remaining_time': 5},
            {'stream': 25, 'time': 10, 'size': 760, 'arrival_time': 24, 'status': 'waiting', 'remaining_time': 10},
        ]
        
        self.original_memory = [
            {'block': 1, 'size': 9500, 'status': 'free', 'job': None, 'internal_fragmentation': 0},
            {'block': 2, 'size': 7000, 'status': 'free', 'job': None, 'internal_fragmentation': 0},
            {'block': 3, 'size': 4500, 'status': 'free', 'job': None, 'internal_fragmentation': 0},
            {'block': 4, 'size': 8500, 'status': 'free', 'job': None, 'internal_fragmentation': 0},
            {'block': 5, 'size': 3000, 'status': 'free', 'job': None, 'internal_fragmentation': 0},
            {'block': 6, 'size': 9000, 'status': 'free', 'job': None, 'internal_fragmentation': 0},
            {'block': 7, 'size': 1000, 'status': 'free', 'job': None, 'internal_fragmentation': 0},
            {'block': 8, 'size': 5500, 'status': 'free', 'job': None, 'internal_fragmentation': 0},
            {'block': 9, 'size': 1500, 'status': 'free', 'job': None, 'internal_fragmentation': 0},
            {'block': 10, 'size': 500, 'status': 'free', 'job': None, 'internal_fragmentation': 0}
        ]
        
        self.allocator = MemoryAllocator()
        self.reset_simulation()
    
    def reset_simulation(self):
        self.current_time = 0
        self.memory = [block.copy() for block in self.original_memory]
        # Initialize usage count for each memory block
        for block in self.memory:
            block['usage_count'] = 0
            block['job'] = None
            block['status'] = 'free'
            block['internal_fragmentation'] = 0
            
        self.jobs = [job.copy() for job in self.original_jobs]
        self.waiting_queue = Queue()
        self.completed_jobs = []
        self.running_jobs = []
        # Default strategy
        self.strategy = 'first_fit'  
        
        for job in self.jobs:
            job['status'] = 'waiting'
            job['wait_time'] = 0
            job['allocated_block'] = None
            job['remaining_time'] = job['time']
            job['last_processed'] = -1
    
    def simulate_step(self, strategy=None):
        if strategy:
            self.strategy = strategy
        
        # Update running jobs and check for completion
        completed_job_streams = set()
        for job in list(self.running_jobs):
            # Only decrement time if this is a new time unit
            if job.get('last_processed', -1) < self.current_time:
                job['remaining_time'] = max(0, job.get('remaining_time', job['time']) - 1)
                job['last_processed'] = self.current_time
                
            if job.get('remaining_time', 0) <= 0:
                # Mark job as completed
                job['status'] = 'completed'
                job['completion_time'] = self.current_time
                if job not in self.completed_jobs:
                    self.completed_jobs.append(job)
                completed_job_streams.add(job['stream'])
        
        # Remove completed jobs from running_jobs and free their memory
        self.running_jobs = [j for j in self.running_jobs if j['stream'] not in completed_job_streams]
        
        # Free memory blocks for completed jobs
        for i, block in enumerate(self.memory):
            if block['status'] == 'occupied' and block.get('job', {}).get('stream') in completed_job_streams:
                self.memory = self.allocator.deallocate_memory(self.memory, block['block'])['memory']
        
        # Process new jobs that should start at this time
        current_time_jobs = [j for j in self.jobs if j['arrival_time'] == self.current_time]
        
        for job in current_time_jobs:
            if job['status'] == 'waiting':
                # Check if job is already in running or waiting queue
                job_running = any(rj.get('stream') == job['stream'] for rj in self.running_jobs)
                job_waiting = any(wj.get('stream') == job['stream'] for wj in list(self.waiting_queue.queue))
                
                if not (job_running or job_waiting):
                    # Try to allocate memory
                    result = self.allocator.allocate_memory(self.memory, job, self.strategy)
                    if result['success']:
                        self.memory = result['memory']
                        job.update(result['job'])
                        job['remaining_time'] = job['time']
                        job['status'] = 'running'
                        job['start_time'] = self.current_time
                        job['last_processed'] = self.current_time
                        self.running_jobs.append(job)
                    else:
                        # Add to waiting queue if allocation fails
                        job['status'] = 'queued'
                        job['wait_start'] = self.current_time
                        self.waiting_queue.put(job)
        
        # Try to allocate waiting jobs
        temp_queue = Queue()
        while not self.waiting_queue.empty():
            job = self.waiting_queue.get()
            result = self.allocator.allocate_memory(self.memory, job, self.strategy)
            if result['success']:
                self.memory = result['memory']
                job.update(result['job'])
                job['remaining_time'] = job['time']
                job['status'] = 'running'
                job['start_time'] = self.current_time
                job['last_processed'] = self.current_time
                self.running_jobs.append(job)
            else:
                temp_queue.put(job)
        
        # Put back jobs that couldn't be allocated
        while not temp_queue.empty():
            job = temp_queue.get()
            job['wait_time'] = self.current_time - job.get('wait_start', job['arrival_time'])
            self.waiting_queue.put(job)
        
        # Update wait times for queued jobs
        temp_queue = Queue()
        while not self.waiting_queue.empty():
            job = self.waiting_queue.get()
            job['wait_time'] = self.current_time - job.get('wait_start', job['arrival_time'])
            temp_queue.put(job)
        
        # Put jobs back in the queue
        while not temp_queue.empty():
            self.waiting_queue.put(temp_queue.get())
        
        self.current_time += 1
    
    
    def first_fit_allocate(self, job):
        result = self.allocator.allocate_memory(self.memory, job, 'first_fit')
        if result['success']:
            self.memory = result['memory']
            job.update(result['job'])
            job['status'] = 'running'
            job['start_time'] = self.current_time
            job['remaining_time'] = job['time']
            if job in self.jobs:
                self.jobs.remove(job)
            if job in self.waiting_queue:
                self.waiting_queue.remove(job)
            if 'running_jobs' not in self.__dict__:
                self.running_jobs = []
            self.running_jobs.append(job)
            return True
        return False
    
    def best_fit_allocate(self, job):
        result = self.allocator.allocate_memory(self.memory, job, 'best_fit')
        if result['success']:
            self.memory = result['memory']
            job.update(result['job'])
            job['status'] = 'running'
            job['start_time'] = self.current_time
            job['remaining_time'] = job['time']
            if job in self.jobs:
                self.jobs.remove(job)
            if job in self.waiting_queue:
                self.waiting_queue.remove(job)
            if 'running_jobs' not in self.__dict__:
                self.running_jobs = []
            self.running_jobs.append(job)
            return True
        return False
    
    def allocate_memory(self, job, block):
        if not hasattr(self, 'strategy'):
            self.strategy = 'first_fit'  
            
        result = self.allocator.allocate_memory(self.memory, job, self.strategy)
        if result['success']:
            self.memory = result['memory']
            job.update(result['job'])
            job['status'] = 'running'
            job['start_time'] = self.current_time
            job['remaining_time'] = job['time']
            if job in self.jobs:
                self.jobs.remove(job)
            if hasattr(self, 'waiting_queue') and job in self.waiting_queue:
                self.waiting_queue.remove(job)
            if 'running_jobs' not in self.__dict__:
                self.running_jobs = []
            self.running_jobs.append(job)
    
    def free_memory_block(self, block):
        if block['status'] == 'occupied':
            result = self.allocator.deallocate_memory(self.memory, block['block'])
            if result['success']:
                self.memory = result['memory']
                job = result['job']
                if job:
                    job['status'] = 'completed'
                    job['end_time'] = self.current_time
                    if 'completed_jobs' not in self.__dict__:
                        self.completed_jobs = []
                    self.completed_jobs.append(job)
                    if hasattr(self, 'running_jobs') and job in self.running_jobs:
                        self.running_jobs.remove(job)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.simulator = MemorySimulator()
        self.worker = None
        self.memory_blocks_widgets = []
        self.init_ui()
        self.update_display()
    
    def init_ui(self):
        self.setWindowTitle("Fixed Partition Memory Management Simulator")
        self.setGeometry(100, 100, 1600, 1000)  
        
       
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Controls and Memory Visualization
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        # Control panel
        self.create_control_panel(left_layout)
        
        # Memory visualization
        self.create_memory_panel(left_layout)
        
        # Right panel - Information and Statistics
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # Information panels
        self.create_info_panels(right_layout)
        
        # Job table
        self.create_job_table(right_layout)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([490, 910])  
    
    def create_control_panel(self, layout):
        control_group = QGroupBox("Simulation Controls")
        control_layout = QGridLayout()
        
        # Algorithm selection
        control_layout.addWidget(QLabel("Algorithm:"), 0, 0)
        
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["First Fit", "Best Fit"])
        control_layout.addWidget(self.algorithm_combo, 0, 1)
        

        self.start_btn = QPushButton("▶ Start")
        self.start_btn.clicked.connect(self.start_simulation)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;  
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;  
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        control_layout.addWidget(self.start_btn, 0, 2)
        
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;  
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;  
            }
            QPushButton:pressed {
                background-color: #E65100;  
            }
        """)
        control_layout.addWidget(self.pause_btn, 0, 3)
        
        self.step_btn = QPushButton("⏭ Step")
        self.step_btn.clicked.connect(self.step_simulation)
        self.step_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; 
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;  
            }
            QPushButton:pressed {
                background-color: #1565C0;  
            }
        """)
        control_layout.addWidget(self.step_btn, 1, 0)
        
        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.clicked.connect(self.reset_simulation)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;  
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #D32F2F;  
            }
            QPushButton:pressed {
                background-color: #C62828;  
            }
        """)
        control_layout.addWidget(self.reset_btn, 1, 1)
        
        # Speed control
        control_layout.addWidget(QLabel("Speed:"), 1, 2)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 30)
        self.speed_slider.setValue(10)
        control_layout.addWidget(self.speed_slider, 1, 3)
        
        # Current time display
        self.time_label = QLabel("Current Time: 0")
        self.time_label.setFont(QFont("Arial", 12, QFont.Bold))
        control_layout.addWidget(self.time_label, 2, 0, 1, 4)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
    
    def create_memory_panel(self, layout):
        memory_group = QGroupBox("Memory Block Visualization")
        memory_layout = QVBoxLayout()
        
        #  scroll area for memory blocks 
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(3) 
        
        #  memory block widgets
        for i, block in enumerate(self.simulator.memory):
            block_widget = MemoryBlock(block)
            self.memory_blocks_widgets.append(block_widget)
            scroll_layout.addWidget(block_widget)
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(600) 
        memory_layout.addWidget(scroll_area)
        memory_group.setLayout(memory_layout)
        layout.addWidget(memory_group)
    
    def create_info_panels(self, layout):
        # create vertical splitter for right panel organization
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.setContentsMargins(0, 0, 0, 0)  
        
        # waiting queue and performance metrics side by side
        top_section = QWidget()
        top_layout = QHBoxLayout()  
        top_layout.setSpacing(5)  
        top_layout.setContentsMargins(0, 0, 0, 0) 
        top_section.setLayout(top_layout)
        
        # waiting queue
        queue_group = QGroupBox("Waiting Queue")
        queue_layout = QVBoxLayout()
        
        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(220)
        queue_layout.addWidget(self.queue_list)
        
        queue_group.setLayout(queue_layout)
        top_layout.addWidget(queue_group)
        
        # performance metrics
        stats_group = QGroupBox("Performance Metrics")
        stats_layout = QVBoxLayout()
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(220)  
        self.stats_text.setFont(QFont("Courier", 9))
        stats_layout.addWidget(self.stats_text)
        
        stats_group.setLayout(stats_layout)
        top_layout.addWidget(stats_group)
        
        # bottom section-chart
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)  
        bottom_section.setLayout(bottom_layout)
        
        chart_group = QGroupBox("Memory Allocation Chart")
        chart_group.setMaximumHeight(300)
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(0)  
        
        self.memory_chart = MemoryCanvas()
        self.memory_chart.setMaximumHeight(280)
        chart_layout.addWidget(self.memory_chart)
        
        chart_group.setLayout(chart_layout)
        chart_group.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(chart_group)
        
        v_splitter.addWidget(top_section)
        v_splitter.addWidget(bottom_section)
        v_splitter.setSizes([280, 420])
        
        layout.addWidget(v_splitter)
    
    def create_job_table(self, layout):
        jobs_group = QGroupBox("Job Status")
        jobs_layout = QVBoxLayout()
        jobs_layout.setContentsMargins(0, 0, 0, 0)  
        
        self.job_table = QTableWidget()
        self.job_table.setColumnCount(7)
        self.job_table.setHorizontalHeaderLabels([
            "Job", "Size", "Time", "Status", "Block", "Wait Time", "Arrival"
        ])
        self.job_table.setRowCount(len(self.simulator.jobs))
        self.job_table.setMaximumHeight(450)
        
        jobs_layout.addWidget(self.job_table)
        jobs_group.setLayout(jobs_layout)
        layout.addWidget(jobs_group)
    
    def start_simulation(self):
        if self.worker is None or not self.worker.isRunning():
            self.simulator.algorithm = self.algorithm_combo.currentText()
            self.worker = SimulationWorker(self.simulator)
            self.worker.speed = self.speed_slider.value() / 10.0
            self.worker.update_signal.connect(self.update_display)
            self.worker.finished_signal.connect(self.simulation_finished)
            self.worker.start()
            
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
    
    def pause_simulation(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
    
    def step_simulation(self):
        self.simulator.algorithm = self.algorithm_combo.currentText()
        self.simulator.simulate_step()
        self.update_display()
    
    def reset_simulation(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        
        self.simulator.reset_simulation()
        self.update_display()
        
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
    
    def simulation_finished(self):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
    
    def update_display(self):
        # Update time
        self.time_label.setText(f"Current Time: {self.simulator.current_time}")
        
        # Update memory blocks
        for i, widget in enumerate(self.memory_blocks_widgets):
            widget.block_data = self.simulator.memory[i]
            widget.update_display()
        
        # Update memory chart
        algorithm = self.algorithm_combo.currentText()
        self.memory_chart.update_chart(self.simulator.memory, algorithm)
        
        # Update waiting queue
        self.queue_list.clear()
        temp_queue = Queue()
        while not self.simulator.waiting_queue.empty():
            job = self.simulator.waiting_queue.get()
            self.queue_list.addItem(f"Job {job['stream']} - Size: {job['size']:,} - Wait: {job['wait_time']}")
            temp_queue.put(job)
        
        while not temp_queue.empty():
            self.simulator.waiting_queue.put(temp_queue.get())
        
    
        self.update_statistics()
        
       
        self.update_job_table()
    
    def update_statistics(self):
        total_jobs = len(self.simulator.original_jobs)
        completed = len({job['stream']: job for job in self.simulator.completed_jobs})
        running = sum(1 for job in self.simulator.jobs if job['status'] == 'running')
    
        waiting_jobs = set()
        temp_queue = Queue()
        while not self.simulator.waiting_queue.empty():
            job = self.simulator.waiting_queue.get()
            waiting_jobs.add(job['stream'])
            temp_queue.put(job)
        
       
        while not temp_queue.empty():
            self.simulator.waiting_queue.put(temp_queue.get())
            
        waiting = len(waiting_jobs)
        
        total_memory = sum(block['size'] for block in self.simulator.memory)
        used_memory = sum(block['size'] - block['internal_fragmentation'] 
                         for block in self.simulator.memory if block['status'] == 'occupied')
        
        total_fragmentation = sum(block['internal_fragmentation'] for block in self.simulator.memory)
        
        # Calculate average wait time for completed jobs 
        unique_completed = {}
        for job in self.simulator.completed_jobs:
            if job['stream'] not in unique_completed:
                unique_completed[job['stream']] = job['wait_time']
        
        avg_wait_time = (sum(unique_completed.values()) / 
                        len(unique_completed)) if unique_completed else 0
        
        throughput = completed / max(self.simulator.current_time, 1)
        memory_utilization = (used_memory / total_memory) * 100 if total_memory > 0 else 0
        fragmentation_percentage = (total_fragmentation / total_memory) * 100 if total_memory > 0 else 0
        
        never_used = sum(1 for block in self.simulator.memory if block['usage_count'] == 0)
        heavily_used = sum(1 for block in self.simulator.memory if block['usage_count'] >= 3)
        
        stats_text = f"""PERFORMANCE METRICS
{'='*40}

Algorithm: {self.algorithm_combo.currentText()}
Current Time: {self.simulator.current_time}

JOB STATUS:
• Completed: {completed}/{total_jobs}
• Running: {running}
• Waiting: {waiting}

THROUGHPUT:
• Jobs/time unit: {throughput:.3f}

MEMORY UTILIZATION:
• Total Memory: {total_memory:,} bytes
• Used Memory: {used_memory:,} bytes
• Utilization: {memory_utilization:.1f}%

FRAGMENTATION:
• Total Internal: {total_fragmentation:,} bytes
• Fragmentation %: {fragmentation_percentage:.1f}%

WAITING STATISTICS:
• Queue Length: {waiting}
• Avg Wait Time: {avg_wait_time:.2f} units

PARTITION USAGE:
• Never Used: {never_used}/10 blocks
• Heavily Used (3+): {heavily_used}/10 blocks
"""
        
        self.stats_text.setPlainText(stats_text)
    
    def update_job_table(self):
        for i, job in enumerate(self.simulator.jobs):
            self.job_table.setItem(i, 0, QTableWidgetItem(str(job['stream'])))
            self.job_table.setItem(i, 1, QTableWidgetItem(f"{job['size']:,}"))
            self.job_table.setItem(i, 2, QTableWidgetItem(str(job['time'])))
            self.job_table.setItem(i, 3, QTableWidgetItem(job['status'].title()))
            self.job_table.setItem(i, 4, QTableWidgetItem(str(job.get('allocated_block', '-'))))
            self.job_table.setItem(i, 5, QTableWidgetItem(str(job['wait_time'])))
            self.job_table.setItem(i, 6, QTableWidgetItem(str(job['arrival_time'])))
            
            # Color code based on status
            if job['status'] == 'completed':
                color = QColor(212, 237, 218)  
            elif job['status'] == 'running':
                color = QColor(255, 243, 205)  
            elif job['status'] in ['waiting', 'queued']:
                color = QColor(248, 215, 218)  
            else:
                color = QColor(255, 255, 255) 
            
            for j in range(7):
                if self.job_table.item(i, j):
                    self.job_table.item(i, j).setBackground(color)

def main():
    app = QApplication(sys.argv)
    
    app.setStyle('Fusion')
   
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, Qt.black)
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

