"""Relations aligner

The alignment between a gold standard relation and a predicted relation is needed
for evaluation. This becomes complicated when we allow partial matching between
arguments.

The danger is that if the relations are anomalous, the search space would become 
huge. If the program does not terminate within minutes, we should look at the 
the output and make sure that the arg spans are reasonable. 
"""
import json
from collections import defaultdict
import numpy as np

from threading_timer_decorator_exit import exit_after

@exit_after(120)
def align_relations(gold_list, predicted_list, partial_match_cutoff):
    """Aligning two lists of relations

    Input:
        gold_list : a list of ground truth relations
        predicted_list : a list of predicted relations

    Returns:
        A list of alignments between gold and predicted relations
    """
    for g_relation in gold_list:
        g_relation['Arg1']['TokenIndexSet'] = \
                set([x[2] for x in g_relation['Arg1']['TokenList']])
        g_relation['Arg2']['TokenIndexSet'] = \
                set([x[2] for x in g_relation['Arg2']['TokenList']])
    for p_relation in predicted_list:
        p_relation['Arg1']['TokenIndexSet'] = \
                set(p_relation['Arg1']['TokenList'])
        p_relation['Arg2']['TokenIndexSet'] = \
                set(p_relation['Arg2']['TokenList'])

    doc_id_to_gold_list = _separate_by_doc_id(gold_list)
    doc_id_to_predicted_list = _separate_by_doc_id(predicted_list)
    all_doc_id = set(
        doc_id_to_gold_list.keys() + doc_id_to_predicted_list.keys())
    relation_alignment = []
    arg1_alignment = []
    arg2_alignment = []
    for doc_id in all_doc_id:
        doc_gold_list = doc_id_to_gold_list[doc_id]
        doc_predicted_list = doc_id_to_predicted_list[doc_id]

        new_relation_alignment = _align(
            doc_gold_list, doc_predicted_list, rel_alignment_score, partial_match_cutoff)
        new_arg1_alignment = _align(
            doc_gold_list, doc_predicted_list, arg1_alignment_score, partial_match_cutoff)
        new_arg2_alignment = _align(
            doc_gold_list, doc_predicted_list, arg2_alignment_score, partial_match_cutoff)
        relation_alignment.extend(new_relation_alignment)
        arg1_alignment.extend(new_arg1_alignment)
        arg2_alignment.extend(new_arg2_alignment)

    return arg1_alignment, arg2_alignment, relation_alignment

def _align(gold_list, predicted_list, alignment_score_fn, partial_match_cutoff):
    """Align the gold standard and the predicted discourse relations in the same doc
    """
    rel_score_matrix, rel_adjacency = compute_score_matrix(
        gold_list, predicted_list, alignment_score_fn, partial_match_cutoff)
    _, index_alignment = _recurs_align_relations(
        0, set(), len(predicted_list), rel_score_matrix, rel_adjacency, partial_match_cutoff)
    rel_alignment = []
    for i, j in index_alignment:
        g_relation = gold_list[i] if i != -1 else None
        p_relation = predicted_list[j] if j != -1 else None
        rel_alignment.append((g_relation, p_relation))
    return rel_alignment

def compute_score_matrix(gold_list, predicted_list, alignment_score_fn, partial_match_cutoff):
    """Compute the weighted adjacency matrix for alignment 

    This score matrix serves as an adjecency matrix for searching for 
    the best alignment.
    """
    score_matrix = {}
    adjacency = np.zeros((len(gold_list), len(predicted_list)))
    for i, g_relation in enumerate(gold_list):
        score_matrix[i] = {}
        for j, p_relation in enumerate(predicted_list):
            score = alignment_score_fn(g_relation, p_relation)
            if score >= partial_match_cutoff:
                score_matrix[i][j] = score
                adjacency[i][j] = 1.0
    return score_matrix, adjacency

