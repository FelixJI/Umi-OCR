# -*- coding: utf-8 -*-

PANEL_STYLESHEET = """
QWidget {
    background-color: #ffffff;
}
QCheckBox {
    spacing: 5px;
    color: #333333;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #999999;
    border-radius: 3px;
    background: #ffffff;
}
QCheckBox::indicator:hover {
    border-color: #666666;
}
QCheckBox::indicator:checked {
    background-color: #ffffff;
    border: 1px solid #333333;
    image: url(images/icons/yes.svg);
}
QCheckBox::indicator:disabled {
    border-color: #cccccc;
    background-color: #f0f0f0;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #cccccc;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 3px;
    left: 10px;
}
"""
