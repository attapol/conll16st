#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The Official CONLL 2016 Shared Task Scorer

"""
import argparse
import json

from confusion_matrix import ConfusionMatrix, Alphabet
from conn_head_mapper import ConnHeadMapper
import validator

CONN_HEAD_MAPPER = ConnHeadMapper()

def evaluate(gold_list, predicted_list):
    connective_cm = evaluate_connectives(gold_list, predicted_list)
    arg1_cm, arg2_cm, rel_arg_cm = evaluate_argument_extractor(gold_list, predicted_list)
    sense_cm = evaluate_sense(gold_list, predicted_list)

    print 'Explicit connectives         : Precision %1.4f Recall %1.4f F1 %1.4f' % connective_cm.get_prf('yes')
    print 'Arg 1 extractor              : Precision %1.4f Recall %1.4f F1 %1.4f' % arg1_cm.get_prf('yes')
    print 'Arg 2 extractor              : Precision %1.4f Recall %1.4f F1 %1.4f' % arg2_cm.get_prf('yes')
    print 'Arg1 Arg2 extractor combined : Precision %1.4f Recall %1.4f F1 %1.4f' % rel_arg_cm.get_prf('yes')
    print 'Sense classification--------------'
    sense_cm.print_summary()
    print 'Overall parser performance --------------'
    precision, recall, f1 = sense_cm.compute_micro_average_f1()
    print 'Precision %1.4f Recall %1.4f F1 %1.4f' % (precision, recall, f1)
    return connective_cm, arg1_cm, arg2_cm, rel_arg_cm, sense_cm, precision, recall, f1


def evaluate_argument_extractor(gold_list, predicted_list):
    """Evaluate argument extractor at Arg1, Arg2, and relation level

    """
    gold_arg1 = [(x['DocID'], x['Arg1']['TokenList']) for x in gold_list]
    predicted_arg1 = [(x['DocID'], x['Arg1']['TokenList']) for x in predicted_list]
    arg1_cm = compute_binary_eval_metric(gold_arg1, predicted_arg1, span_exact_matching)

    gold_arg2 = [(x['DocID'], x['Arg2']['TokenList']) for x in gold_list]
    predicted_arg2 = [(x['DocID'], x['Arg2']['TokenList']) for x in predicted_list]
    arg2_cm = compute_binary_eval_metric(gold_arg2, predicted_arg2, span_exact_matching)

    gold_arg12 = [(x['DocID'], (x['Arg1']['TokenList'], x['Arg2']['TokenList'])) \
            for x in gold_list]
    predicted_arg12 = [(x['DocID'], (x['Arg1']['TokenList'], x['Arg2']['TokenList'])) \
            for x in predicted_list]
    rel_arg_cm = compute_binary_eval_metric(gold_arg12, predicted_arg12, spans_exact_matching)
    return arg1_cm, arg2_cm, rel_arg_cm

def evaluate_connectives(gold_list, predicted_list):
    """Evaluate connective recognition accuracy for explicit discourse relations

    """
    explicit_gold_list = [(x['DocID'], x['Connective']['TokenList'], x['Connective']['RawText']) \
            for x in gold_list if x['Type'] == 'Explicit']
    explicit_predicted_list = [(x['DocID'], x['Connective']['TokenList']) \
            for x in predicted_list if x['Type'] == 'Explicit']
    connective_cm = compute_binary_eval_metric(
            explicit_gold_list, explicit_predicted_list, connective_head_matching)    
    return connective_cm

def spans_exact_matching(gold_doc_id_spans, predicted_doc_id_spans):
    """Matching two lists of spans

    Input:
        gold_doc_id_spans : (DocID , a list of lists of tuples of token addresses)
        predicted_doc_id_spans : (DocID , a list of lists of token indices)

    Returns:
        True if the spans match exactly
    """
    exact_match = True
    gold_docID = gold_doc_id_spans[0]
    gold_spans = gold_doc_id_spans[1]
    predicted_docID = predicted_doc_id_spans[0]
    predicted_spans = predicted_doc_id_spans[1]

    for gold_span, predicted_span in zip(gold_spans, predicted_spans):
        exact_match = span_exact_matching((gold_docID,gold_span), (predicted_docID, predicted_span)) \
                and exact_match
    return exact_match

def span_exact_matching(gold_span, predicted_span):
    """Matching two spans

    Input:
        gold_span : a list of tuples :(DocID, list of tuples of token addresses)
        predicted_span : a list of tuples :(DocID, list of token indices)

    Returns:
        True if the spans match exactly
    """
    gold_docID = gold_span[0]
    predicted_docID = predicted_span[0]
    gold_token_indices = [x[2] for x in gold_span[1]]
    predicted_token_indices = predicted_span[1]
    return gold_docID == predicted_docID and gold_token_indices == predicted_token_indices

def connective_head_matching(gold_raw_connective, predicted_raw_connective):
    """Matching connectives

    Input:
        gold_raw_connective : (DocID, a list of tuples of token addresses, raw connective token)
        predicted_raw_connective : (DocID, a list of tuples of token addresses)

    A predicted raw connective is considered iff
        1) the predicted raw connective includes the connective "head"
        2) the predicted raw connective tokens are the subset of predicted raw connective tokens

    For example:
        connective_head_matching('two weeks after', 'weeks after')  --> True
        connective_head_matching('two weeks after', 'two weeks')  --> False not covering head
        connective_head_matching('just because', 'because')  --> True
        connective_head_matching('just because', 'simply because')  --> False not subset
        connective_head_matching('just because', 'since')  --> False
    """
    gold_docID, gold_token_address_list, gold_tokens = gold_raw_connective
    predicted_docID, predicted_token_list = predicted_raw_connective
    if gold_docID != predicted_docID:
        return False

    gold_token_indices = [x[2] for x in gold_token_address_list]

    if gold_token_address_list == predicted_token_list:
        return True
    elif not set(predicted_token_list).issubset(set(gold_token_indices)):
        return False
    else:
        conn_head, indices = CONN_HEAD_MAPPER.map_raw_connective(gold_tokens)
        gold_head_connective_indices = [gold_token_indices[x] for x in indices]
        return set(gold_head_connective_indices).issubset(set(predicted_token_list))

def evaluate_sense(gold_list, predicted_list):
    """Evaluate sense classifier

    The label ConfusionMatrix.NEGATIVE_CLASS is for the relations 
    that are missed by the system
    because the arguments don't match any of the gold relations.
    """
    sense_alphabet = Alphabet()
    valid_senses = validator.identify_valid_senses(gold_list)
    for relation in gold_list:
        sense = relation['Sense'][0]
        if sense in valid_senses:
            sense_alphabet.add(sense)

    sense_alphabet.add(ConfusionMatrix.NEGATIVE_CLASS)

    sense_cm = ConfusionMatrix(sense_alphabet)
    gold_to_predicted_map, predicted_to_gold_map = \
            _link_gold_predicted(gold_list, predicted_list, spans_exact_matching)

    for i, gold_relation in enumerate(gold_list):
        gold_sense = gold_relation['Sense'][0]
        if gold_sense in valid_senses:
            if i in gold_to_predicted_map:
                predicted_sense = gold_to_predicted_map[i]['Sense'][0]
                if predicted_sense in gold_relation['Sense']:
                    sense_cm.add(predicted_sense, predicted_sense)
                else:
                    if not sense_cm.alphabet.has_label(predicted_sense):
                        predicted_sense = ConfusionMatrix.NEGATIVE_CLASS
                    sense_cm.add(predicted_sense, gold_sense)
            else:
                sense_cm.add(ConfusionMatrix.NEGATIVE_CLASS, gold_sense)

    for i, predicted_relation in enumerate(predicted_list):
        if i not in predicted_to_gold_map:
            predicted_sense = predicted_relation['Sense'][0]
            if not sense_cm.alphabet.has_label(predicted_sense):
                predicted_sense = ConfusionMatrix.NEGATIVE_CLASS
            sense_cm.add(predicted_sense, ConfusionMatrix.NEGATIVE_CLASS)
    return sense_cm


def combine_spans(span1, span2):
    """Merge two text span dictionaries

    """
    new_span = {}
    new_span['CharacterSpanList'] = span1['CharacterSpanList'] + span2['CharacterSpanList']
    new_span['SpanList'] = span1['SpanList'] + span2['SpanList']
    new_span['RawText'] = span1['RawText'] + span2['RawText']
    new_span['TokenList'] = span1['TokenList'] + span2['TokenList']
    return new_span

def compute_binary_eval_metric(gold_list, predicted_list, matching_fn):
    """Compute binary evaluation metric

    """
    binary_alphabet = Alphabet()
    binary_alphabet.add('yes')
    binary_alphabet.add('no')
    cm = ConfusionMatrix(binary_alphabet)
    matched_predicted = [False for x in predicted_list]
    for gold_span in gold_list:
        found_match = False
        for i, predicted_span in enumerate(predicted_list):
            if matching_fn(gold_span, predicted_span) and not matched_predicted[i]:
                cm.add('yes', 'yes')
                matched_predicted[i] = True
                found_match = True
                break
        if not found_match:
            cm.add('yes', 'no')
    # Predicted span that does not match with any
    for matched in matched_predicted:
        if not matched:
            cm.add('no', 'yes')
    return cm


def _link_gold_predicted(gold_list, predicted_list, matching_fn):
    """Link gold standard relations to the predicted relations

    A pair of relations are linked when the arg1 and the arg2 match exactly.
    We do this because we want to evaluate sense classification later.

    Returns:
        A tuple of two dictionaries:
        1) mapping from gold relation index to predicted relation index
        2) mapping from predicted relation index to gold relation index
    """
    gold_to_predicted_map = {}
    predicted_to_gold_map = {}
    gold_arg12_list = [(x['DocID'], (x['Arg1']['TokenList'], x['Arg2']['TokenList']))
            for x in gold_list]
    predicted_arg12_list = [(x['DocID'], (x['Arg1']['TokenList'], x['Arg2']['TokenList']))
            for x in predicted_list]
    for gi, gold_span in enumerate(gold_arg12_list):
        for pi, predicted_span in enumerate(predicted_arg12_list):
            if matching_fn(gold_span, predicted_span):
                gold_to_predicted_map[gi] = predicted_list[pi]
                predicted_to_gold_map[pi] = gold_list[gi]
    return gold_to_predicted_map, predicted_to_gold_map


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate system's output against the gold standard")
    parser.add_argument('gold', help='Gold standard file')
    parser.add_argument('predicted', help='System output file')
    args = parser.parse_args()
    gold_list = [json.loads(x) for x in open(args.gold)]
    predicted_list = [json.loads(x) for x in open(args.predicted)]
    print '\n================================================'
    print 'Evaluation for all discourse relations'
    evaluate(gold_list, predicted_list)

    print '\n================================================'
    print 'Evaluation for explicit discourse relations only'
    explicit_gold_list = [x for x in gold_list if x['Type'] == 'Explicit']
    explicit_predicted_list = [x for x in predicted_list if x['Type'] == 'Explicit']
    evaluate(explicit_gold_list, explicit_predicted_list)

    print '\n================================================'
    print 'Evaluation for non-explicit discourse relations only (Implicit, EntRel, AltLex)'
    non_explicit_gold_list = [x for x in gold_list if x['Type'] != 'Explicit']
    non_explicit_predicted_list = [x for x in predicted_list if x['Type'] != 'Explicit']
    evaluate(non_explicit_gold_list, non_explicit_predicted_list)

if __name__ == '__main__':
    main()

