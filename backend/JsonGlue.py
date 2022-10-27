import json
import re

import networkx, jaro
from nltk import word_tokenize
from nltk.corpus import stopwords, wordnet


# This code is an adapted version of the code from https://github.com/7vbauer/JSONGlue (accessed 05-10-2022) and
# is described in
# "JSONGlue: A hybrid matcher for JSON schema matching" by Vitor Marini Blaselbauer & Jõao Marcelo Borovina Josko

def compare_jaro_winkler(graph1, graph2, node1, node2):
    distance = jaro.jaro_winkler_metric(graph1.nodes[node1]['name'], graph2.nodes[node2]['name'])
    return distance


def compare_wu_palmer(graph1, graph2, node1, node2):
    w1 = graph1.nodes[node1]['name']
    w2 = graph2.nodes[node2]['name']

    lst1 = w1.split()
    lst2 = w2.split()

    len1 = len(lst1)
    len2 = len(lst2)

    if len1 == 0 or len2 == 0:
        graph1.nodes[node1]['comp'] = None
        graph2.nodes[node2]['comp'] = None
        return 1.0
    if len1 == 1 and len2 == 1:  # caso simples 1-1
        graph1.nodes[node1]['comp'] = w1
        graph2.nodes[node2]['comp'] = w2
        return find_best_synset(w1, w2)
    else:
        if len1 == 1 and len2 == 2:  # caso atr1 com 1 termo atr2 2 ou mais
            edges = graph1.edges
            ancnode = -1
            for e in edges:
                if node1 == e[1]:
                    ancnode = e[0]
                    break
            if ancnode == -1:
                anc = w1
            else:
                anc = graph1.nodes[ancnode]['name']
            w11 = anc
            w12 = w1
            w21 = lst2[0]
            w22 = lst2[1]
            if w11 is None or w12 is None or w21 is None or w22 is None:
                if w11 is None:
                    w11 = ''
                if w12 is None:
                    w12 = ''
                if w21 is None:
                    w21 = ''
                if w22 is None:
                    w22 = ''
                graph1.nodes[node1]['comp'] = ' '.join([w11, w12])
                graph2.nodes[node2]['comp'] = ' '.join([w21, w22])
                return 1.0
            graph1.nodes[node1]['comp'] = ' '.join([w11, w12])
            graph2.nodes[node2]['comp'] = ' '.join([w21, w22])
            return find_average_wu_palmer(w11, w12, w21, w22)
        elif len1 == 2 and len2 == 1:
            edges = graph2.edges
            ancnode = -1
            for e in edges:
                if node2 == e[1]:
                    ancnode = e[0]
                    break
            if ancnode == -1:
                anc = w2
            else:
                anc = graph2.nodes[ancnode]['name']
            w11 = lst1[0]
            w12 = lst1[1]
            w21 = anc
            w22 = w2
            if w11 is None or w12 is None or w21 is None or w22 is None:
                if w11 is None:
                    w11 = ''
                if w12 is None:
                    w12 = ''
                if w21 is None:
                    w21 = ''
                if w22 is None:
                    w22 = ''
                graph1.nodes[node1]['comp'] = ' '.join([w11, w12])
                graph2.nodes[node2]['comp'] = ' '.join([w21, w22])
                return 1.0
            graph1.nodes[node1]['comp'] = ' '.join([w11, w12])
            graph2.nodes[node2]['comp'] = ' '.join([w21, w22])
            return find_average_wu_palmer(w11, w12, w21, w22)
        elif len1 == 2 and len2 == 2:
            w11 = lst1[0]
            w12 = lst1[1]
            w21 = lst2[0]
            w22 = lst2[1]
            if w11 is None or w12 is None or w21 is None or w22 is None:
                if w11 is None:
                    w11 = ''
                if w12 is None:
                    w12 = ''
                if w21 is None:
                    w21 = ''
                if w22 is None:
                    w22 = ''
                graph1.nodes[node1]['comp'] = ' '.join([w11, w12])
                graph2.nodes[node2]['comp'] = ' '.join([w21, w22])
                return 1.0
            graph1.nodes[node1]['comp'] = ' '.join([w11, w12])
            graph2.nodes[node2]['comp'] = ' '.join([w21, w22])
            return find_average_wu_palmer(w11, w12, w21, w22)
        else:
            graph1.nodes[node1]['comp'] = None
            graph2.nodes[node2]['comp'] = None
            return 1.0


