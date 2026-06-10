import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                             QScrollArea, QComboBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QTextBrowser)
from PyQt6.QtCore import Qt
from database import (get_monthly_category_stats, get_monthly_daily_trends, 
                      get_detailed_budgets, get_ledger_entries)
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
        lbl.setStyleSheet("font-weight: bold; font-size: 15px; color: #1a73e8; margin-bottom: 5px;")
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
        
        # Month Selector
        top_ctrl = QHBoxLayout()
        self.month_combo = QComboBox()
        self.month_combo.setMaxVisibleItems(12)
        for m in range(1, 13): self.month_combo.addItem(f"{m}월", m)
        self.month_combo.setCurrentIndex(self.month - 1)
        self.month_combo.currentIndexChanged.connect(self.on_month_changed)
        top_ctrl.addWidget(QLabel("📅 분석 월:"))
        top_ctrl.addWidget(self.month_combo)
        top_ctrl.addStretch()
        main_layout.addLayout(top_ctrl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("ScrollContent")
        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(20)

        # 1. KPI Dash Area (Fixed vs Variable)
        kpi_layout = QHBoxLayout()
        self.card_variable = ReportSection("⚠️ 변동비 집중 모니터링")
        self.card_budget = ReportSection("📉 예산 집행률 디테일")
        kpi_layout.addWidget(self.card_variable)
        kpi_layout.addWidget(self.card_budget)
        self.layout.addLayout(kpi_layout)

        # 2. Center Area: Category Chart + Top Spend Table
        center_layout = QHBoxLayout()
        self.chart_section = ReportSection("📊 카테고리별 지출 현황 (클릭 가능)")
        self.cat_canvas = FigureCanvas(plt.Figure(figsize=(6, 5), tight_layout=True))
        self.chart_section.content_layout.addWidget(self.cat_canvas)
        
        self.table_section = ReportSection("✨ 이달의 주요 소비처 (Top Spending)")
        self.top_table = QTableWidget(0, 5)
        self.top_table.setHorizontalHeaderLabels(["날짜", "카테고리", "사용처", "결제수단", "금액"])
        self.top_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.top_table.verticalHeader().setVisible(False)
        self.table_section.content_layout.addWidget(self.top_table)
        
        center_layout.addWidget(self.chart_section, 3)
        center_layout.addWidget(self.table_section, 4)
        self.layout.addLayout(center_layout)

        # 3. Bottom Area: Daily Line Chart + AI Insights
        bottom_layout = QHBoxLayout()
        self.daily_section = ReportSection("📅 일별 지출 추이 (Line)")
        self.daily_canvas = FigureCanvas(plt.Figure(figsize=(8, 4), tight_layout=True))
        self.daily_section.content_layout.addWidget(self.daily_canvas)
        
        self.insight_section = ReportSection("💡 소비 패턴 분석 인사이트")
        self.insight_text = QTextBrowser()
        self.insight_text.setOpenExternalLinks(True)
        self.insight_section.content_layout.addWidget(self.insight_text)
        
        bottom_layout.addWidget(self.daily_section, 5)
        bottom_layout.addWidget(self.insight_section, 3)
        self.layout.addLayout(bottom_layout)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def style_axes(self, ax):
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#dadce0')
        ax.spines['bottom'].set_color('#dadce0')
        ax.tick_params(axis='both', colors='#5f6368', labelsize=10)
        ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#e8eaed')
        ax.set_facecolor('none')

    def on_month_changed(self):
        self.month = self.month_combo.currentData()
        self.load_data()

    def load_data(self):
        if self.hid is None: return
        
        # Data Retrieval
        cat_stats = get_monthly_category_stats(self.hid, self.year, self.month)
        daily_trends = get_monthly_daily_trends(self.hid, self.year, self.month)
        ledger_entries = get_ledger_entries(self.hid, self.year, self.month)
        
        # 1. KPI Cards (Simplified Fixed vs Variable logic)
        # Assuming certain categories are fixed (Housing, Interest, etc.)
        fixed_cats = ["고정지출(주거)", "이자", "월세", "상환"]
        total_fixed = 0
        total_var = 0
        for row in cat_stats:
            if row[0] in fixed_cats: total_fixed += row[1]
            else: total_var += row[1]
        
        total_exp = total_fixed + total_var
        
        self.card_variable.clear_content()
        self.card_variable.content_layout.addWidget(QLabel(f"<span style='font-size:18px;'>이번 달 변동비 <b>{total_var:,}원</b> 지출</span>"))
        self.card_variable.content_layout.addWidget(QLabel(f"<span style='color:#5f6368;'>전체 지출 중 { (total_var/total_exp*100) if total_exp > 0 else 0:.1f}% 차지</span>"))

        budget_data = get_detailed_budgets(self.hid, self.year)
        monthly_budget = sum(c.get(self.month, 0) for c in budget_data.values())
        diff = total_exp - monthly_budget
        diff_text = f"<span style='color:#d93025;'>{diff:,}원 초과</span>" if diff > 0 else f"<span style='color:#1a73e8;'>{abs(diff):,}원 절약</span>"
        
        self.card_budget.clear_content()
        self.card_budget.content_layout.addWidget(QLabel(f"<span style='font-size:18px;'>예산 {monthly_budget:,}원 중 <b>{total_exp:,}원</b> 지출</span>"))
        self.card_budget.content_layout.addWidget(QLabel(f"결과: {diff_text}"))

        # 2. Category Chart (Horizontal Bar for labels, X: Amount, Y: Category)
        # Reverting to horizontal bar because it handles long Korean names best, but ensuring Y:Cat, X:Amt
        self.cat_canvas.figure.clear()
        if cat_stats:
            ax = self.cat_canvas.figure.add_subplot(111)
            self.style_axes(ax)
            cat_stats_sorted = sorted(cat_stats, key=lambda x: x[1])
            labels = [r[0] for r in cat_stats_sorted]
            values = [r[1] for r in cat_stats_sorted]
            
            bars = ax.barh(labels, values, color='#1a73e8', height=0.6, alpha=0.9)
            ax.set_title(f"{self.month}월 지출 분포", pad=15, fontweight='bold')
            ax.xaxis.grid(True, linestyle='--', alpha=0.3)
            ax.yaxis.grid(False)
            # Ensure labels are horizontal (matplotlib barh does this by default)
        self.cat_canvas.draw()

        # 3. Top Spending Table
        self.top_table.setRowCount(0)
        # Sort all ledger entries for this month by amount descending
        expense_entries = [e for e in ledger_entries if e[2] == "지출"]
        top_5 = sorted(expense_entries, key=lambda x: x[5], reverse=True)[:10] # Show Top 10
        for e in top_5:
            row = self.top_table.rowCount()
            self.top_table.insertRow(row)
            # data: [date, cat, payee, payment, amount]
            self.top_table.setItem(row, 0, QTableWidgetItem(e[1]))
            self.top_table.setItem(row, 1, QTableWidgetItem(f"{e[9]}>{e[10]}"))
            self.top_table.setItem(row, 2, QTableWidgetItem(e[7]))
            self.top_table.setItem(row, 3, QTableWidgetItem(e[8]))
            self.top_table.setItem(row, 4, QTableWidgetItem(format(e[5], ',')))

        # 4. Daily Line Chart
        self.daily_canvas.figure.clear()
        if daily_trends:
            ax = self.daily_canvas.figure.add_subplot(111)
            self.style_axes(ax)
            days = [int(r[0]) for r in daily_trends]
            amts = [r[1] for r in daily_trends]
            
            # Full month array for line continuity
            ax.plot(days, amts, color='#1a73e8', marker='o', markersize=4, linewidth=2)
            ax.fill_between(days, amts, alpha=0.1, color='#1a73e8')
            
            # Average Line
            avg_val = total_exp / 30 # Simple avg
            ax.axhline(avg_val, color='#d93025', linestyle='--', alpha=0.5, label='평균 지출')
            ax.legend()
            ax.set_xticks(range(1, 32, 5))
        self.daily_canvas.draw()

        # 5. AI Insights (Mock logic based on data)
        self.generate_insights(total_exp, total_var, top_5, daily_trends)

    def generate_insights(self, total, var, top_5, trends):
        html = "<div style='line-height:150%; font-size:13px; color:#3c4043;'>"
        if not top_5:
            html += "<p>데이터가 부족하여 분석을 진행할 수 없습니다.</p>"
        else:
            max_item = top_5[0]
            html += f"<p>📍 지출이 가장 컸던 날은 <b>{max_item[1]}</b>이며, <b>{max_item[7]}</b>에서 {max_item[5]:,}원을 지출하셨습니다.</p>"
            
            # Find peak day
            if trends:
                peak_day = sorted(trends, key=lambda x: x[1], reverse=True)[0]
                html += f"<p>📅 {self.month}월 {peak_day[0]}일에 지출 피크가 발생했습니다. 해당 일의 소비 내역을 점검해 보세요.</p>"
            
            var_ratio = (var / total * 100) if total > 0 else 0
            if var_ratio > 50:
                html += f"<p style='color:#d93025;'>⚠️ 변동비 비중이 {var_ratio:.1f}%로 높습니다. 불필요한 쇼핑이나 외식이 없었는지 확인이 필요합니다.</p>"
            else:
                html += "<p style='color:#1a73e8;'>✅ 변동비가 잘 통제되고 있습니다. 지금처럼 유지해 주세요!</p>"
                
        html += "</div>"
        self.insight_text.setHtml(html)

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
        self.trend_canvas = FigureCanvas(plt.Figure(figsize=(10, 5), tight_layout=True))
        self.trend_section.content_layout.addWidget(self.trend_canvas)
        self.layout.addWidget(self.trend_section)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def load_data(self):
        if self.hid is None: return
        
        trends = get_yearly_monthly_trends(self.hid, self.year)
        
        self.trend_canvas.figure.clear()
        ax = self.trend_canvas.figure.add_subplot(111)
        # Apply Material Style
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#dadce0')
        ax.spines['bottom'].set_color('#dadce0')
        ax.tick_params(axis='both', colors='#5f6368')
        
        months = sorted(trends.keys())
        inc_data = [trends[m]["수입"] for m in months]
        exp_data = [trends[m]["지출"] for m in months]
        
        ax.plot(months, inc_data, marker='o', label='수입', color='#1a73e8', linewidth=2)
        ax.plot(months, exp_data, marker='o', label='지출', color='#d93025', linewidth=2)
        ax.fill_between(months, inc_data, alpha=0.1, color='#1a73e8')
        ax.fill_between(months, exp_data, alpha=0.1, color='#d93025')
        ax.legend()
        ax.set_title(f"{self.year}년 재정 흐름 (단위: 원)", pad=20, fontsize=12, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.3)
        self.trend_canvas.draw()
