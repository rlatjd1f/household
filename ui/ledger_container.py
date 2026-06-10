from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from ui.ledger_tab import LedgerTab

class LedgerContainer(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        
        # Create tabs for January to December
        self.monthly_tabs = []
        for month in range(1, 13):
            tab = LedgerTab(month=month)
            self.monthly_tabs.append(tab)
            self.tabs.addTab(tab, f"{month}월")
            
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        
        # Connect tab change signal to refresh data
        self.tabs.currentChanged.connect(self.handle_tab_change)

    def handle_tab_change(self, index):
        self.monthly_tabs[index].refresh_data()

    def load_data(self):
        # Refresh current active tab
        idx = self.tabs.currentIndex()
        if idx >= 0:
            self.monthly_tabs[idx].refresh_data()
            
    def refresh_all(self):
        self.load_data()
