import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QComboBox
from PyQt6.QtCore import Qt
from database import get_monthly_category_stats, get_monthly_daily_trends, get_yearly_monthly_trends, get_detailed_budgets
import datetime

class ReportSection(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("ContentCard")
        layout = QVBoxLayout(self)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: bold; font-size: 16px; color: #1a73e8; margin-bottom: 10px;")
        layout.addWidget(lbl)
        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)

class MonthlyReportTab(QWidget):
    def __init__(self, hid=None):
        super().__init__()
        self.hid = hid
        self.year = datetime.datetime.now().year
        self.month = datetime.datetime.now().month
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Month Selector
        top_layout = QHBoxLayout()
        self.month_combo = QComboBox()
        for m in range(1, 13): self.month_combo.addItem(f"{m}월", m)
        self.month_combo.setCurrentIndex(self.month - 1)
        self.month_combo.currentIndexChanged.connect(self.on_month_changed)
        top_layout.addWidget(QLabel("분석 월:"))
        top_layout.addWidget(self.month_combo)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("ScrollContent")
        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(20)

        # 1. Summary Cards
        summary_row = QHBoxLayout()
        self.card_total_exp = ReportSection("💳 총 지출")
        self.card_budget_util = ReportSection("📉 예산 집행률")
        summary_row.addWidget(self.card_total_exp)
        summary_row.addWidget(self.card_budget_util)
        self.layout.addLayout(summary_row)

        # 2. Category Distribution (Pie Chart)
        self.cat_section = ReportSection("🍕 카테고리별 지출 비중")
        self.cat_canvas = FigureCanvas(plt.Figure(figsize=(5, 4)))
        self.cat_section.content_layout.addWidget(self.cat_canvas)
        self.layout.addWidget(self.cat_section)

        # 3. Daily Trends (Bar Chart)
        self.trend_section = ReportSection("📅 일별 지출 추이")
        self.trend_canvas = FigureCanvas(plt.Figure(figsize=(8, 4)))
        self.trend_section.content_layout.addWidget(self.trend_canvas)
        self.layout.addWidget(self.trend_section)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def on_month_changed(self):
        self.month = self.month_combo.currentData()
        self.load_data()

    def load_data(self):
        if self.hid is None: return
        
        # Stats Data
        cat_stats = get_monthly_category_stats(self.hid, self.year, self.month)
        daily_trends = get_monthly_daily_trends(self.hid, self.year, self.month)
        
        # 1. Update Cards
        total_exp = sum(row[1] for row in cat_stats)
        self.card_total_exp.content_layout.addWidget(QLabel(f"<h2 style='color:#d93025'>{total_exp:,} 원</h2>"))
        
        # 2. Pie Chart
        self.cat_canvas.figure.clear()
        if cat_stats:
            ax = self.cat_canvas.figure.add_subplot(111)
            labels = [row[0] for row in cat_stats]
            sizes = [row[1] for row in cat_stats]
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=plt.cm.Pastel1.colors)
            ax.set_title(f"{self.month}월 지출 분포")
        self.cat_canvas.draw()

        # 3. Bar Chart
        self.trend_canvas.figure.clear()
        if daily_trends:
            ax = self.trend_canvas.figure.add_subplot(111)
            days = [int(r[0]) for r in daily_trends]
            amts = [r[1] for r in daily_trends]
            ax.bar(days, amts, color='#8ab4f8')
            ax.set_xlabel("일 (Day)")
            ax.set_ylabel("지출액")
            ax.set_xticks(range(1, 32, 2))
        self.trend_canvas.draw()

class YearlyReportTab(QWidget):
    def __init__(self, hid=None):
        super().__init__()
        self.hid = hid
        self.year = datetime.datetime.now().year
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("ScrollContent")
        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(20)

        # 1. Yearly Monthly Trend (Line Chart)
        self.trend_section = ReportSection(f"📈 {self.year}년 수입/지출 추이")
        self.trend_canvas = FigureCanvas(plt.Figure(figsize=(10, 5)))
        self.trend_section.content_layout.addWidget(self.trend_canvas)
        self.layout.addWidget(self.trend_section)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def load_data(self):
        if self.hid is None: return
        
        trends = get_yearly_monthly_trends(self.hid, self.year)
        
        self.trend_canvas.figure.clear()
        ax = self.trend_canvas.figure.add_subplot(111)
        months = sorted(trends.keys())
        inc_data = [trends[m]["수입"] for m in months]
        exp_data = [trends[m]["지출"] for m in months]
        
        ax.plot(months, inc_data, marker='o', label='수입', color='#1a73e8', linewidth=2)
        ax.plot(months, exp_data, marker='o', label='지출', color='#d93025', linewidth=2)
        ax.fill_between(months, inc_data, alpha=0.1, color='#1a73e8')
        ax.fill_between(months, exp_data, alpha=0.1, color='#d93025')
        ax.legend()
        ax.set_title(f"{self.year}년 재정 흐름")
        ax.grid(True, linestyle='--', alpha=0.5)
        self.trend_canvas.draw()
