"""Scorer for partial argument match

"""

import argparse
import json

import validator
import aligner
import scorer

from confusion_matrix import ConfusionMatrix, Alphabet
from conn_head_mapper import ConnHeadMapper

def partial_evaluate(gold_list, predicted_list, partial_match_cutoff):
    """Evaluate the parse output with partial matching for arguments
    """
    print 'Aligning relations - This will time out after 120 seconds'
    arg1_alignment, arg2_alignment, relation_alignment = \
        aligner.align_relations(gold_list, predicted_list, partial_match_cutoff)
    arg1_match_prf, arg2_match_prf, total_match_prf = \
        evaluate_args(arg1_alignment, arg2_alignment, partial_match_cutoff)
    entire_relation_match_prf = \
        evaluate_rel_arg_whole_rel(relation_alignment, partial_match_cutoff)
    valid_senses = validator.identify_valid_senses(gold_list)
    sense_cm = evaluate_sense(relation_alignment, valid_senses)

    print 'Arg 1 extractor (partial matching)                     : Precision %1.4f Recall %1.4f F1 %1.4f' % arg1_match_prf
    print 'Arg 2 extractor (partial matching)                     : Precision %1.4f Recall %1.4f F1 %1.4f' % arg2_match_prf

    print 'Concatenated Arg 1 Arg 2 extractor (partial matching)  : Precision %1.4f Recall %1.4f F1 %1.4f' % total_match_prf

    print 'Conjunctive Arg 1 & Arg 2 extractor (partial matching) : Precision %1.4f Recall %1.4f F1 %1.4f' % entire_relation_match_prf

    print 'Sense classification--------------'
    sense_cm.print_summary()
    print 'Overall parser performance (cutoff = %s)--------------' % partial_match_cutoff
    precision, recall, f1 = sense_cm.compute_micro_average_f1()
    print 'Precision %1.4f Recall %1.4f F1 %1.4f' % (precision, recall, f1)

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
    if total_predicted == 0:
        precision = 1.0
    else:
        precision = total_correct / total_predicted
    if total_gold == 0:
        recall = 1.0
    else:
        recall = total_correct / total_gold
    f1_score = 2.0 * (precision * recall) / (precision + recall) \
        if precision + recall != 0 else 0.0
    return (round(precision, 4), round(recall, 4), round(f1_score,4))


def evaluate_sense(relation_pairs, valid_senses):
    sense_alphabet = Alphabet()
    for g_relation, _ in relation_pairs:
        if g_relation is not None:
            sense = g_relation['Sense'][0]
            if sense in valid_senses:
                sense_alphabet.add(sense)
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
            if gold_sense in valid_senses:
                sense_cm.add(ConfusionMatrix.NEGATIVE_CLASS, gold_sense)
        else:
            predicted_sense = p_relation['Sense'][0]
            gold_sense = g_relation['Sense'][0]
            if gold_sense in valid_senses:
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
    print '\n================================================'
    print 'Evaluation for all discourse relations'
    partial_evaluate(gold_list, predicted_list, 0.7)

    print '\n================================================'
    print 'Evaluation for explicit discourse relations only'
    explicit_gold_list = [x for x in gold_list if x['Type'] == 'Explicit']
    explicit_predicted_list = [x for x in predicted_list if x['Type'] == 'Explicit']
    partial_evaluate(explicit_gold_list, explicit_predicted_list, 0.7)

    print '\n================================================'
    print 'Evaluation for non-explicit discourse relations only (Implicit, EntRel, AltLex)'
    non_explicit_gold_list = [x for x in gold_list if x['Type'] != 'Explicit']
    non_explicit_predicted_list = [x for x in predicted_list if x['Type'] != 'Explicit']
    partial_evaluate(non_explicit_gold_list, non_explicit_predicted_list, 0.7)

if __name__ == '__main__':
    main()
