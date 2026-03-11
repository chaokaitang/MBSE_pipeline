from docx import Document
import re

# =========================
# 1. 打开 Word 文档
# =========================
doc = Document("merged_fixed.docx")

# 最近一次确认的标题编号
last_number = None

# 已出现过的标题编号（用于去重）
seen_numbers = set()


# =========================
# 2. 判断是否是标题候选
# =========================
def is_title_candidate(text: str) -> bool:
    text = text.strip()

    # ---------- 规则 1：必须包含中文 ----------
    if not re.search(r'[\u4e00-\u9fff]', text):
        return False

    # ---------- 规则 2：排除 HTML / 表格残留 ----------
    if re.search(r'<\s*/?\s*(td|tr|table)[^>]*>', text, re.IGNORECASE):
        return False
    if '<' in text or '>' in text:
        return False

    # ---------- 规则 3：包含中英文冒号的一律不是标题 ----------
    if ':' in text or '：' in text:
        return False

    # ---------- 规则 4：必须数字开头 ----------
    if not re.match(r'^\d', text):
        return False

    # ---------- 规则 5：排除枚举项 ----------
    if re.match(r'^\d+\s*[)\]]', text):
        return False

    # ---------- 规则 6：排除明显正文 ----------
    if len(text) > 60:
        return False
    if text.endswith(('。', '.', ';')):
        return False

    # ---------- 情况 A：多级标题（含小数点） ----------
    if '.' in text:
        return True

    # ---------- 情况 B：一级标题（无小数点） ----------
    # 允许：
    #   1范围
    #   1 范围
    #   12设备布置
    m = re.match(r'^(\d+)(\s*)(\S+)', text)
    if m:
        title_text = m.group(3)
        if len(title_text) <= 10 and len(text) <= 20:
            return True

    return False


# =========================
# 3. 提取编号
# =========================
def extract_number(text: str):
    """
    从段落开头提取编号
    返回 (number_list, rest_text)
    """
    m = re.match(r'^(\d+(?:\.\d+)*)(.*)', text)
    if not m:
        return None, None

    num_list = [int(x) for x in m.group(1).split('.')]
    rest = m.group(2).strip()

    # 编号后必须跟文本
    if not rest:
        return None, None

    return num_list, rest


# =========================
# 4. 连续性修正（只允许同级）
# =========================
def fix_by_continuity(curr, last):
    """
    只在“同级标题”下修复 OCR 错误
    严禁破坏合法下钻
    """
    if last is None:
        return curr

    # 情况 0：合法下钻（如 9.1 → 9.1.1）
    if len(curr) > len(last):
        return curr

    # 情况 1：明显 OCR 错（230 这种）
    if curr[-1] >= 100:
        return last[:-1] + [last[-1] + 1]

    # 情况 2：同级兄弟节点但不连续
    if len(curr) == len(last):
        prefix_len = len(curr) - 1
        if prefix_len >= 1 and curr[:prefix_len] == last[:prefix_len]:
            if curr[-1] != last[-1] + 1:
                return last[:-1] + [last[-1] + 1]

    return curr


# =========================
# 5. 主处理流程
# =========================
for p in doc.paragraphs:
    text = p.text.strip()
    if not text:
        continue

    # 严格标题候选判定
    if not is_title_candidate(text):
        continue

    num_list, rest = extract_number(text)
    if not num_list:
        continue

    # 连续性修正
    fixed_num = fix_by_continuity(num_list, last_number)

    num_tuple = tuple(fixed_num)

    # ---------- 新规则：标题编号重复出现，直接忽略 ----------
    if num_tuple in seen_numbers:
        continue

    # 更新状态
    last_number = fixed_num
    seen_numbers.add(num_tuple)

    # 设置 Word 标题样式
    level = min(len(fixed_num), 9)
    try:
        p.style = f'Heading {level}'
    except KeyError:
        p.style = 'Heading 9'


# =========================
# 6. 保存结果
# =========================
doc.save("output.docx")
