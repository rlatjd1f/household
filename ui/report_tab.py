import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import FuncFormatter
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                             QScrollArea, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QTextBrowser, QApplication, QSizePolicy, QAbstractItemView)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from database import (get_monthly_category_stats, get_monthly_daily_trends, 
                      get_yearly_monthly_trends, get_detailed_budgets, get_ledger_entries)
import datetime
import platform

# --- Helper for Comma Formatting on Axes ---
def comma_formatter(x, pos):
    return f'{int(x):,}'

# --- Font Setup for Korean ---
plt.rcParams['axes.unicode_minus'] = False
if platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
elif platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'

CHART_NUMBER_FONT_SIZE = 9
CHART_TITLE_FONT_SIZE = 12
CHART_LEGEND_FONT_SIZE = 9
plt.rcParams['xtick.labelsize'] = CHART_NUMBER_FONT_SIZE
plt.rcParams['ytick.labelsize'] = CHART_NUMBER_FONT_SIZE
plt.rcParams['legend.fontsize'] = CHART_LEGEND_FONT_SIZE


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
        self.month_buttons = []
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # 12-Month Button Bar
        top_ctrl = QHBoxLayout()
        top_ctrl.setSpacing(8)
        top_ctrl.addWidget(QLabel("📅 분석 월 선택:"))
        
        for m in range(1, 13):
            btn = QPushButton(f"{m}월")
            btn.setObjectName("MonthBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if m == self.month:
                btn.setProperty("active", True)
                btn.setChecked(True)
            else:
                btn.setProperty("active", False)
            
            btn.clicked.connect(lambda chk, month=m: self.on_month_btn_clicked(month))
            top_ctrl.addWidget(btn)
            self.month_buttons.append(btn)
            
        top_ctrl.addStretch()
        main_layout.addLayout(top_ctrl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("ScrollContent")
        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(20)

        # 1. KPI Dash Area
        kpi_layout = QHBoxLayout()
        self.card_variable = ReportSection("⚠️ 변동비 집중 모니터링")
        self.card_budget = ReportSection("📉 예산 집행률 디테일")
        kpi_layout.addWidget(self.card_variable)
        kpi_layout.addWidget(self.card_budget)
        self.layout.addLayout(kpi_layout)

        # 2. Center Area: Category Chart + Top Spend Table
        center_layout = QHBoxLayout()
        self.chart_section = ReportSection("📊 카테고리별 지출 현황")
        self.cat_canvas = FigureCanvas(plt.Figure(figsize=(7, 5), tight_layout=True))
        self.chart_section.content_layout.addWidget(self.cat_canvas)
        
        self.table_section = ReportSection("✨ 이달의 주요 소비처 (Top 10)")
        self.top_table = QTableWidget(0, 5)
        self.top_table.setHorizontalHeaderLabels(["날짜", "카테고리", "사용처", "결제수단", "금액"])
        self.top_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.top_table.verticalHeader().setVisible(False)
        self.top_table.setStyleSheet("font-size: 11px;")
        self.table_section.content_layout.addWidget(self.top_table)
        
        center_layout.addWidget(self.chart_section, 4)
        center_layout.addWidget(self.table_section, 3)
        self.layout.addLayout(center_layout)

        # 3. Bottom Area: Daily Line Chart + AI Insights
        bottom_layout = QHBoxLayout()
        self.daily_section = ReportSection("📅 일별 지출 추이")
        self.daily_canvas = FigureCanvas(plt.Figure(figsize=(8, 4), tight_layout=True))
        self.daily_section.content_layout.addWidget(self.daily_canvas)
        
        self.insight_section = ReportSection("💡 소비 패턴 분석 인사이트")
        self.insight_text = QTextBrowser()
        self.insight_text.setStyleSheet("background: transparent; border: none;")
        self.insight_section.content_layout.addWidget(self.insight_text)
        
        bottom_layout.addWidget(self.daily_section, 5)
        bottom_layout.addWidget(self.insight_section, 3)
        self.layout.addLayout(bottom_layout)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def on_month_btn_clicked(self, selected_month):
        self.month = selected_month
        # Update button states
        for i, btn in enumerate(self.month_buttons):
            is_active = (i + 1 == selected_month)
            btn.setProperty("active", is_active)
            btn.setChecked(is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.load_data()

    def style_axes(self, ax, format_x=True, format_y=True):
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#dadce0')
        ax.spines['bottom'].set_color('#dadce0')
        ax.tick_params(axis='both', colors='#5f6368', labelsize=CHART_NUMBER_FONT_SIZE)
        ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#e8eaed')
        ax.set_axisbelow(True)
        ax.set_facecolor('none')
        if format_y: ax.yaxis.set_major_formatter(FuncFormatter(comma_formatter))
        if format_x: ax.xaxis.set_major_formatter(FuncFormatter(comma_formatter))

    def is_dark(self):
        return "background-color: #202124" in (QApplication.instance().styleSheet() or "")

    def load_data(self):
        if self.hid is None: return
        cat_stats = sorted(get_monthly_category_stats(self.hid, self.year, self.month), key=lambda x: x[1], reverse=True)
        daily_trends = get_monthly_daily_trends(self.hid, self.year, self.month)
        ledger_entries = get_ledger_entries(self.hid, self.year, self.month)
        
        # 1. KPI Cards
        fixed_cats = ["고정지출(주거)", "이자", "월세", "상환"]
        total_fixed = sum(r[1] for r in cat_stats if r[0] in fixed_cats)
        total_var = sum(r[1] for r in cat_stats if r[0] not in fixed_cats)
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

        # 2. Category Chart
        self.cat_canvas.figure.clear()
        if cat_stats:
            ax = self.cat_canvas.figure.add_subplot(111)
            self.style_axes(ax, format_x=False, format_y=True)
            labels = [row[0] for row in cat_stats]
            values = [row[1] for row in cat_stats]
            bars = ax.bar(labels, values, color='#1a73e8', width=0.6, alpha=0.9)
            ax.set_title(f"{self.month}월 항목별 지출", pad=15, fontweight='bold', color='#202124')
            plt.setp(ax.get_xticklabels(), rotation=0) 
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height):,}', ha='center', va='bottom', fontsize=CHART_NUMBER_FONT_SIZE, color='#1a73e8', fontweight='bold')
            ax.yaxis.grid(True, linestyle='--', alpha=0.3)
            ax.xaxis.grid(False)
        self.cat_canvas.draw()

        # 3. Top Table
        self.top_table.setRowCount(0)
        expense_entries = [e for e in ledger_entries if e[2] == "지출"]
        top_10 = sorted(expense_entries, key=lambda x: x[5], reverse=True)[:10]
        for e in top_10:
            row = self.top_table.rowCount(); self.top_table.insertRow(row)
            self.top_table.setItem(row, 0, QTableWidgetItem(e[1]))
            self.top_table.setItem(row, 1, QTableWidgetItem(f"{e[9]}>{e[10]}"))
            self.top_table.setItem(row, 2, QTableWidgetItem(e[7]))
            self.top_table.setItem(row, 3, QTableWidgetItem(e[8]))
            self.top_table.setItem(row, 4, QTableWidgetItem(format(e[5], ',')))

        # 4. Daily Trend
        self.daily_canvas.figure.clear()
        if daily_trends:
            ax = self.daily_canvas.figure.add_subplot(111)
            self.style_axes(ax, format_x=False, format_y=True)
            days = [int(r[0]) for r in daily_trends]
            amts = [r[1] for r in daily_trends]
            ax.plot(days, amts, color='#1a73e8', marker='o', markersize=4, linewidth=2)
            ax.fill_between(days, amts, alpha=0.1, color='#1a73e8')
            ax.set_xticks(range(1, 32, 5))
        self.daily_canvas.draw()

        self.generate_insights(total_exp, total_var, top_10, daily_trends)

    def generate_insights(self, total, var, top_10, trends):
        text_color = "#e8eaed" if self.is_dark() else "#3c4043"
        html = f"<div style='line-height:160%; font-size:14px; color:{text_color};'>"
        if not top_10:
            html += "<p>데이터가 부족하여 분석을 진행할 수 없습니다.</p>"
        else:
            max_item = top_10[0]
            html += f"<p>📍 지출이 가장 컸던 날은 <b>{max_item[1]}</b>이며, <b>{max_item[7]}</b>에서 {max_item[5]:,}원을 지출하셨습니다.</p>"
            if trends:
                peak_day = sorted(trends, key=lambda x: x[1], reverse=True)[0]
                html += f"<p>📅 {self.month}월 {peak_day[0]}일에 지출 피크가 발생했습니다. 해당 일의 소비 내역을 점검해 보세요.</p>"
            var_ratio = (var / total * 100) if total > 0 else 0
            if var_ratio > 50: html += f"<p style='color:#d93025;'>⚠️ 변동비 비중이 {var_ratio:.1f}%로 높습니다. 불필요한 쇼핑이나 외식이 없었는지 확인이 필요합니다.</p>"
            else: html += "<p style='color:#1a73e8;'>✅ 변동비가 잘 통제되고 있습니다. 지금처럼 유지해 주세요!</p>"
        html += "</div>"
        self.insight_text.setHtml(html)

class YearlyReportTab(QWidget):
    def __init__(self, hid=None):
        super().__init__()
        self.hid = hid; self.year = datetime.datetime.now().year
        self.init_ui(); self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(); content.setObjectName("ScrollContent"); self.layout = QVBoxLayout(content); self.layout.setSpacing(20); self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)
        self.kpi_cards = {
            "income": self.create_kpi_card("연간 수입", "#1a73e8"),
            "expense": self.create_kpi_card("연간 지출", "#d93025"),
            "net": self.create_kpi_card("순저축", "#188038"),
            "avg_expense": self.create_kpi_card("평균 월지출", "#5f6368"),
        }
        for card in self.kpi_cards.values():
            kpi_layout.addWidget(card["frame"])
        self.layout.addLayout(kpi_layout)

        self.trend_section = ReportSection(f"📈 {self.year}년 수입/지출 추이")
        self.trend_section.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.trend_canvas = FigureCanvas(plt.Figure(figsize=(10, 5), tight_layout=True))
        self.trend_canvas.setMinimumHeight(460)
        self.trend_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.trend_section.content_layout.addWidget(self.trend_canvas); self.layout.addWidget(self.trend_section)

        detail_layout = QHBoxLayout()
        detail_layout.setSpacing(15)

        self.monthly_section = ReportSection("📋 월별 요약")
        self.monthly_table = QTableWidget(0, 4)
        self.monthly_table.setHorizontalHeaderLabels(["월", "수입", "지출", "차액"])
        self.monthly_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.monthly_table.verticalHeader().setVisible(False)
        self.monthly_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.monthly_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.monthly_section.content_layout.addWidget(self.monthly_table)

        self.top_category_section = ReportSection("🏆 연간 지출 Top 5")
        self.top_category_table = QTableWidget(0, 3)
        self.top_category_table.setHorizontalHeaderLabels(["순위", "분류", "금액"])
        self.top_category_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.top_category_table.verticalHeader().setVisible(False)
        self.top_category_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.top_category_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.top_category_section.content_layout.addWidget(self.top_category_table)

        self.insight_section = ReportSection("💡 연간 인사이트")
        self.insight_text = QTextBrowser()
        self.insight_text.setStyleSheet("background: transparent; border: none;")
        self.insight_section.content_layout.addWidget(self.insight_text)

        detail_layout.addWidget(self.monthly_section, 5)
        detail_layout.addWidget(self.top_category_section, 3)
        detail_layout.addWidget(self.insight_section, 4)
        self.layout.addLayout(detail_layout)

        self.layout.addStretch()
        scroll.setWidget(content); main_layout.addWidget(scroll)

    def create_kpi_card(self, title, color):
        frame = QFrame()
        frame.setObjectName("ContentCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; color: #5f6368;")
        value_label = QLabel("0원")
        value_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")
        sub_label = QLabel("")
        sub_label.setStyleSheet("font-size: 12px; color: #5f6368;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(sub_label)
        return {"frame": frame, "value": value_label, "sub": sub_label}

    def update_kpi_card(self, key, value, sub_text=""):
        self.kpi_cards[key]["value"].setText(value)
        self.kpi_cards[key]["sub"].setText(sub_text)

    def style_axes(self, ax, format_x=False, format_y=True):
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#dadce0'); ax.spines['bottom'].set_color('#dadce0')
        ax.tick_params(axis='both', colors='#5f6368', labelsize=CHART_NUMBER_FONT_SIZE)
        if format_y: ax.yaxis.set_major_formatter(FuncFormatter(comma_formatter))
        if format_x: ax.xaxis.set_major_formatter(FuncFormatter(comma_formatter))

    def is_dark(self):
        return "background-color: #202124" in (QApplication.instance().styleSheet() or "")

    def load_data(self):
        if self.hid is None: return
        trends = get_yearly_monthly_trends(self.hid, self.year)
        months = sorted(trends.keys())
        inc_data = [trends[m].get("수입", 0) for m in months]
        exp_data = [trends[m].get("지출", 0) for m in months]
        net_data = [inc - exp for inc, exp in zip(inc_data, exp_data)]
        total_income = sum(inc_data)
        total_expense = sum(exp_data)
        total_net = total_income - total_expense
        avg_expense = total_expense // 12
        active_months = sum(1 for inc, exp in zip(inc_data, exp_data) if inc or exp)

        self.update_kpi_card("income", f"{total_income:,}원", f"입력 월 {active_months}개월")
        self.update_kpi_card("expense", f"{total_expense:,}원", f"월평균 {avg_expense:,}원")
        self.update_kpi_card("net", f"{total_net:,}원", f"저축률 {(total_net / total_income * 100) if total_income else 0:.1f}%")
        self.update_kpi_card("avg_expense", f"{avg_expense:,}원", "12개월 기준")

        self.trend_canvas.figure.clear()
        ax = self.trend_canvas.figure.add_subplot(111)
        self.style_axes(ax)
        ax.bar(months, net_data, label='순현금흐름', color=['#188038' if v >= 0 else '#d93025' for v in net_data], alpha=0.18)
        ax.plot(months, inc_data, marker='o', label='수입', color='#1a73e8', linewidth=2)
        ax.plot(months, exp_data, marker='o', label='지출', color='#d93025', linewidth=2)
        ax.fill_between(months, inc_data, alpha=0.1, color='#1a73e8')
        ax.fill_between(months, exp_data, alpha=0.1, color='#d93025')
        ax.legend(fontsize=CHART_LEGEND_FONT_SIZE); ax.set_title(f"{self.year}년 재정 흐름 (단위: 원)", pad=20, fontsize=CHART_TITLE_FONT_SIZE, fontweight='bold'); ax.grid(True, linestyle='--', alpha=0.3)
        self.trend_canvas.figure.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.12)
        self.trend_canvas.draw()

        self.monthly_table.setRowCount(0)
        for month, income, expense, net in zip(months, inc_data, exp_data, net_data):
            row = self.monthly_table.rowCount()
            self.monthly_table.insertRow(row)
            values = [f"{int(month)}월", f"{income:,}", f"{expense:,}", f"{net:,}"]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 3:
                    item.setForeground(QColor("#188038") if net >= 0 else QColor("#d93025"))
                self.monthly_table.setItem(row, col, item)

        category_totals = {}
        for month in range(1, 13):
            for entry in get_ledger_entries(self.hid, self.year, month):
                if entry[2] != "지출":
                    continue
                category = entry[9] or "미분류"
                category_totals[category] = category_totals.get(category, 0) + entry[5]

        top_categories = sorted(category_totals.items(), key=lambda item: item[1], reverse=True)[:5]
        self.top_category_table.setRowCount(0)
        for rank, (category, amount) in enumerate(top_categories, start=1):
            row = self.top_category_table.rowCount()
            self.top_category_table.insertRow(row)
            self.top_category_table.setItem(row, 0, QTableWidgetItem(str(rank)))
            self.top_category_table.setItem(row, 1, QTableWidgetItem(category))
            amount_item = QTableWidgetItem(f"{amount:,}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.top_category_table.setItem(row, 2, amount_item)

        self.update_yearly_insights(months, inc_data, exp_data, net_data, top_categories)

    def update_yearly_insights(self, months, inc_data, exp_data, net_data, top_categories):
        text_color = "#e8eaed" if "background-color: #202124" in (QApplication.instance().styleSheet() or "") else "#3c4043"
        expense_peak = max(zip(months, exp_data), key=lambda item: item[1])
        income_peak = max(zip(months, inc_data), key=lambda item: item[1])
        deficit_months = [f"{int(month)}월" for month, net in zip(months, net_data) if net < 0]
        top_category_text = f"{top_categories[0][0]} {top_categories[0][1]:,}원" if top_categories else "데이터 없음"

        html = f"""
        <div style="line-height:165%; font-size:14px; color:{text_color};">
            <p><b>가장 지출이 큰 달</b>: {int(expense_peak[0])}월 ({expense_peak[1]:,}원)</p>
            <p><b>가장 수입이 큰 달</b>: {int(income_peak[0])}월 ({income_peak[1]:,}원)</p>
            <p><b>최대 지출 분류</b>: {top_category_text}</p>
            <p><b>적자 월</b>: {', '.join(deficit_months) if deficit_months else '없음'}</p>
        </div>
        """
        self.insight_text.setHtml(html)
