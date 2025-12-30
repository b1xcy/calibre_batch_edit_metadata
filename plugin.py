#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calibre批量元数据修改插件 - 核心功能模块
"""

import re
import os
from collections import Counter
from typing import List, Dict, Tuple, Optional
import math

# 中文数字映射（扩展版）
CHINESE_NUMBERS = {
    '零': 0, '〇': 0, '一': 1, '壹': 1, '二': 2, '贰': 2, '兩': 2, '两': 2,
    '三': 3, '叁': 3, '四': 4, '肆': 4, '五': 5, '伍': 5,
    '六': 6, '陆': 6, '七': 7, '柒': 7, '八': 8, '捌': 8,
    '九': 9, '玖': 9, '十': 10, '拾': 10,
    '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
    '十六': 16, '十七': 17, '十八': 18, '十九': 19,
    '二十': 20, '廿': 20, '卅': 30, '卌': 40,
    '百': 100, '佰': 100, '千': 1000, '仟': 1000, '万': 10000, '萬': 10000,
}

# 常见的卷号关键词
VOLUME_KEYWORDS = ['卷', '冊', '册', '部', '篇', '集', '季', '期', '话', '回']


def extract_base_title(titles: List[str]) -> str:
    """
    从多个书名中提取共同的基础名称
    
    Args:
        titles: 书名列表
        
    Returns:
        提取的基础名称
    """
    if not titles:
        return ""
    
    # 1. 去除每本书名的卷号部分，得到简化标题
    simplified_titles = []
    for title in titles:
        # 提取卷号并获取简化标题
        simplified, _ = extract_volume_with_context(title)
        if simplified:
            simplified_titles.append(simplified.strip())
    
    # 如果没有成功提取到简化标题，使用原始标题
    if not simplified_titles:
        simplified_titles = titles
    
    # 2. 如果只有一个标题，直接返回
    if len(simplified_titles) == 1:
        return simplified_titles[0]
    
    # 3. 尝试找到最长公共前缀
    common_prefix = os.path.commonprefix(simplified_titles)
    if len(common_prefix) >= 3:
        # 确保公共前缀以完整词语结束
        common_prefix = trim_to_word_boundary(common_prefix)
        if len(common_prefix) >= 3:
            return common_prefix
    
    # 4. 使用最长公共子序列（LCS）算法找到更精确的公共部分
    lcs_result = find_longest_common_subsequence(simplified_titles)
    if lcs_result and len(lcs_result) >= 5:
        return lcs_result
    
    # 5. 使用词频统计找到共同词语
    common_words = find_common_words(simplified_titles)
    if common_words:
        return ' '.join(common_words)
    
    # 6. 如果所有方法都失败，返回出现频率最高的简化标题
    if simplified_titles:
        counter = Counter(simplified_titles)
        return counter.most_common(1)[0][0]
    
    return titles[0] if titles else ""


def trim_to_word_boundary(text: str) -> str:
    """修剪文本到最近的词语边界"""
    # 中文字符和常见标点
    word_boundaries = {' ', '-', '_', '·', '~', '～', ':', '：', '·', '・'}
    
    # 从末尾开始，找到第一个词语边界
    for i in range(len(text) - 1, -1, -1):
        if text[i] in word_boundaries:
            return text[:i].rstrip()
    
    return text


def find_longest_common_subsequence(titles: List[str]) -> Optional[str]:
    """寻找最长公共子序列"""
    if not titles:
        return None
    
    # 使用第一个标题作为基准
    base = titles[0]
    lcs = base
    
    for title in titles[1:]:
        lcs = longest_common_subsequence(lcs, title)
        if not lcs:
            return None
    
    return lcs if len(lcs) >= 5 else None


def longest_common_subsequence(s1: str, s2: str) -> str:
    """动态规划寻找两个字符串的最长公共子序列"""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    # 填充dp表
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    # 回溯构建LCS
    i, j = m, n
    lcs_chars = []
    
    while i > 0 and j > 0:
        if s1[i-1] == s2[j-1]:
            lcs_chars.append(s1[i-1])
            i -= 1
            j -= 1
        elif dp[i-1][j] > dp[i][j-1]:
            i -= 1
        else:
            j -= 1
    
    return ''.join(reversed(lcs_chars))


def find_common_words(titles: List[str]) -> List[str]:
    """找出所有标题中共同出现的词语"""
    if not titles:
        return []
    
    # 分割词语（中文不需要空格分割，但可以按长度分割）
    words_sets = []
    for title in titles:
        # 按非中文字符分割
        words = re.split(r'[^\u4e00-\u9fff\w]+', title)
        words = [w for w in words if len(w) >= 2]  # 只保留长度>=2的词语
        words_sets.append(set(words))
    
    # 找出共同词语
    common_words = set(words_sets[0])
    for word_set in words_sets[1:]:
        common_words &= word_set
    
    return sorted(common_words, key=len, reverse=True)


def extract_volume_with_context(title: str) -> Tuple[Optional[str], Optional[int]]:
    """
    从书名中提取卷号，并返回去除卷号后的书名
    
    Args:
        title: 原始书名
        
    Returns:
        (去除卷号后的书名, 卷号数字)
    """
    original_title = title
    
    # 模式1: 第X卷、第X册等
    pattern1 = r'第([零一二三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟萬\dIVXLCDM]+)[卷冊册部篇集季期话回](.*?)$'
    match = re.search(pattern1, title)
    if match:
        volume_str = match.group(1)
        suffix = match.group(2) or ''
        volume = parse_volume_number(volume_str)
        if volume is not None:
            base_title = title[:match.start()].rstrip(' -_·・')
            return base_title, volume
    
    # 模式2: 书名 X、书名-X、书名_X
    patterns = [
        r'[-_\s]+([零一二三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟萬\dIVXLCDM]+)[卷冊册部篇集季期话回]?$',
        r'[（\(]([零一二三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟萬\dIVXLCDM]+)[卷冊册部篇集季期话回]?[）\)]$',
        r'[【〔]([零一二三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟萬\dIVXLCDM]+)[卷冊册部篇集季期话回]?[】〕]$',
        r'v([零一二三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟萬\d]+)$',
        r'第([零一二三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟萬\d]+)部分$',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            volume_str = match.group(1)
            volume = parse_volume_number(volume_str)
            if volume is not None:
                base_title = title[:match.start()].rstrip(' -_·・')
                return base_title, volume
    
    # 模式3: 纯数字在末尾
    match = re.search(r'(\d+)$', title)
    if match and len(match.group(1)) <= 4:  # 避免年份被误识别
        volume = int(match.group(1))
        base_title = title[:match.start()].rstrip(' -_·・')
        return base_title, volume
    
    # 如果没有找到卷号，返回原始标题和None
    return original_title, None


def parse_volume_number(volume_str: str) -> Optional[int]:
    """解析各种格式的卷号数字"""
    if not volume_str:
        return None
    
    # 转换为字符串
    volume_str = str(volume_str).strip()
    
    # 1. 如果是纯阿拉伯数字
    if volume_str.isdigit():
        return int(volume_str)
    
    # 2. 如果是罗马数字
    roman_match = re.match(r'^[IVXLCDM]+$', volume_str.upper())
    if roman_match:
        try:
            return roman_to_int(roman_match.group())
        except:
            pass
    
    # 3. 如果是中文数字
    try:
        return chinese_to_int(volume_str)
    except:
        pass
    
    return None


def chinese_to_int(chinese_num: str) -> int:
    """将中文数字转换为整数"""
    if not chinese_num:
        return 0
    
    # 如果是简体中文数字字符串
    result = 0
    temp = 0
    last_unit = 1
    
    for char in chinese_num:
        if char in CHINESE_NUMBERS:
            num = CHINESE_NUMBERS[char]
            if num >= 10:  # 这是单位（十、百、千、万）
                if temp == 0:
                    temp = 1
                result += temp * num
                temp = 0
                last_unit = num
            else:  # 这是数字（零到九）
                temp = num
        else:
            # 非中文数字字符，中断解析
            break
    
    result += temp
    
    # 处理一些特殊情况，如"十一"、"二十"等
    if chinese_num in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[chinese_num]
    
    return result


def roman_to_int(roman: str) -> int:
    """将罗马数字转换为整数"""
    roman_dict = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    prev_value = 0
    
    for char in reversed(roman.upper()):
        value = roman_dict.get(char, 0)
        if value < prev_value:
            result -= value
        else:
            result += value
        prev_value = value
    
    return result


def format_volume(volume: int, format_type: str = 'number') -> str:
    """
    格式化卷号
    
    Args:
        volume: 卷号数字
        format_type: 格式类型，可选 'number'（数字格式）或 'chinese'（中文格式）
        
    Returns:
        格式化后的卷号字符串
    """
    if format_type == 'number':
        # 根据卷号大小决定格式化方式
        if volume < 10:
            return f"0{volume}"
        else:
            return str(volume)
    elif format_type == 'chinese':
        return f"第{int_to_chinese(volume)}卷"
    else:
        return str(volume)


def int_to_chinese(num: int) -> str:
    """将整数转换为中文数字"""
    if num <= 0:
        return "零"
    
    # 基本数字
    chinese_digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
    chinese_units = ['', '十', '百', '千', '万']
    
    if num < 10:
        return chinese_digits[num]
    elif num < 20:
        # 十一到十九的特殊处理
        if num == 10:
            return "十"
        else:
            return f"十{chinese_digits[num % 10]}"
    elif num < 100:
        tens = num // 10
        units = num % 10
        if units == 0:
            return f"{chinese_digits[tens]}十"
        else:
            return f"{chinese_digits[tens]}十{chinese_digits[units]}"
    else:
        # 处理更大的数字（简化版）
        return str(num)


def get_all_authors(books: List) -> List[str]:
    """
    从书籍列表中提取所有作者
    
    Args:
        books: 书籍元数据对象列表
        
    Returns:
        去重并排序后的作者列表
    """
    authors = set()
    for book in books:
        if hasattr(book, 'authors') and book.authors:
            for author in book.authors:
                # 清理作者名
                clean_author = author.strip()
                if clean_author:
                    authors.add(clean_author)
    return sorted(authors)

def batch_update_metadata(db, book_ids: List[int], new_title_base: str, author: str, 
                         clear_tags: bool = True, clear_series: bool = True, 
                         clear_publisher: bool = True, volume_format: str = 'number') -> int:
    """
    批量更新书籍元数据 - 避免对象共享的终极版本
    """
    updated_count = 0
    
    for i, book_id in enumerate(book_ids, 1):
        try:
            # **关键：每次循环都重新建立数据库连接**
            # 使用 index_is_id=True 确保正确获取
            mi = db.get_metadata(book_id, index_is_id=True, get_cover=False)
            
            if not mi:
                print(f"警告: ID={book_id} 的元数据为空")
                continue
            
            print(f"处理 {i}/{len(book_ids)}: ID={book_id}")
            
            # 构建新书名
            if volume_format == 'chinese':
                volume_suffix = f"第{int_to_chinese(i)}卷"
            else:
                total_books = len(book_ids)
                digits = 1 if total_books < 10 else 2 if total_books < 100 else 3
                volume_suffix = f"{i:0{digits}d}"
            
            new_title = f"{new_title_base}{volume_suffix}"
            
            # **创建新的元数据对象（正确的方法）**
            from calibre.ebooks.metadata.book.base import Metadata
            new_mi = Metadata(new_title)
            
            # 1. 作者处理
            if author and author.strip():
                new_mi.authors = [author.strip()]
                new_mi.sort_authors = [author.strip()]
            else:
                # 保留原作者
                if hasattr(mi, 'authors'):
                    new_mi.authors = list(mi.authors)
                if hasattr(mi, 'sort_authors'):
                    new_mi.sort_authors = list(mi.sort_authors)
            
            # 2. 排序标题处理 - 保留原排序标题或使用新标题
            if hasattr(mi, 'sort_title') and mi.sort_title:
                new_mi.sort_title = mi.sort_title
            else:
                new_mi.sort_title = new_title
            
            # 3. 其他字段
            if hasattr(mi, 'comments'):
                new_mi.comments = mi.comments
            
            # 4. 清空选项
            if clear_tags:
                new_mi.tags = []
            else:
                new_mi.tags = list(mi.tags)
            
            if clear_series:
                # 清空丛书
                new_mi.series = ""
                new_mi.series_index = ""
            else:
                new_mi.series = mi.series
                new_mi.series_index = mi.series_index
            
            if clear_publisher:
                new_mi.publisher = mi.publisher
            else:
                # 清空出版方
                new_mi.publisher = ""
            
            # 5. 复制其他重要字段
            for attr in ['identifiers', 'languages', 'pubdate', 'timestamp',
                        'last_modified', 'rating']:
                if hasattr(mi, attr):
                    value = getattr(mi, attr)
                    if isinstance(value, (list, tuple)):
                        setattr(new_mi, attr, list(value))
                    else:
                        setattr(new_mi, attr, value)
            
            # **关键：使用正确的 set_metadata 方法**
            db.set_metadata(book_id, new_mi, force_changes=True)
            updated_count += 1
            
            print(f"成功: {new_title}")
            
        except Exception as e:
            print(f"失败 ID={book_id}: {e}")
            import traceback
            traceback.print_exc()
    
    return updated_count

# 辅助函数：智能卷号检测和排序
def detect_and_sort_books_by_volume(db, book_ids: List[int]) -> List[Tuple[int, int]]:
    """
    检测书籍的卷号并排序
    
    Args:
        db: Calibre数据库对象
        book_ids: 书籍ID列表
        
    Returns:
        排序后的(book_id, volume_number)列表
    """
    books_with_volume = []
    
    for book_id in book_ids:
        try:
            mi = db.get_metadata(book_id, index_is_id=True, get_cover=False)
            if mi and hasattr(mi, 'title'):
                _, volume = extract_volume_with_context(mi.title)
                books_with_volume.append((book_id, volume or 0))
        except:
            books_with_volume.append((book_id, 0))
    
    # 按卷号排序
    books_with_volume.sort(key=lambda x: x[1])
    return books_with_volume


# 新增功能：预览更新结果
def preview_metadata_changes(db, book_ids: List[int], new_title_base: str, 
                           author: str, volume_format: str = 'number') -> List[Dict]:
    """
    预览元数据更改，而不实际修改数据库
    
    Args:
        db: Calibre数据库对象
        book_ids: 书籍ID列表
        new_title_base: 新的书名基础
        author: 统一的作者名
        volume_format: 卷号格式
        
    Returns:
        预览结果列表，包含新旧标题对比
    """
    previews = []
    
    # 直接使用传入的book_ids（已在GUI中排好序）
    books_data = []
    for book_id in book_ids:
        try:
            mi = db.get_metadata(book_id, index_is_id=True, get_cover=False)
            if mi:
                _, volume = extract_volume_with_context(mi.title)
                books_data.append({
                    'id': book_id,
                    'mi': mi,
                    'volume': volume
                })
        except:
            continue
    
    # 生成预览
    for i, book_data in enumerate(books_data, 1):
        mi = book_data['mi']
        
        # 构建新标题（不添加空格）
        if volume_format == 'chinese':
            volume_suffix = f"第{int_to_chinese(i)}卷"
        else:
            total_books = len(books_data)
            digits = math.ceil(math.log10(total_books + 1))
            volume_suffix = f"{i:0{digits}d}"
        
        new_title = f"{new_title_base}{volume_suffix}"
        
        previews.append({
            'book_id': book_data['id'],
            'old_title': mi.title,
            'new_title': new_title,
            'old_authors': mi.authors if hasattr(mi, 'authors') else [],
            'new_author': author,
            'index': i
        })
    
    return previews