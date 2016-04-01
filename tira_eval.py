#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The evaluator used on the TIRA evaluation plaform for CoNLL 2016 Shared Task

"""
import json
import sys
from scorer import evaluate
from partial_scorer import partial_evaluate
from validator import validate_relation_list, identify_language

def write_proto_text(key, value, f):
    f.write('measure {\n key: "%s" \n value: "%s"\n}\n' % (key ,round(value, 4)))

def write_results(prefix, result_tuple, output_file):
    connective_cm, arg1_cm, arg2_cm, rel_arg_cm, sense_cm, precision, recall, f1 = result_tuple
    write_proto_text('%s Parser precision' % prefix, precision, output_file)
    write_proto_text('%s Parser recall' % prefix, recall, output_file)
    write_proto_text('%s Parser f1' % prefix, f1, output_file)

    p, r, f = connective_cm.get_prf('yes')
    write_proto_text('%s Explicit connective precision' % prefix, p, output_file)
    write_proto_text('%s Explicit connective recall' % prefix, r, output_file)
    write_proto_text('%s Explicit connective f1' % prefix, f, output_file)

    p, r, f = arg1_cm.get_prf('yes')
    write_proto_text('%s Arg1 extraction precision' % prefix, p, output_file)
    write_proto_text('%s Arg1 extraction recall' % prefix, r, output_file)
    write_proto_text('%s Arg1 extraction f1' % prefix, f, output_file)

    p, r, f = arg2_cm.get_prf('yes')
    write_proto_text('%s Arg2 extraction precision' % prefix, p, output_file)
    write_proto_text('%s Arg2 extraction recall' % prefix, r, output_file)
    write_proto_text('%s Arg2 extraction f1' % prefix, f, output_file)

    p, r, f = rel_arg_cm.get_prf('yes')
    write_proto_text('%s Arg 1 Arg2 extraction precision' % prefix, p, output_file)
    write_proto_text('%s Arg 1 Arg2 extraction recall' % prefix, r, output_file)
    write_proto_text('%s Arg 1 Arg2 extraction f1' % prefix, f, output_file)

def write_partial_match_results(prefix, result_tuple, output_file):
    arg1_match_prf, arg2_match_prf, entire_relation_match_prf, parser_prf = result_tuple

    precision, recall, f1 = parser_prf
    write_proto_text('%s Parser precision' % prefix, precision, output_file)
    write_proto_text('%s Parser recall' % prefix, recall, output_file)
    write_proto_text('%s Parser f1' % prefix, f1, output_file)

    precision, recall, f1 = arg1_match_prf
    write_proto_text('%s Arg1 extraction precision' % prefix, precision, output_file)
    write_proto_text('%s Arg1 extraction recall' % prefix, recall, output_file)
    write_proto_text('%s Arg1 extraction f1' % prefix, f1, output_file)

    precision, recall, f1 = arg2_match_prf
    write_proto_text('%s Arg2 extraction precision' % prefix, precision, output_file)
    write_proto_text('%s Arg2 extraction recall' % prefix, recall, output_file)
    write_proto_text('%s Arg2 extraction f1' % prefix, f1, output_file)

    precision, recall, f1 = entire_relation_match_prf
    write_proto_text('%s Arg 1 Arg2 extraction precision' % prefix, precision, output_file)
    write_proto_text('%s Arg 1 Arg2 extraction recall' % prefix, recall, output_file)
    write_proto_text('%s Arg 1 Arg2 extraction f1' % prefix, f1, output_file)


def main(args):
    input_dataset = args[1]
    input_run = args[2]
    output_dir = args[3]

    gold_relations = [json.loads(x) for x in open('%s/relations.json' % input_dataset)]
    predicted_relations = [json.loads(x) for x in open('%s/output.json' % input_run)]

    language = identify_language(gold_relations)
    all_correct = validate_relation_list(predicted_relations, language)
    if not all_correct:
        exit(1)

    output_file = open('%s/evaluation.prototext' % output_dir, 'w')
    print 'Evaluation for all discourse relations'
    write_results('All', evaluate(gold_relations, predicted_relations), output_file)

    print 'Evaluation for explicit discourse relations only'
    explicit_gold_relations = [x for x in gold_relations if x['Type'] == 'Explicit']
    explicit_predicted_relations = [x for x in predicted_relations if x['Type'] == 'Explicit']
    write_results('Explicit only', \
        evaluate(explicit_gold_relations, explicit_predicted_relations), output_file)

    print 'Evaluation for non-explicit discourse relations only (Implicit, EntRel, AltLex)'
    non_explicit_gold_relations = [x for x in gold_relations if x['Type'] != 'Explicit']
    non_explicit_predicted_relations = [x for x in predicted_relations if x['Type'] != 'Explicit']
    write_results('Non-explicit only', \
        evaluate(non_explicit_gold_relations, non_explicit_predicted_relations), output_file)

    print '\nPartial Evaluation for all discourse relations'
    write_partial_match_results('All (partial match)', \
        partial_evaluate(gold_relations, predicted_relations, 0.7), output_file)
    print '\nPartial Evaluation for explicit discourse relations'
    write_partial_match_results('Explicit only (partial match)', \
        partial_evaluate(explicit_gold_relations, explicit_predicted_relations, 0.7), output_file)
    print '\nPartial Evaluation for non-explicit discourse relations only (Implicit, EntRel, AltLex)'
    write_partial_match_results('Non-explicit only (partial match)', \
        partial_evaluate(non_explicit_gold_relations, non_explicit_predicted_relations, 0.7), output_file)

    output_file.close()

if __name__ == '__main__':
    main(sys.argv)