def find_average_wu_palmer(w11, w12, w21, w22):
    x = find_best_synset(w11, w21)
    y = find_best_synset(w12, w22)
    return (x + y) / 2


def find_best_synset(word1, word2):
    synsets_1 = wordnet.synsets(word1)
    synsets_2 = wordnet.synsets(word2)

    if len(synsets_1) == 0 or len(synsets_2) == 0:
        return 1.0

    max_sim = 0.0
    sim = None
    for synset_1 in synsets_1:
        for synset_2 in synsets_2:
            sim = wordnet.wup_similarity(synset_1, synset_2)
        if sim is not None and sim > max_sim:
            max_sim = sim
    return 1 - max_sim


def create_graph(jstring, i, lvl, node_number, graph=None):  # 1
    return_dict = {}
    if graph is None:
        graph = networkx.Graph()
    # print("searching....1 String: " + jstring)
    i = jstring.find('"properties":{"', i) + len('"properties":{"')  # 1.1
    # print("Found 1")
    while True:
        node_base = node_number
        tmp = ""
        j = jstring.find('"', i)
        tmp += jstring[i:j]  # 1.2
        # print("finding type...")
        aux = find_type(jstring, i)
        # print("found type")
        tmp_type = aux[0]
        # print("type: " + tmp_type)
        j = aux[1]
        i = j
        graph.add_node(node_number, name=tmp, type=tmp_type, height=lvl)
        return_dict.update({node_number: [tmp, tmp_type, lvl]})  # Necessario ainda?
        node_number += 1

        if tmp_type == 'array':  # 4
            # print("searching....2 String: " + jstring)
            i = jstring.find('"items":{', i) + len('"items":{')  # 4
            # print("Found 2")
            tmp_type = find_type(jstring, i)[0]  # ja encontra o tipo
            if tmp_type == 'object':
                i = jstring.find('"properties":{"', i) + len('"properties":{"')  # 6
                array_edge = node_number - 1
                lvl += 1
                while True:
                    tmp = ""  # limpa o container do nome
                    # print("searching....3 String: " + jstring)
                    j = jstring.find('"', i)  # encontra o fim do nome
                    # print("Found 3")

                    tmp += jstring[i:j]  # recebe o nome do item
                    tmp_type = find_type(jstring, i)[0]  # recebe o tipo do item
                    graph.add_node(node_number, name=tmp, type=tmp_type, height=lvl)  # cria o nó
                    graph.add_edge(array_edge, node_number)
                    # return_dict.update({node_number : [tmp, tmp_type, lvl]}) acho q nao precisa?
                    node_number += 1  # incrementa o contador de nós
                    # print("searching....4 String: " + jstring)
                    i = jstring.find('}', i)
                    # print("Found 4")

                    if jstring[i + 1] == ',':  # teoricamente tratando corretamente
                        i += 3
                        continue
                    elif jstring[i + 1] == '}':
                        i += 1
                        # print("searching....5 String: " + jstring)
                        i = jstring.find('}', i + 1)
                        # print("Found 5")

                        break
                lvl -= 1
            else:
                i = jstring.find('}', i)

        elif tmp_type == 'object':  # 3
            retorno_t = create_graph(jstring, i, lvl + 1, node_number, graph)
            i = retorno_t[1]
            node_number = retorno_t[3]

            for key, value in retorno_t[0].items():
                if value[2] == lvl + 1:
                    graph.add_edge(node_base, key)
                    # print(value)

        if jstring[i] == '}':
            i = jstring.find('}', i + 1)
        else:
            i = jstring.find('}', i)

        if i + 1 == len(jstring):  # verificar se está chegando nesse caso
            break
        elif jstring[i + 1] == ',':
            i += 3  # .find('"', i)
            continue
        elif jstring[i + 1] == '}':
            i += 1
            break
        else:
            break
    return return_dict, i, lvl, node_number, graph


