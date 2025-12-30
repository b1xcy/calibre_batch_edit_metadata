#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calibre批量元数据修改插件
用于批量统一书籍元数据，包括书名、作者等
"""

from calibre.customize import InterfaceActionBase

__version__ = '1.0'
__license__ = 'GPL v3'
__copyright__ = '2025, b1xcy'


class CalibreEditMetadata(InterfaceActionBase):
    """批量元数据修改插件"""
    name = '批量元数据修改'
    description = '批量统一修改书籍元数据，包括书名、作者等'
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'b1xcy'
    version = tuple(map(int, __version__.split('.')))
    minimum_calibre_version = (5, 0, 0)
    
    #: 实际插件类的位置
    actual_plugin = 'calibre_plugins.calibre_edit_metadata.ui:BatchEditMetadataAction'

    def is_customizable(self):
        """是否支持自定义配置"""
        return False

    def config_widget(self):
        """配置界面"""
        return None

    def save_settings(self, config_widget):
        """保存配置"""
        pass
