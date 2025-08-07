import difflib
import ast
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .schemas import FileDetail, CodeLine, CodeChunk


class AstNormalizer(ast.NodeTransformer):

    def __init__(self):
        self.identifiers = {}
        self.counter = 0

    def get_name(self, name):
        if name not in self.identifiers:
            self.identifiers[name] = f"id_{self.counter}"
            self.counter += 1
        return self.identifiers[name]

    def visit_Name(self, node):
        node.id = self.get_name(node.id)
        return node

    def visit_FunctionDef(self, node):
        node.name = self.get_name(node.name)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        node.name = self.get_name(node.name)
        self.generic_visit(node)
        return node

    def visit_arg(self, node):
        node.arg = self.get_name(node.arg)
        return node


def calculate_similarity(code1: str, code2: str) -> float:
    try:
        tree1 = ast.parse(code1)
        tree2 = ast.parse(code2)
        normalizer1 = AstNormalizer()
        normalized_tree1 = normalizer1.visit(tree1)
        normalizer2 = AstNormalizer()
        normalized_tree2 = normalizer2.visit(tree2)
        normalized_code1 = ast.dump(normalized_tree1)
        normalized_code2 = ast.dump(normalized_tree2)
        seq_matcher = difflib.SequenceMatcher(None, normalized_code1, normalized_code2)
        return seq_matcher.ratio()
    except (SyntaxError, Exception):
        try:
            vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b')
            tfidf_matrix = vectorizer.fit_transform([code1, code2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            return float(similarity[0][0])
        except ValueError:
            return 0.0


def generate_detailed_diff(file1_name: str, code1: str, file2_name: str, code2: str) -> dict:
    return _generate_diff_fallback(file1_name, code1, file2_name, code2)


def _generate_diff_fallback(file1_name: str, code1: str, file2_name: str, code2: str) -> dict:
    code1_lines = code1.splitlines()
    code2_lines = code2.splitlines()
    line_matcher = difflib.SequenceMatcher(None, code1_lines, code2_lines, autojunk=False)

    file1_details_lines = []
    file2_details_lines = []

    # 内部函数，对单行进行词语级比较并返回chunks
    def get_word_diff_chunks(line1, line2):
        # 使用正则表达式按空白符分割，并保留空白符作为独立的token
        words1 = [token for token in re.split(r'(\s+|[^\w\s])', line1) if token]
        words2 = [token for token in re.split(r'(\s+|[^\w\s])', line2) if token]

        word_matcher = difflib.SequenceMatcher(None, words1, words2)

        chunks1, chunks2 = [], []

        # 遍历词语级别的差异 (此部分逻辑无需改变)
        for word_tag, w_i1, w_i2, w_j1, w_j2 in word_matcher.get_opcodes():
            text1 = "".join(words1[w_i1:w_i2])
            text2 = "".join(words2[w_j1:w_j2])

            if word_tag == 'equal':
                if text1:
                    chunks1.append(CodeChunk(text=text1, status='similar'))
                    chunks2.append(CodeChunk(text=text2, status='similar'))
            else:
                if text1:
                    chunks1.append(CodeChunk(text=text1, status='unique'))
                if text2:
                    chunks2.append(CodeChunk(text=text2, status='unique'))

        # 合并相邻块的逻辑也无需改变
        def merge_chunks(chunks):
            if not chunks: return [CodeChunk(text="", status='unique')]
            merged = [chunks[0]]
            for chunk in chunks[1:]:
                if chunk.status == merged[-1].status:
                    merged[-1].text += chunk.text
                else:
                    merged.append(chunk)
            return merged

        return merge_chunks(chunks1), merge_chunks(chunks2)

    # 遍历行级别的差异
    for tag, i1, i2, j1, j2 in line_matcher.get_opcodes():
        if tag == 'equal':
            # 相同的行，所有内容都是 similar
            for i in range(i1, i2):
                file1_details_lines.append(CodeLine(line_num=i + 1, chunks=[CodeChunk(text=code1_lines[i], status='similar')]))
            for j in range(j1, j2):
                file2_details_lines.append(CodeLine(line_num=j + 1, chunks=[CodeChunk(text=code2_lines[j], status='similar')]))

        elif tag == 'delete':
            # 只在文件1中存在的行，所有内容都是 unique
            for i in range(i1, i2):
                file1_details_lines.append(CodeLine(line_num=i + 1, chunks=[CodeChunk(text=code1_lines[i], status='unique')]))

        elif tag == 'insert':
            # 只在文件2中存在的行，所有内容都是 unique
            for j in range(j1, j2):
                file2_details_lines.append(CodeLine(line_num=j + 1, chunks=[CodeChunk(text=code2_lines[j], status='unique')]))

        elif tag == 'replace':
            # 两边都存在但内容不同的行，需要进行词语级比较
            num_pairs = min(i2 - i1, j2 - j1)
            # 逐行进行词语比较
            for k in range(num_pairs):
                chunks1, chunks2 = get_word_diff_chunks(code1_lines[i1 + k], code2_lines[j1 + k])
                file1_details_lines.append(CodeLine(line_num=i1 + k + 1, chunks=chunks1))
                file2_details_lines.append(CodeLine(line_num=j1 + k + 1, chunks=chunks2))

            # 处理多余的行（如果替换块的行数不等）
            if (i2 - i1) > num_pairs: # 文件1多出来的行
                for k in range(num_pairs, i2 - i1):
                    file1_details_lines.append(CodeLine(line_num=i1 + k + 1, chunks=[CodeChunk(text=code1_lines[i1+k], status='unique')]))
            if (j2 - j1) > num_pairs: # 文件2多出来的行
                for k in range(num_pairs, j2 - j1):
                    file2_details_lines.append(CodeLine(line_num=j1 + k + 1, chunks=[CodeChunk(text=code2_lines[j1+k], status='unique')]))


    file1_details = FileDetail(name=file1_name, lines=file1_details_lines)
    file2_details = FileDetail(name=file2_name, lines=file2_details_lines)

    return {"file1_details": file1_details, "file2_details": file2_details}
