from .config import log


class QueryEngine:
    """
    Hybrid retrieval: vector search + keyword search + graph traversal.
    Then assembles context and calls Groq for a grounded answer.
    """

    def __init__(self, db, vector_store, groq):
        self.db = db
        self.vs = vector_store
        self.groq = groq

    def ask(self, question: str) -> str:
        log.info(f"Query: {question}")

        vector_results = self.vs.search(question, limit=5)
        keywords = [word for word in question.split() if len(word) > 3]
        keyword_results = self._search_keywords(keywords)
        graph_results = self._search_graph(keywords)
        context = self._build_context(vector_results, keyword_results, graph_results)

        if not context:
            return (
                "I don't have any relevant memories yet. Keep the agent running and "
                "I'll learn from your work."
            )

        return self.groq.answer_question(question, context)

    def _search_keywords(self, keywords: list) -> list:
        keyword_results = []
        for keyword in keywords[:3]:
            keyword_results.extend(self.db.search_entities(keyword, limit=3))
        return keyword_results

    def _search_graph(self, keywords: list) -> list:
        graph_results = []
        for keyword in keywords[:2]:
            graph_results.extend(self.db.graph_neighbors(keyword, limit=4))
        return graph_results

    def _build_context(
        self, vector_results: list, keyword_results: list, graph_results: list
    ) -> list:
        context = []
        seen = set()

        for result in vector_results:
            key = result.get("event_id", result.get("text", ""))[:50]
            if key not in seen:
                seen.add(key)
                context.append(result)

        if keyword_results:
            entity_text = "Related entities found: " + ", ".join(
                f"{entity['value']} ({entity['entity_type']})"
                for entity in keyword_results[:6]
            )
            context.append(
                {"text": entity_text, "source_app": "memory", "timestamp": ""}
            )

        if graph_results:
            graph_text = "Related connections: " + "; ".join(
                f"{graph['source']} {graph['relation']} {graph['target']}"
                for graph in graph_results[:5]
            )
            context.append(
                {"text": graph_text, "source_app": "memory", "timestamp": ""}
            )

        return context
