import difflib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import FileDetail, CodeLine


def calculate_similarity(code1: str, code2: str) -> float:
    """使用 TF-IDF 和余弦相似度计算两段代码的相似度"""
    try:
        vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b')
        tfidf_matrix = vectorizer.fit_transform([code1, code2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        return float(similarity[0][0])
    except ValueError:
        return 0.0


def generate_detailed_diff(file1_name: str, code1: str, file2_name: str, code2: str) -> dict:
    """
    【二次修复】修正了 'Match' object has no attribute 'n' 的错误。
    将 block.n 替换为正确的 block.size。
    """
    code1_lines = code1.splitlines()
    code2_lines = code2.splitlines()

    file1_lines_with_status = [
        CodeLine(line_num=i + 1, text=line, status='unique')
        for i, line in enumerate(code1_lines)
    ]
    file2_lines_with_status = [
        CodeLine(line_num=i + 1, text=line, status='unique')
        for i, line in enumerate(code2_lines)
    ]

    matcher = difflib.SequenceMatcher(None, code1_lines, code2_lines, autojunk=False)

    # get_matching_blocks() 返回的匹配对象，其长度属性是 .size 而不是 .n
    for block in matcher.get_matching_blocks():
        # 如果匹配长度为0，则跳过
        if block.size == 0:
            continue

        # 遍历匹配块中的每一行，并更新状态
        for k in range(block.size):
            # 将文件1中匹配的行状态改为 'similar'
            if block.a + k < len(file1_lines_with_status):
                file1_lines_with_status[block.a + k].status = 'similar'

            # 将文件2中匹配的行状态改为 'similar'
            if block.b + k < len(file2_lines_with_status):
                file2_lines_with_status[block.b + k].status = 'similar'

    file1_details = FileDetail(name=file1_name, lines=file1_lines_with_status)
    file2_details = FileDetail(name=file2_name, lines=file2_lines_with_status)

    return {"file1_details": file1_details, "file2_details": file2_details}