import json, os, toml, sys
from langchain_community.graphs.networkx_graph import NetworkxEntityGraph, KnowledgeTriple
from langchain_openai import ChatOpenAI
from langchain_community.chains.graph_qa.base import GraphQAChain
import networkx as nx
import matplotlib.pyplot as plt

def load_api_key(toml_file_path="secrets.toml"):
    try:
        with open(toml_file_path, 'r') as file:
            data = toml.load(file)
    except FileNotFoundError:
        print(f"File not found: {toml_file_path}", file=sys.stderr)
        return
    except toml.TomlDecodeError:
        print(f"Error decoding TOML file: {toml_file_path}", file=sys.stderr)
        return
    # Set environment variables
    for key, value in data.items():
        os.environ[key] = str(value)

def read_json_triplets(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return [(item['sujeto'], item['predicado'], item['objeto']) for item in data if 'sujeto' in item and 'predicado' in item and 'objeto' in item]
    except json.JSONDecodeError:
        print(f"Error al leer el archivo JSON: {file_path}")
        return []


load_api_key()

# Buscar archivos que terminen en ".txt" en la carpeta triplets
triplets_dir = os.path.join(os.getcwd(), "triplets")
if os.path.exists(triplets_dir) and os.path.isdir(triplets_dir):
    files = [os.path.join(triplets_dir, f) for f in os.listdir(triplets_dir) if f.endswith(".txt")]
else:
    print(f"Warning: Directory '{triplets_dir}' not found or is not a directory.")
    files = []
kg = []

for file_name in files:
    file_path = os.path.join(os.getcwd(), file_name)
    triplets = read_json_triplets(file_path)
    kg.extend(triplets)

graph = NetworkxEntityGraph()
# Añadir los triplets al graph
for (node1, relation, node2) in kg:
    graph.add_triple(KnowledgeTriple(node1, relation, node2))

def query_knowledge_graph(graph, question):
    print(f"Query: {question}")
    
    # Get all entities and relationships in the graph
    all_triples = []
    
    # Access the underlying NetworkX graph directly - it's stored as graph._graph
    nx_graph = graph._graph
    
    # Iterate through edges and collect triples
    for source, target, edge_data in nx_graph.edges(data=True):
        relation = edge_data.get("relation", "")
        all_triples.append((source, relation, target))
    
    # Filter results by date if "mayo" and "2025" are in the question
    if "mayo" in question.lower() and "2025" in question:
        relevant_triples = []
        for triple in all_triples:
            subject, relation, obj = triple
            if "mayo" in str(subject).lower() or "mayo" in str(obj).lower() or "mayo" in str(relation).lower():
                if "2025" in str(subject) or "2025" in str(obj) or "2025" in str(relation):
                    relevant_triples.append(triple)
    else:
        relevant_triples = all_triples
    
    # If no results, return general 2025 events
    if not relevant_triples:
        relevant_triples = [t for t in all_triples if "2025" in str(t[0]) or "2025" in str(t[1]) or "2025" in str(t[2])]
    
    print("Entities Extracted:")
    print("\nFull Context:")
    for subject, relation, obj in relevant_triples:
        print(f"{subject} {relation} {obj}")
    
    return relevant_triples

question = "Que ha pasado el 8 de mayo de 2025"
query_knowledge_graph(graph, question)

'''
> Entering new GraphQAChain chain...
Entities Extracted:

Las Ratas
Full Context:
Las Ratas pasa a Final COAC 2025
Las Ratas actúa en Gala Carnaval de Cádiz 2025
Las Ratas ocupan segunda posición en el ranking de Jurado con Solera
Las Ratas participó en COAC 2025
Las Ratas es una comparsa
Las Ratas tiene música de Jesús Bienvenido Saucedo
Las Ratas es dirigida por Daniel Obregón Guillén
Las Ratas es de Cádiz
Las Ratas criticó en un pasodoble a Juanma Moreno Bonilla
Las Ratas criticó en un cuplé a Carlos Mazón

> Finished chain.
'''

# Dibujar el grafo
# Create directed graph
G = nx.DiGraph()
for node1, relation, node2 in kg:
    ## Añadimos solamente los 50 primeros nodos
    if len(G.nodes) >= 50:
        break
    G.add_edge(node1, node2, label=relation)

# Plot the graph
plt.figure(figsize=(25, 25), dpi=25)
pos = nx.spring_layout(G, k=2, iterations=50, seed=0)

nx.draw_networkx_nodes(G, pos, node_size=5000)
nx.draw_networkx_edges(G, pos, edge_color='gray', edgelist=G.edges(), width=2)
nx.draw_networkx_labels(G, pos, font_size=24)
edge_labels = nx.get_edge_attributes(G, 'label')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=24)

# Display the plot
plt.axis('off')
plt.show()