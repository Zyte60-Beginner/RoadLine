# styles.py

BASE_STYLE = """
/* Aplicação Global e Sidebar */
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
}

#Sidebar {
    background-color: #222222;
    border-top-right-radius: 15px;
    border-bottom-right-radius: 15px;
}

QPushButton.MenuButton {
    background-color: transparent;
    color: #b0b0b0;
    text-align: left;
    padding-left: 20px;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: bold;
    height: 45px;
    margin: 5px 15px;
}

QPushButton.MenuButton:hover {
    background-color: #333333;
    color: white;
}

QPushButton.MenuButton:checked {
    background-color: #4DB6AC;
    color: white;
}

/* Cards Inferiores Fixos de Ação */
QFrame.ActionCardDark { background-color: #333333; border-radius: 15px; }
QFrame.ActionCardRed { background-color: #F85A5A; border-radius: 15px; }
QFrame.ActionCardTeal { background-color: #4DB6AC; border-radius: 15px; }

QLabel.ActionCardText { color: white; font-weight: bold; font-size: 14px; }
QLabel.ActionCardSub { color: #dddddd; font-size: 10px; }
"""

DARK_THEME = BASE_STYLE + """
#MainContent {
    background-color: #121212;
}

QLabel.SectionTitle {
    font-size: 18px;
    font-weight: bold;
    color: #FFFFFF;
    margin-top: 15px;
    margin-bottom: 5px;
}

QFrame.Card {
    background-color: #1E1E1E;
    border-radius: 15px;
}

QLabel.MonitorValue {
    font-size: 24px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel.MonitorLabel {
    font-size: 12px;
    color: #AAAAAA;
}

QLabel.NormalText {
    color: #E0E0E0;
    font-size: 14px;
}

QLabel.VersionText {
    color: #555555;
    font-size: 12px;
}
"""

LIGHT_THEME = BASE_STYLE + """
#MainContent {
    background-color: #F4F5F7;
}

QLabel.SectionTitle {
    font-size: 18px;
    font-weight: bold;
    color: #000000;
    margin-top: 15px;
    margin-bottom: 5px;
}

QFrame.Card {
    background-color: #E8EAED;
    border-radius: 15px;
}

QLabel.MonitorValue {
    font-size: 24px;
    font-weight: bold;
    color: #333333;
}

QLabel.MonitorLabel {
    font-size: 12px;
    color: #666666;
}

QLabel.NormalText {
    color: #222222;
    font-size: 14px;
}

QLabel.VersionText {
    color: #999999;
    font-size: 12px;
}
"""