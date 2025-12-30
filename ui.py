#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calibre批量元数据修改插件 - UI界面模块
"""

from calibre.gui2.actions import InterfaceAction
from calibre_plugins.calibre_edit_metadata.main import BatchEditMetadataDialog


class BatchEditMetadataAction(InterfaceAction):
    """批量编辑元数据的界面动作"""
    name = '批量元数据修改'
    
    # 定义动作规格
    action_spec = ('批量元数据修改', None, '批量统一书籍元数据', None)
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])

    def genesis(self):
        """初始化动作"""
        # 连接信号
        self.qaction.triggered.connect(self.show_dialog)

    def show_dialog(self):
        """
        显示对话框
        """
        # 创建对话框
        d = BatchEditMetadataDialog(self.gui)
        # 只有在有选中书籍时才显示对话框
        if not hasattr(d, 'no_books_selected') or not d.no_books_selected:
            # 显示对话框
            d.exec_()

    def apply_settings(self):
        """应用设置"""
        pass