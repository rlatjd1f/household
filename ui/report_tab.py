import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QComboBox
from PyQt6.QtCore import Qt
from database import get_monthly_category_stats, get_monthly_daily_trends, get_yearly_monthly_trends, get_detailed_budgets
import datetime
import platform

# --- Font Setup for Korean ---
plt.rcParams['axes.unicode_minus'] = False
if platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
elif platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'

class ReportSection(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("ContentCard")
        layout = QVBoxLayout(self)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: bold; font-size: 16px; color: #1a73e8; margin-bottom: 10px;")
        layout.addWidget(lbl)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.content_widget)

    def clear_content(self):
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

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

        # 2. Category Distribution (Horizontal Bar Chart)
        self.cat_section = ReportSection("📊 카테고리별 지출 현황")
        # Increase figure height to accommodate more categories
        self.cat_canvas = FigureCanvas(plt.Figure(figsize=(8, 7), tight_layout=True))
        self.cat_section.content_layout.addWidget(self.cat_canvas)
        self.layout.addWidget(self.cat_section)

        # 3. Daily Trends (Bar Chart)
        self.trend_section = ReportSection("📈 일별 지출 추이")
        self.trend_canvas = FigureCanvas(plt.Figure(figsize=(10, 4), tight_layout=True))
        self.trend_section.content_layout.addWidget(self.trend_canvas)
        self.layout.addWidget(self.trend_section)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def style_axes(self, ax):
        """Apply Google/Material style to a Matplotlib axes object."""
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#dadce0')
        ax.spines['bottom'].set_color('#dadce0')
        ax.tick_params(axis='both', colors='#5f6368', labelsize=10)
        ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#e8eaed')
        ax.set_axisbelow(True)
        ax.set_facecolor('none')

    def on_month_changed(self):
        self.month = self.month_combo.currentData()
        self.load_data()

    def load_data(self):
        if self.hid is None: return
        cat_stats = sorted(get_monthly_category_stats(self.hid, self.year, self.month), key=lambda x: x[1])
        daily_trends = get_monthly_daily_trends(self.hid, self.year, self.month)
        
        # 1. Update Cards
        total_exp = sum(row[1] for row in cat_stats)
        self.card_total_exp.clear_content()
        self.card_total_exp.content_layout.addWidget(QLabel(f"<h1 style='color:#d93025; font-size:24px;'>{total_exp:,} 원</h1>"))
        
        budget_data = get_detailed_budgets(self.hid, self.year)
        monthly_budget = sum(c.get(self.month, 0) for c in budget_data.values())
        util_percent = (total_exp / monthly_budget * 100) if monthly_budget > 0 else 0
        util_color = "#1a73e8" if util_percent <= 100 else "#d93025"
        self.card_budget_util.clear_content()
        self.card_budget_util.content_layout.addWidget(QLabel(f"<h1 style='color:{util_color}; font-size:24px;'>{util_percent:.1f}%</h1>"))
        self.card_budget_util.content_layout.addWidget(QLabel(f"<small>(총 예산: {monthly_budget:,} 원)</small>"))

        # 2. Category Horizontal Bar Chart
        self.cat_canvas.figure.clear()
        if cat_stats:
            ax = self.cat_canvas.figure.add_subplot(111)
            self.style_axes(ax)
            labels = [row[0] for row in cat_stats]
            values = [row[1] for row in cat_stats]
            bars = ax.barh(labels, values, color='#1a73e8', height=0.6, alpha=0.9)
            ax.set_title(f"{self.month}월 항목별 지출 (단위: 원)", pad=20, fontsize=12, fontweight='bold', color='#202124')
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2, f' {int(width):,}', va='center', fontsize=9, color='#1a73e8', fontweight='bold')
            ax.xaxis.grid(True, linestyle='--', alpha=0.5, color='#e8eaed')
            ax.yaxis.grid(False)
        self.cat_canvas.draw()

        # 3. Daily Trends Bar Chart
        self.trend_canvas.figure.clear()
        if daily_trends:
            ax = self.trend_canvas.figure.add_subplot(111)
            self.style_axes(ax)
            days = [int(r[0]) for r in daily_trends]
            amts = [r[1] for r in daily_trends]
            ax.bar(days, amts, color='#8ab4f8', alpha=0.8, width=0.7)
            ax.set_title(f"{self.month}월 일별 지출 흐름", pad=20, fontsize=12, fontweight='bold', color='#202124')
            ax.set_xticks(range(1, 32, 2))
        self.trend_canvas.draw()

class YearlyReportTab(QWidget):
    def __init__(self, hid=None):
        super().__init__()
        self.hid = hid; self.year = datetime.datetime.now().year
        self.init_ui(); self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(); content.setObjectName("ScrollContent"); self.layout = QVBoxLayout(content); self.layout.setSpacing(20)
        self.trend_section = ReportSection(f"📈 {self.year}년 수입/지출 추이")
        self.trend_canvas = FigureCanvas(plt.Figure(figsize=(10, 5), tight_layout=True))
        self.trend_section.content_layout.addWidget(self.trend_canvas); self.layout.addWidget(self.trend_section)
        scroll.setWidget(content); main_layout.addWidget(scroll)

    def load_data(self):
        if self.hid is None: return
        trends = get_yearly_monthly_trends(self.hid, self.year)
        self.trend_canvas.figure.clear()
        ax = self.trend_canvas.figure.add_subplot(111)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        months = sorted(trends.keys()); inc_data = [trends[m]["수입"] for m in months]; exp_data = [trends[m]["지출"] for m in months]
        ax.plot(months, inc_data, marker='o', label='수입', color='#1a73e8', linewidth=2)
        ax.plot(months, exp_data, marker='o', label='지출', color='#d93025', linewidth=2)
        ax.fill_between(months, inc_data, alpha=0.1, color='#1a73e8')
        ax.fill_between(months, exp_data, alpha=0.1, color='#d93025')
        ax.legend(); ax.set_title(f"{self.year}년 재정 흐름", pad=20, fontsize=12, fontweight='bold'); ax.grid(True, linestyle='--', alpha=0.3)
        self.trend_canvas.draw()
