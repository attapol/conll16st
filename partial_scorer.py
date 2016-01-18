"""Scorer for partial argument match

"""

import argparse
import json

import validator
import aligner

from confusion_matrix import ConfusionMatrix, Alphabet
from conn_head_mapper import ConnHeadMapper

def partial_evaluate(gold_list, predicted_list, partial_match_cutoff):
    """Evaluate the parse output with partial matching for arguments
    """
    arg1_alignment, arg2_alignment, relation_alignment = \
        aligner.align_relations(gold_list, predicted_list, partial_match_cutoff)
    arg1_match_prf, arg2_match_prf, total_match_prf = \
        evaluate_args(arg1_alignment, arg2_alignment, partial_match_cutoff)
    entire_relation_match_prf = \
        evaluate_rel_arg_whole_rel(relation_alignment, partial_match_cutoff)
    sense_cm = evaluate_sense(relation_alignment)

    print arg1_match_prf, arg2_match_prf
    print total_match_prf
    print entire_relation_match_prf
    sense_cm.print_summary()
    return arg1_match_prf, arg2_match_prf, entire_relation_match_prf, \
        sense_cm.compute_micro_average_f1()

def evaluate_args(arg1_alignment, arg2_alignment, partial_match_cutoff):
    """Evaluate argument matches"""
    total_arg1_gold, total_arg1_predicted, total_arg1_correct = \
            evaluate_arg_partial_match(arg1_alignment, 1, partial_match_cutoff)
    total_arg2_gold, total_arg2_predicted, total_arg2_correct = \
            evaluate_arg_partial_match(arg2_alignment, 2, partial_match_cutoff)
    arg1_prf = compute_prf(
        total_arg1_gold, total_arg1_predicted, total_arg1_correct)
    arg2_prf = compute_prf(
        total_arg2_gold, total_arg2_predicted, total_arg2_correct)
    rel_arg_prf = compute_prf(
        total_arg1_gold + total_arg2_gold,
        total_arg1_predicted + total_arg2_predicted,
        total_arg1_correct + total_arg2_correct)
    return arg1_prf, arg2_prf, rel_arg_prf

def evaluate_arg_tokenwise(relation_pairs, position):
    assert position == 1 or position == 2
    total_correct = 0.0
    total_gold = 0.0
    total_predicted = 0.0
    for g_relation, p_relation in relation_pairs:
        assert g_relation is not None or p_relation is not None
        g_arg = g_relation['Arg%s' % position]['TokenIndexSet'] \
                if g_relation is not None else set([])
        p_arg = p_relation['Arg%s' % position]['TokenIndexSet'] \
                if p_relation is not None else set([])
        total_correct += len(g_arg.intersection(p_arg))
        total_gold += len(g_arg)
        total_predicted += len(p_arg)
    return total_gold, total_predicted, total_correct

def evaluate_arg_partial_match(relation_pairs, position, partial_match_cutoff):
    """Evaluate the argument based on partial matching criterion

    We evaluate the argument as a whole. 
    """
    assert position == 1 or position == 2
    total_correct = 0.0
    total_gold = 0.0
    total_predicted = 0.0
    for g_relation, p_relation in relation_pairs:
        assert g_relation is not None or p_relation is not None
        if g_relation is None:
            total_predicted += 1
        elif p_relation is None:
            total_gold += 1
        else:
            g_arg = g_relation['Arg%s' % position]['TokenIndexSet']
            p_arg = p_relation['Arg%s' % position]['TokenIndexSet']
            f1_score = aligner.compute_f1_span(g_arg, p_arg)
            if f1_score >= partial_match_cutoff:
                total_correct += 1
            total_predicted += 1
            total_gold += 1
    return total_gold, total_predicted, total_correct

def evaluate_rel_arg_whole_rel(relation_pairs, partial_match_cutoff):
    total_correct = 0.0
    total_gold = 0.0
    total_predicted = 0.0
    for g_relation, p_relation in relation_pairs:
        assert g_relation is not None or p_relation is not None
        if g_relation is None:
            total_predicted += 1
        elif p_relation is None:
            total_gold += 1
        else:
            g_arg1 = g_relation['Arg1']['TokenIndexSet'] \
                    if g_relation is not None else set([])
            p_arg1 = p_relation['Arg1']['TokenIndexSet'] \
                    if p_relation is not None else set([])
            arg1_f1_score = aligner.compute_f1_span(g_arg1, p_arg1)

            g_arg2 = g_relation['Arg2']['TokenIndexSet'] \
                    if g_relation is not None else set([])
            p_arg2 = p_relation['Arg2']['TokenIndexSet'] \
                    if p_relation is not None else set([])
            arg2_f1_score = aligner.compute_f1_span(g_arg2, p_arg2)
            if arg1_f1_score >= partial_match_cutoff and \
                arg2_f1_score >= partial_match_cutoff:
                total_correct += 1
                total_predicted += 1
                total_gold += 1
    return compute_prf(total_gold, total_predicted, total_correct)

def compute_prf(total_gold, total_predicted, total_correct):
    """Compute precision, recall, and F1

    Assume binary classification where we are only interested
    in the positive class. In our case, we look at argument extraction.
    """
    precision = total_correct / total_predicted
    recall = total_correct / total_gold
    f1_score = 2.0 * (precision * recall) / (precision + recall) \
        if precision + recall != 0 else 0.0
    return (round(precision, 4), round(recall, 4), round(f1_score,4))


def evaluate_sense(relation_pairs):
    sense_alphabet = Alphabet()
    for g_relation, _ in relation_pairs:
        if g_relation is not None:
            sense_alphabet.add(g_relation['Sense'][0])
    sense_alphabet.add(ConfusionMatrix.NEGATIVE_CLASS)
    sense_alphabet.growing = False

    sense_cm = ConfusionMatrix(sense_alphabet)
    for g_relation, p_relation in relation_pairs:
        assert g_relation is not None or p_relation is not None
        if g_relation is None:
            predicted_sense = p_relation['Sense'][0]
            sense_cm.add(predicted_sense, ConfusionMatrix.NEGATIVE_CLASS)
        elif p_relation is None:
            gold_sense = g_relation['Sense'][0]
            if gold_sense in validator.SENSES:
                sense_cm.add(ConfusionMatrix.NEGATIVE_CLASS, gold_sense)
        else:
            predicted_sense = p_relation['Sense'][0]
            gold_sense = g_relation['Sense'][0]
            if gold_sense in validator.SENSES:
                sense_cm.add(predicted_sense, gold_sense)
    return sense_cm


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate system's output against the gold standard based on partial matches")
    parser.add_argument('gold', help='Gold standard file')
    parser.add_argument('predicted', help='System output file')
    args = parser.parse_args()
    gold_list = [json.loads(x) for x in open(args.gold)]
    predicted_list = [json.loads(x) for x in open(args.predicted)]
    partial_evaluate(gold_list, predicted_list, 0.7)

if __name__ == '__main__':
    main()
