from datasimulator.graph import Graph
from dictionaryutils import dictionary


def test():
    graph = Graph(dictionary, "DEV", "test")
    graph.generate_nodes_from_dictionary()
    graph.construct_graph_edges()
    assert graph.graph_validation()
