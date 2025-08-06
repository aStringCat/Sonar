import difflib
import ast
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .schemas import FileDetail, CodeLine


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
    def get_normalized_node_map(code):
        tree = ast.parse(code)
        node_map = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.For, ast.While, ast.If, ast.With)):
                # 规范化节点以获得其结构
                normalized_node = AstNormalizer().visit(node)
                # 使用 ast.dump 作为该节点结构的“哈希”
                node_key = ast.dump(normalized_node)
                # 记录该结构对应的行号范围
                start_line = node.lineno
                end_line = getattr(node, 'end_lineno', start_line)
                if node_key not in node_map:
                    node_map[node_key] = []
                node_map[node_key].append((start_line, end_line))
        return node_map

    try:
        map1 = get_normalized_node_map(code1)
        map2 = get_normalized_node_map(code2)
    except (SyntaxError, Exception):
        # 如果AST解析失败，则退回到基于文本的difflib
        return _generate_diff_fallback(file1_name, code1, file2_name, code2)

    # 查找两个文件中都存在的相同结构
    common_keys = set(map1.keys()) & set(map2.keys())

    matched_lines1 = [False] * len(code1.splitlines())
    for key in common_keys:
        for start, end in map1[key]:
            for i in range(start - 1, end):
                if i < len(matched_lines1):
                    matched_lines1[i] = True

    matched_lines2 = [False] * len(code2.splitlines())
    for key in common_keys:
        for start, end in map2[key]:
            for i in range(start - 1, end):
                if i < len(matched_lines2):
                    matched_lines2[i] = True

    file1_lines = [CodeLine(line_num=i + 1, text=line, status='similar' if matched_lines1[i] else 'unique') for i, line
                   in enumerate(code1.splitlines())]
    file2_lines = [CodeLine(line_num=i + 1, text=line, status='similar' if matched_lines2[i] else 'unique') for i, line
                   in enumerate(code2.splitlines())]

    return {
        "file1_details": FileDetail(name=file1_name, lines=file1_lines),
        "file2_details": FileDetail(name=file2_name, lines=file2_lines)
    }


def _generate_diff_fallback(file1_name: str, code1: str, file2_name: str, code2: str) -> dict:
    code1_lines = code1.splitlines()
    code2_lines = code2.splitlines()
    matcher = difflib.SequenceMatcher(None, code1_lines, code2_lines, autojunk=False)

    file1_status = ['unique'] * len(code1_lines)
    file2_status = ['unique'] * len(code2_lines)

    for block in matcher.get_matching_blocks():
        if block.size == 0: continue
        for i in range(block.size):
            file1_status[block.a + i] = 'similar'
            file2_status[block.b + i] = 'similar'

    file1_details = FileDetail(name=file1_name,
                               lines=[CodeLine(line_num=i + 1, text=line, status=file1_status[i]) for i, line in
                                      enumerate(code1_lines)])
    file2_details = FileDetail(name=file2_name,
                               lines=[CodeLine(line_num=i + 1, text=line, status=file2_status[i]) for i, line in
                                      enumerate(code2_lines)])

    return {"file1_details": file1_details, "file2_details": file2_details}
