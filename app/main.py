# -*- coding: utf-8 -*-
"""应用入口: python -m app.main 或根目录 python run.py"""

import sys

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from . import config, db
from .styles import APP_QSS
from .update_dialog import UpdateDialog
from .main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setOrganizationName(config.APP_ORG)
    app.setStyleSheet(APP_QSS)

    config.ensure_data()  # 确保运行数据目录存在

    if not db.database_exists():
        # 首次运行：必须由用户导入官方免费提供的 eBird 分类表后才能进入程序
        # （eBird 分类表及演绎产物不允许随程序分发）
        setup = UpdateDialog(first_run=True)
        if setup.exec() != QDialog.Accepted:
            return 0
        if not db.database_exists():
            QMessageBox.critical(
                None,
                "导入失败",
                "未能生成数据库，程序无法启动。请重新运行后再次导入。",
            )
            return 1

    db.ensure_schema()  # 旧库补充新列（photo.sort_order 等）

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