def traverse_nodes_helper(json_schema):
    node_counter = 0
    graph = networkx.Graph()

    def traverse_nodes(start_node, node_counter, graph, parent=None, level=0, name=""):
        if "oneOf" not in start_node and "anyOf" not in start_node:
            node_type = start_node["type"] if "type" in start_node else "null"
            if parent is not None:
                graph.add_edge(parent, node_counter)
            parent = node_counter
            if name:
                graph.add_node(node_counter, name=name, type=node_type, height=level)
                node_counter += 1
            if node_type == "object" and "properties" in start_node:
                if name:
                    level += 1
                for item in start_node["properties"].keys():
                    graph, node_counter = traverse_nodes(
                        start_node["properties"][item],
                        node_counter,
                        graph,
                        parent=parent,
                        level=level,
                        name=item,
                    )
            elif node_type == "array" and "items" in start_node:
                if "type" in start_node["items"] and start_node["items"]["type"] == "object":
                    if "properties" in start_node["items"]:
                        for item in start_node["items"]["properties"].keys():
                            graph, node_counter = traverse_nodes(
                                start_node["items"]["properties"][item],
                                node_counter,
                                graph,
                                parent=parent,
                            level=level + 1,
                            name=item,
                        )
        return graph, node_counter

    return traverse_nodes(json_schema, node_counter, graph)


def find_type(jstring, i):
    i = jstring.find('"type":"', i) + len('"type":"')
    j = jstring.find('"', i)
    return jstring[i:j], j


def remove_spaces(js):
    ret = ''
    f = 1
    for i in js:
        if (i == ' ' or i == '\n') and f == 1:
            continue
        elif i == '"':
            ret += i
            f *= -1
        else:
            ret += i
    return ret


def preprocess(in_str):
    if not isinstance(in_str, str):
        return None
    # Remove Special Char, Number....
    clean_str = re.sub('[^A-Za-z]+', ' ', in_str.lower())
    # Remove additional space between words
    clean_str = re.sub(' +', ' ', clean_str)
    # Extract Stop words
    stop_words = set(stopwords.words('english'))
    # Extract Stop words
    tokens = word_tokenize(clean_str)
    str_list = [w for w in tokens if w not in stop_words]
    return ' '.join(map(str, str_list))


def compare_graphs(graph1, graph2, node_number1, node_number2):
    results = {}
    for x in range(0, node_number1):
        closest_matching_item = {"lexical": {"name": "", "value": float(1)}, "edit": {"name": "", "value": float(1)}}
        for y in range(0, node_number2):
            if graph1.nodes[x]['type'] == 'object' or graph2.nodes[y]['type'] == 'object':
                pass
            else:
                edit = compare_jaro_winkler(graph1, graph2, x, y)
                if edit < closest_matching_item["edit"]["value"]:
                    closest_matching_item["edit"]["value"] = edit
                    closest_matching_item["edit"]["name"] = graph2.nodes[y]["name"]
                lexical = compare_wu_palmer(graph1, graph2, x, y)
                if lexical < closest_matching_item["lexical"]["value"]:
                    closest_matching_item["lexical"]["value"] = lexical
                    closest_matching_item["lexical"]["name"] = graph2.nodes[y]["name"]
        results[graph1.nodes[x]['name']] = closest_matching_item

    return results


def average_result(result):
    dict_length = len(result)
    edit_total = sum(value["edit"]["value"] for key, value in result.items())
    lexical_total = sum(value["lexical"]["value"] for key, value in result.items())
    try:
        return {"edit_average": (edit_total / dict_length), "lexical_average": (lexical_total / dict_length)}
    except ZeroDivisionError:
        return {"edit_average": 1.0, "lexical_average": 1.0}


def calculate_json_glue_score(schema1, schema2):
    schema1 = json.loads(schema1)
    schema2 = json.loads(schema2)
    if schema1 is None or schema2 is None:
        return {"edit_average": 1.0, "lexical_average": 1.0}
    json_dict = {"json1": schema1, "json2": schema2}
    graphs_dict = {}
    graphs_size = {}
    for schema in json_dict.keys():
        graph = traverse_nodes_helper(json_dict[schema])
        graphs_dict[schema] = graph[0]
        graphs_size[schema] = graph[1]
        for j in range(0, int(graphs_size[schema])):
            graphs_dict[schema].nodes[j]['orig'] = graphs_dict[schema].nodes[j]['name']
            tmp = preprocess(graphs_dict[schema].nodes[j]['name'])
            names = tmp.split()
            graphs_dict[schema].nodes[j]['name'] = ' '.join(names)
    result = compare_graphs(graphs_dict["json1"], graphs_dict["json2"], graphs_size["json1"], graphs_size["json2"])
    return average_result(result)