def _recurs_align_relations(gi, pi_used_set, num_predicted, score_matrix, adjacency, partial_match_cutoff):
    if gi == len(score_matrix):
        alignment = [(-1, pi)
            for pi in xrange(num_predicted) if pi not in pi_used_set]
        return 0, alignment
    max_score = 0.0
    max_alignment = []
    found_maximal_match = False
    for pi in score_matrix[gi]:
        alignment_score = score_matrix[gi][pi]
        #perfect match or one-to-one already
        found_maximal_match = (alignment_score == 1) or \
            (adjacency.sum(0)[pi] == 1 and len(score_matrix[gi]) == 1)
        if alignment_score >= partial_match_cutoff and pi not in pi_used_set:
            pi_used_set.add(pi)
            score, alignment = _recurs_align_relations(
                gi+1, pi_used_set, num_predicted, score_matrix, adjacency, partial_match_cutoff)
            if alignment_score + score >= max_score:
                max_score = alignment_score + score
                max_alignment = alignment + [(gi, pi)]
            pi_used_set.remove(pi)

        if found_maximal_match:
            break

    if not found_maximal_match:
        score, alignment = _recurs_align_relations(
            gi+1, pi_used_set, num_predicted, score_matrix, adjacency, partial_match_cutoff)
        if score >= max_score:
            max_score = score
            max_alignment = alignment + [(gi, -1)]
    return max_score, max_alignment



def rel_alignment_score(g_relation, p_relation):
    arg1_overlap = is_overlap(g_relation['Arg1'], p_relation['Arg1'])
    arg2_overlap = is_overlap(g_relation['Arg2'], p_relation['Arg2'])
    if arg1_overlap and arg2_overlap:
        arg1_f1 = _arg_pos_alignment_score(g_relation, p_relation, 1)
        arg2_f1 = _arg_pos_alignment_score(g_relation, p_relation, 2)
        return (arg1_f1 + arg2_f1) / 2
    else:
        return 0.0

def arg1_alignment_score(g_relation, p_relation):
    arg1_overlap = is_overlap(g_relation['Arg1'], p_relation['Arg1'])
    if arg1_overlap:
        return _arg_pos_alignment_score(g_relation, p_relation, 1)
    else: 
        return 0.0

def arg2_alignment_score(g_relation, p_relation):
    arg2_overlap = is_overlap(g_relation['Arg2'], p_relation['Arg2'])
    if arg2_overlap:
        return _arg_pos_alignment_score(g_relation, p_relation, 2)
    else:
        return 0.0

def _arg_pos_alignment_score(g_relation, p_relation, arg_pos):
    assert arg_pos == 1 or arg_pos == 2
    key = 'Arg%s' % arg_pos
    arg_f1 = compute_f1_span(
        g_relation[key]['TokenIndexSet'],
        p_relation[key]['TokenIndexSet'])
    return arg_f1

def save_alignment(relation_pairs):
    """Save alignment for inspection"""
    f = open('relation_alignment.json', 'w')
    for pair in relation_pairs:
        new_pair = []
        new_pair.append(pair[0].deepcopy())
        new_pair.append(pair[1].deepcopy())
        if pair[0] is None:
            new_pair[0] = {}
        else:
            del new_pair[0]['Arg1']['TokenIndexSet']
            del new_pair[0]['Arg2']['TokenIndexSet']
        if pair[1] is None:
            new_pair[1] = {}
        else:
            del new_pair[1]['Arg1']['TokenIndexSet']
            del new_pair[1]['Arg2']['TokenIndexSet']
        f.write(json.dumps(new_pair) + '\n')
    f.close()

def is_overlap(g_arg, p_arg):
    """Check if there is an overlap between gold arg and predicted Arg1

    We need this function to prune the search space. If there is no overlap,
    we will not recurse on this pair.
    """
    if len(p_arg['TokenList']) == 0:
        return False
    return (g_arg['TokenList'][-1][2] > p_arg['TokenList'][0] and \
            g_arg['TokenList'][0][2] <= p_arg['TokenList'][0]) or \
        (p_arg['TokenList'][-1] > g_arg['TokenList'][0][2] and \
            p_arg['TokenList'][0] <= g_arg['TokenList'][0][2])


def compute_f1_span(g_index_set, p_index_set):
    """Compute F1 score for a given pair of token list"""
    correct = float(len(g_index_set.intersection(p_index_set)))
    if correct == 0.0:
        return 0.0
    precision = correct / len(p_index_set)
    recall = correct / len(g_index_set)
    return 2 * (precision * recall) / (precision + recall)

def _separate_by_doc_id(relation_list):
    """Use a dictionary to sort out the relation list by the docID"""
    doc_id_to_relation_list = defaultdict(list)
    for relation in relation_list:
        doc_id_to_relation_list[relation['DocID']].append(relation)
    return doc_id_to_relation_list
