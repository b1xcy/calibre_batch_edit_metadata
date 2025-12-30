#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calibre批量元数据修改插件 - 主功能模块
"""

import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QGroupBox, QListWidget,
    QListWidgetItem, QMessageBox, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QSizePolicy
)
from PyQt5.QtCore import Qt
from calibre.gui2 import error_dialog, info_dialog
from calibre_plugins.calibre_edit_metadata.plugin import (
    extract_base_title, get_all_authors, batch_update_metadata, 
    detect_and_sort_books_by_volume, preview_metadata_changes
)


class BatchEditMetadataDialog(QDialog):
    """批量编辑元数据对话框"""
    def __init__(self, gui):
        """
        初始化对话框
        :param gui: Calibre主界面
        """
        QDialog.__init__(self, gui)
        self.gui = gui
        self.db = gui.current_db
        
        # 调试模式开关
        self.debug_mode = False  # 设为 True 开启调试，False 关闭
        
        # 获取选中的书籍ID
        self.book_ids = self.get_selected_book_ids()
        
        if self.debug_mode:
            self.debug_message(f"获取到的原始书籍ID列表: {self.book_ids}")
        
        if not self.book_ids:
            self.show_error("未选中书籍", "请先选中要修改元数据的书籍")
            self.close()
            return
        
        # 初始化数据结构
        self.books_dict = {}  # key: book_id, value: metadata
        self.book_id_to_title = {}  # key: book_id, value: title
        self.valid_book_ids = []    # 有效的书籍ID（保持原始顺序）
        self.books = []             # 对应的书籍元数据对象列表
        self.titles = []            # 对应的标题列表
        
        # 批量获取元数据
        self.fetch_books_metadata()
        
        if not self.books_dict:
            self.show_error("未获取到书籍", "无法获取任何选中书籍的元数据")
            return
        
        # 整理数据，确保ID和标题的顺序一致
        self.organize_book_data()
        
        if not self.valid_book_ids:
            self.show_error("数据错误", "未能获取有效的书籍数据")
            return
        
        # 提取基础信息
        self.base_title = extract_base_title(self.titles)
        self.all_authors = get_all_authors(self.books)
        
        if self.debug_mode:
            self.debug_message(f"有效书籍数量: {len(self.valid_book_ids)}")
            for i, (book_id, title) in enumerate(zip(self.valid_book_ids, self.titles)):
                self.debug_message(f"书籍{i+1}: ID={book_id}, 标题={title}")
            self.debug_message(f"提取的基础书名: {self.base_title}")
            self.debug_message(f"提取的所有作者: {self.all_authors}")
        
        # 更新book_ids为有效的书籍ID
        self.book_ids = self.valid_book_ids
        
        # 初始化UI
        self.setup_ui()
    
    def debug_message(self, message):
        """调试信息输出"""
        if self.debug_mode:
            # 使用控制台输出，避免对话框干扰
            print(f"DEBUG: {message}", file=sys.stderr)
    
    def show_error(self, title, message):
        """显示错误信息"""
        error_dialog(self.gui, title, message, show=True)
    
    def get_selected_book_ids(self):
        """
        获取选中的书籍ID - 使用Calibre推荐的方法
        :return: 书籍ID列表，保持用户选择的顺序
        """
        selected_ids = []
        
        try:
            # 方法1：使用 Calibre 的 get_selected_ids() 方法（最推荐）
            if hasattr(self.gui, 'library_view'):
                view = self.gui.library_view
                selected_ids = list(view.get_selected_ids())
                
                if self.debug_mode:
                    self.debug_message(f"使用 get_selected_ids() 获取到的ID: {selected_ids}")
        
        except Exception as e:
            if self.debug_mode:
                self.debug_message(f"获取选中ID时出错: {str(e)}")
        return selected_ids
    
    def fetch_books_metadata(self):
        """批量获取书籍元数据"""
        for book_id in self.book_ids:
            try:
                # 使用 index_is_id=True 确保正确获取元数据
                mi = self.db.get_metadata(book_id, index_is_id=True, get_cover=False)
                
                if mi and hasattr(mi, 'title') and mi.title:
                    self.books_dict[book_id] = mi
                    self.book_id_to_title[book_id] = mi.title
                    
                    if self.debug_mode:
                        self.debug_message(f"成功获取: ID={book_id}, 标题={mi.title}")
                else:
                    if self.debug_mode:
                        self.debug_message(f"获取失败: ID={book_id}, 元数据为空")
                        
            except Exception as e:
                if self.debug_mode:
                    self.debug_message(f"错误: ID={book_id}, 异常={str(e)}")
    
    def organize_book_data(self):
        """
        整理书籍数据，确保ID、元数据和标题的顺序一致
        """
        # 使用现成的排序函数按卷号排序书籍
        sorted_books = detect_and_sort_books_by_volume(self.db, self.book_ids)
        
        # 将排序后的数据添加到正式列表
        for book_id, _ in sorted_books:
            if book_id in self.books_dict:
                mi = self.books_dict[book_id]
                title = self.book_id_to_title[book_id]
                self.valid_book_ids.append(book_id)
                self.books.append(mi)
                self.titles.append(title)
        
        # 验证数据一致性
        if self.debug_mode:
            self.debug_message(f"数据统计 - IDs: {len(self.valid_book_ids)}, "
                             f"Books: {len(self.books)}, Titles: {len(self.titles)}")
        
        # 确保三个列表长度一致
        if len(self.valid_book_ids) != len(self.books) or len(self.books) != len(self.titles):
            if self.debug_mode:
                self.debug_message("警告: 数据长度不一致，进行清理...")
            
            # 取最小长度，确保数据一致
            min_len = min(len(self.valid_book_ids), len(self.books), len(self.titles))
            
            if min_len == 0:
                if self.debug_mode:
                    self.debug_message("错误: 没有有效的数据")
                return
            
            self.valid_book_ids = self.valid_book_ids[:min_len]
            self.books = self.books[:min_len]
            self.titles = self.titles[:min_len]
            
            if self.debug_mode:
                self.debug_message(f"清理后数据长度: {min_len}")
    
    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("批量元数据修改")
        self.setMinimumWidth(500)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 书籍信息组
        info_group = QGroupBox("选中书籍信息")
        info_layout = QVBoxLayout(info_group)
        
        # 书籍列表和排序控制
        list_control_layout = QHBoxLayout()
        
        # 书籍列表
        self.books_list = QListWidget()
        # 设置选择模式为单选，方便移动
        self.books_list.setSelectionMode(QListWidget.SingleSelection)
        
        self.refresh_books_list()
        
        # 排序控制按钮
        control_layout = QVBoxLayout()
        
        # 上移按钮
        self.move_up_button = QPushButton("↑ 上移")
        self.move_up_button.clicked.connect(self.move_book_up)
        control_layout.addWidget(self.move_up_button)
        
        # 下移按钮
        self.move_down_button = QPushButton("↓ 下移")
        self.move_down_button.clicked.connect(self.move_book_down)
        control_layout.addWidget(self.move_down_button)
        
        # 拉伸空间
        control_layout.addStretch(1)
        
        # 组装布局
        list_control_layout.addWidget(self.books_list, 1)  # 书籍列表占大部分空间
        list_control_layout.addLayout(control_layout)
        
        info_layout.addLayout(list_control_layout)
        main_layout.addWidget(info_group)
        
        # 书名设置组
        title_group = QGroupBox("书名设置")
        title_layout = QVBoxLayout(title_group)
        
        # 基础书名输入
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("统一书名:"))
        self.title_edit = QLineEdit(self.base_title)
        title_row.addWidget(self.title_edit)
        title_layout.addLayout(title_row)
        main_layout.addWidget(title_group)
        
        # 作者设置组
        author_group = QGroupBox("作者设置")
        author_layout = QVBoxLayout(author_group)
        
        # 作者选择
        author_row = QHBoxLayout()
        author_row.addWidget(QLabel("统一作者:"))
        self.author_combo = QComboBox()
        self.author_combo.addItem("", "")  # 空选项
        for author in self.all_authors:
            self.author_combo.addItem(author, author)
        # 允许编辑
        self.author_combo.setEditable(True)
        author_row.addWidget(self.author_combo)
        author_layout.addLayout(author_row)
        main_layout.addWidget(author_group)
        
        # 清空选项组
        clear_group = QGroupBox("清空选项")
        clear_layout = QVBoxLayout(clear_group)
        
        # 清空标签
        self.clear_tags_check = QCheckBox("清空标签")
        self.clear_tags_check.setChecked(True)
        clear_layout.addWidget(self.clear_tags_check)
        
        # 清空丛书
        self.clear_series_check = QCheckBox("清空丛书")
        self.clear_series_check.setChecked(True)
        clear_layout.addWidget(self.clear_series_check)
        
        # 清空出版方
        self.clear_publisher_check = QCheckBox("清空出版方")
        self.clear_publisher_check.setChecked(True)
        clear_layout.addWidget(self.clear_publisher_check)
        
        main_layout.addWidget(clear_group)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 预览按钮
        self.preview_button = QPushButton("预览修改")
        self.preview_button.clicked.connect(self.preview_changes)
        button_layout.addWidget(self.preview_button)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_button)
        
        # 确认按钮
        self.ok_button = QPushButton("确认修改")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        button_layout.insertStretch(0, 1)
        main_layout.addLayout(button_layout)
        
        # 在调试模式下显示书籍ID信息
        if self.debug_mode:
            debug_label = QLabel(f"书籍ID: {self.book_ids}")
            debug_label.setStyleSheet("color: gray; font-size: 10px;")
            main_layout.addWidget(debug_label)
    
    def refresh_books_list(self):
        """
        刷新书籍列表显示
        """
        self.books_list.clear()
        for i, mi in enumerate(self.books):
            # 显示编号，便于确认顺序
            title = mi.title if hasattr(mi, 'title') else f"未知标题"
            authors = '、'.join(mi.authors) if hasattr(mi, 'authors') and mi.authors else "未知作者"
            item_text = f"{i+1}. {title} - {authors}"
            if self.debug_mode:
                item_text += f" (ID: {self.valid_book_ids[i]})"
            
            item = QListWidgetItem(item_text)
            self.books_list.addItem(item)
    
    def move_book_up(self):
        """
        上移选中的书籍
        """
        current_row = self.books_list.currentRow()
        if current_row > 0:
            # 移动书籍数据
            self.swap_book_items(current_row, current_row - 1)
            # 更新列表选择
            self.books_list.setCurrentRow(current_row - 1)
    
    def move_book_down(self):
        """
        下移选中的书籍
        """
        current_row = self.books_list.currentRow()
        if current_row < len(self.books) - 1:
            # 移动书籍数据
            self.swap_book_items(current_row, current_row + 1)
            # 更新列表选择
            self.books_list.setCurrentRow(current_row + 1)
    
    def swap_book_items(self, index1, index2):
        """
        交换两个位置的书籍数据
        :param index1: 第一个位置索引
        :param index2: 第二个位置索引
        """
        # 交换 valid_book_ids 列表
        self.valid_book_ids[index1], self.valid_book_ids[index2] = self.valid_book_ids[index2], self.valid_book_ids[index1]
        
        # 交换 books 列表
        self.books[index1], self.books[index2] = self.books[index2], self.books[index1]
        
        # 交换 titles 列表
        self.titles[index1], self.titles[index2] = self.titles[index2], self.titles[index1]
        
        # 交换 books_dict 中的顺序？不，books_dict 是按 ID 索引的，不需要交换
        
        # 刷新列表显示
        self.refresh_books_list()
        
        if self.debug_mode:
            self.debug_message(f"书籍顺序调整: {index1+1} ↔ {index2+1}")
            self.debug_message(f"调整后的书籍ID列表: {self.valid_book_ids}")
    
    def accept(self):
        """
        确认修改，执行批量更新
        """
        # 更新 book_ids 为调整后的顺序
        self.book_ids = self.valid_book_ids
        
        # 在执行前验证数据一致性
        if len(self.book_ids) != len(self.books):
            error_dialog(self.gui, "数据错误", 
                        f"书籍ID数量({len(self.book_ids)})与元数据数量({len(self.books)})不匹配",
                        show=True)
            return
        
        # 获取用户输入
        new_title_base = self.title_edit.text().strip()
        author = self.author_combo.currentText().strip()
        clear_tags = self.clear_tags_check.isChecked()
        clear_series = self.clear_series_check.isChecked()
        clear_publisher = self.clear_publisher_check.isChecked()
        
        # 验证输入
        if not new_title_base:
            QMessageBox.warning(self, "警告", "请输入统一书名")
            return
        
        if not author:
            reply = QMessageBox.question(
                self, "确认", "您没有选择或输入作者，是否继续？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        try:
            # 在调试模式下显示详细信息
            if self.debug_mode:
                print(f"\n=== 开始批量更新 ===", file=sys.stderr)
                print(f"书名模板: {new_title_base}", file=sys.stderr)
                print(f"作者: {author}", file=sys.stderr)
                print(f"清空选项: tags={clear_tags}, series={clear_series}, publisher={clear_publisher}", file=sys.stderr)
                print(f"书籍ID列表: {self.book_ids}", file=sys.stderr)
                
                # 验证每个ID对应的标题
                for i, (book_id, book) in enumerate(zip(self.book_ids, self.books)):
                    print(f"书籍{i+1}: ID={book_id}, 原标题={book.title}, "
                          f"新标题={new_title_base}{' ' + str(i+1) if i > 0 else ''}", file=sys.stderr)
            
            # 执行批量更新
            updated_count = batch_update_metadata(
                self.db,
                self.book_ids,
                new_title_base,
                author,
                clear_tags,
                clear_series,
                clear_publisher
            )
            
            # 刷新GUI - 修复了 refresh_current_selection 问题
            self.refresh_gui()
            
            # 显示成功信息
            info_dialog(self.gui, "更新完成", f"成功更新了 {updated_count} 本书的元数据", show=True)
            
        except Exception as e:
            error_dialog(self.gui, "更新失败", f"更新元数据时出错: {str(e)}", show=True)
        finally:
            # progress.close()
            self.close()
    
    def preview_changes(self):
        """
        预览元数据修改
        """
        # 获取用户输入
        new_title_base = self.title_edit.text().strip()
        author = self.author_combo.currentText().strip()
        
        # 验证输入
        if not new_title_base:
            QMessageBox.warning(self, "警告", "请输入统一书名")
            return
        
        try:            
            # 获取当前选中的书籍ID（已排序）
            book_ids = self.valid_book_ids
            
            # 调用预览函数
            previews = preview_metadata_changes(self.db, book_ids, new_title_base, author)
            
            # 显示预览窗口
            preview_window = PreviewWindow(self, previews)
            preview_window.exec_()
            
        except Exception as e:
            if self.debug_mode:
                self.debug_message(f"预览时出错: {e}")
            error_dialog(self.gui, "预览失败", f"生成预览时出错: {str(e)}", show=True)
    
    def refresh_gui(self):
        """
        刷新Calibre GUI以显示更新后的数据
        兼容不同版本的Calibre
        """
        try:
            # 方法1：使用 refresh_ids 刷新特定书籍
            if hasattr(self.gui.library_view.model(), 'refresh_ids'):
                self.gui.library_view.model().refresh_ids(self.book_ids)
            
            # 方法2：刷新当前视图
            if hasattr(self.gui.library_view, 'refresh'):
                self.gui.library_view.refresh()
            
            # 方法3：刷新整个视图模型
            if hasattr(self.gui.library_view.model(), 'resort'):
                self.gui.library_view.model().resort()
            
            # 方法4：如果有选择模型，保持选择
            if hasattr(self.gui.library_view, 'selectionModel'):
                # 重新选择相同的书籍（如果需要）
                # 这里可以选择不进行任何操作，因为用户可能不需要保持选择
                pass
            
            if self.debug_mode:
                self.debug_message("GUI刷新完成")
                
        except Exception as e:
            if self.debug_mode:
                self.debug_message(f"刷新GUI时出错: {e}")
            # 不抛出异常，因为元数据已经更新成功
            info_dialog(self.gui, "调试信息", f"刷新GUI时出错: {e}", show=True)


# 预览窗口类
class PreviewWindow(QDialog):
    def __init__(self, parent, previews):
        super().__init__(parent)
        self.previews = previews
        self.setWindowTitle("元数据修改预览")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setup_ui()
    
    def setup_ui(self):
        """
        设置预览窗口UI
        """
        main_layout = QVBoxLayout(self)
        
        # 预览表格
        self.table = QTableWidget()
        self.table.setRowCount(len(self.previews))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["序号", "原书名", "原作者", "新书名", "新作者"])
        
        # 设置表格属性
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        # 设置表格大小策略，允许扩展
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 设置列对齐方式
        # 原书名（第1列）和新书名（第3列）居中显示
        for column in [1, 3]:
            header = self.table.horizontalHeaderItem(column)
            header.setTextAlignment(Qt.AlignCenter)
        
        # 填充数据
        for i, preview in enumerate(self.previews):
            # 序号 - 居中对齐
            item = QTableWidgetItem(str(i+1))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, item)
            
            # 原书名 - 居中对齐
            old_title = preview.get('old_title', '')
            item = QTableWidgetItem(old_title)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, item)
            
            # 原作者 - 居中对齐
            old_authors = '、'.join(preview.get('old_authors', []))
            item = QTableWidgetItem(old_authors)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, item)
            
            # 新书名 - 居中对齐
            new_title = preview.get('new_title', '')
            item = QTableWidgetItem(new_title)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, item)
            
            # 新作者 - 居中对齐
            new_author = preview.get('new_author', '')
            item = QTableWidgetItem(new_author)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 4, item)
        
        # 先自动调整列宽，获取基础宽度
        self.table.resizeColumnsToContents()
        
        # 为每一列增加固定留白，避免内容挤在一起
        padding = 30  # 每列增加30px的留白
        total_width = 0
        for i in range(self.table.columnCount()):
            current_width = self.table.columnWidth(i)
            new_width = current_width + padding
            self.table.setColumnWidth(i, new_width)
            total_width += new_width
        
        # 添加到布局
        main_layout.addWidget(self.table)
        
        # 关闭按钮
        button_layout = QHBoxLayout()
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
        
        # 根据计算的总宽度调整窗口大小
        # 添加一些额外的宽度用于窗口边框和内边距
        extra_width = 10
        window_width = total_width + extra_width
        
        # 设置窗口最小高度
        min_height = max(400, 30 + len(self.previews) * 25)  # 根据行数调整最小高度
        
        # 调整窗口大小
        self.resize(window_width, min_height)