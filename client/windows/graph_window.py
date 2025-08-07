import networkx as nx
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QFileDialog
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import io

class GraphWindow(QDialog):
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle("抄袭关系网络图")
        self.setModal(True)
        self.setLayout(QVBoxLayout())
        self.resize(800, 600)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout().addWidget(self.canvas)

        self.download_button = QPushButton("下载图片")
        self.download_button.clicked.connect(self.download_image)
        self.layout().addWidget(self.download_button)

        self.generate_graph(results)

    def generate_graph(self, results):
        G = nx.Graph()
        for item in results:
            similarity = item.get('similarity', 0.0)
            if similarity > 0.1:  # 只显示有一定相似度的关系
                G.add_edge(item['file1'], item['file2'], weight=similarity)

        if not G.edges():
            self.figure.text(0.5, 0.5, "未发现显著的抄袭关系", ha='center')
            self.canvas.draw()
            return

        pos = nx.spring_layout(G, k=0.8, iterations=50)

        # 节点大小根据度（连接数）来决定
        node_sizes = [v * 500 + 500 for v in dict(G.degree()).values()]

        # 边的宽度和颜色根据相似度权重来决定
        edge_weights = [G[u][v]['weight'] for u, v in G.edges()]
        edge_colors = [w * 1.5 for w in edge_weights]

        plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='skyblue', alpha=0.9)
        nx.draw_networkx_edges(G, pos, width=edge_weights, edge_color=edge_colors,
                               edge_cmap=plt.cm.Reds, alpha=0.7)
        nx.draw_networkx_labels(G, pos, font_size=10)

        plt.title("文件抄袭关系网络图")
        self.canvas.draw()

    def download_image(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "保存网络图", "plagiarism_network.png", "PNG Files (*.png);;JPEG Files (*.jpg)")
        if file_path:
            self.figure.savefig(file_path, dpi=300, bbox_inches='tight')