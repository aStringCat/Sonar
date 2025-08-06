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
        # 1. 将代码解析为 AST
        tree1 = ast.parse(code1)
        tree2 = ast.parse(code2)

        # 2. 规范化 AST (替换变量名、函数名等)
        normalizer1 = AstNormalizer()
        normalized_tree1 = normalizer1.visit(tree1)

        normalizer2 = AstNormalizer()
        normalized_tree2 = normalizer2.visit(tree2)

        # 3. 将规范化后的 AST 转回字符串，以便比较
        # ast.dump() 能提供一个非常适合比较的、紧凑的树结构表示
        normalized_code1 = ast.dump(normalized_tree1)
        normalized_code2 = ast.dump(normalized_tree2)

        # 4. 使用 SequenceMatcher 计算两个规范化后字符串的相似度
        seq_matcher = difflib.SequenceMatcher(None, normalized_code1, normalized_code2)

        return seq_matcher.ratio()

    except SyntaxError:
        '''针对AST无法处理的情况'''
        try:
            vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b')
            tfidf_matrix = vectorizer.fit_transform([code1, code2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            return float(similarity[0][0])
        except ValueError:
            return 0.0
    except ValueError:
        return 0.0
    except TypeError:
        return 0.0
    except NameError:
        return 0.0
    except AttributeError:
        return 0.0


def generate_detailed_diff(file1_name: str, code1: str, file2_name: str, code2: str) -> dict:
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