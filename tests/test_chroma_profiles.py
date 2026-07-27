import numpy as np

from src import chroma


class CapturingModel:
    def __init__(self):
        self.inputs = []

    def encode(self, texts, normalize_embeddings=True):
        self.inputs.append(list(texts))
        return np.ones((len(texts), 2))


def test_ruri_v3_retrieval_prefixes():
    model = CapturingModel()

    chroma.embed_texts(
        ["質問"],
        model,
        input_type="query",
        prefix_scheme="ruri_v3_retrieval",
    )
    chroma.embed_texts(
        ["記憶"],
        model,
        input_type="document",
        prefix_scheme="ruri_v3_retrieval",
    )

    assert model.inputs == [["検索クエリ: 質問"], ["検索文書: 記憶"]]


def test_legacy_collection_keeps_existing_embedding_behavior():
    model = CapturingModel()

    chroma.embed_query("質問", model)

    assert model.inputs == [["質問"]]
