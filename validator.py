#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CONLL Shared Task 2016 System output validator

It verifies that each line is
1) a well-formed json and readable by json.loads
2) a relation json looks similar to the one given in the training set
"""
import argparse
import json
import sys

RELATION_TYPES = ['Explicit', 'Implicit', 'AltLex', 'EntRel', 'NoRel']
EN_SENSES = [
    'Temporal.Asynchronous.Precedence',
    'Temporal.Asynchronous.Succession',
    'Temporal.Synchrony',
    'Contingency.Cause.Reason',
    'Contingency.Cause.Result',
    'Contingency.Condition',
    'Comparison.Contrast',
    'Comparison.Concession',
    'Expansion.Conjunction',
    'Expansion.Instantiation',
    'Expansion.Restatement',
    'Expansion.Alternative',
    'Expansion.Alternative.Chosen alternative',
    'Expansion.Exception',
    'EntRel',
    ]

ZH_SENSES = [
    'Alternative',
    'Causation',
    'Conditional',
    'Conjunction',
    'Contrast',
    'EntRel',
    'Expansion',
    'Progression',
    'Purpose',
    'Temporal',
    ]

def validate_file(file_name, language):
    lines = open(file_name)
    all_correct = True
    for i, line in enumerate(lines):
        try:
            print 'Validating line %s' % (i+1)
            relation = json.loads(line)
            check_type(relation)
            check_sense(relation, language)
            check_args(relation)
            check_connective(relation)
        except (ValueError, TypeError) as e:
            sys.stderr.write('\tLine %s %s\n' % ((i+1), e))
            all_correct = False
    return all_correct

def validate_relation_list(relation_list, language):
    all_correct = True
    for i, relation in enumerate(relation_list):
        try:
            check_type(relation)
            check_sense(relation, language)
            check_args(relation)
            check_connective(relation)
        except (ValueError, TypeError) as e:
            sys.stderr.write('Relation %s %s\n' % (i, e))
            all_correct = False
    return all_correct
 
def check_type(relation):
    if 'Type' not in relation:
        raise ValueError('Field \'Type\' is required but not found')
    relation_type = relation['Type']
    if relation_type not in RELATION_TYPES:
        raise ValueError('Invalid type of %s' % relation_type)
    if relation_type == 'NoRel':
        raise ValueError('NoRel should be removed as it is treated as a negative example')


def check_sense(relation, language):
    if 'Sense' not in relation:
        raise ValueError('Field \'Sense\' is required but not found')
    senses = relation['Sense']
    if not isinstance(senses, list):
        raise TypeError('Sense field must be a list of one element')
    if len(senses) > 1:
        raise TypeError('Sense field must be a list of one element. Got %s' % len(senses))
    sense = senses[0]
    if language == 'en':
        valid_senses = EN_SENSES
    elif language == 'zh':
        valid_senses = ZH_SENSES
    else:
        print 'Invalid language option'
        return
    if sense not in valid_senses:
        raise ValueError('Invalid sense of %s' % sense)

def check_args(relation):
    if 'Arg1' not in relation:
        raise ValueError('Field \'Arg1\' is required but not found')
    else:
        check_span(relation['Arg1'])
    if 'Arg2' not in relation:
        raise ValueError('Field \'Arg2\' is required but not found')
    else:
        check_span(relation['Arg2'])

def check_connective(relation):
    if 'Connective' not in relation:
        raise ValueError('Field \'Connective\' is required but not found')
    else:
        check_span(relation['Connective'])

def check_span(span):
    if 'TokenList' not in span:
        raise ValueError('Field \'TokenList\' is required but not found')
    if not isinstance(span['TokenList'], list):
        raise TypeError('TokenList field must a list of token indices')

def identify_language(g_relation_list):
    """Identify the language of the relation list based on senses
    """
    english = 0.0
    chinese = 0.0
    for relation in g_relation_list:
        sense = relation['Sense'][0]
        if sense in EN_SENSES:
            english += 1
        elif sense in ZH_SENSES:
            chinese += 1
    if english > chinese:
        return 'en'
    else:
        return 'zh'

def identify_valid_senses(g_relation_list):
    language = identify_language(g_relation_list)
    if language == 'en':
        return EN_SENSES
    else:
        return ZH_SENSES

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser('System output format validator')
    parser.add_argument('language', choices=['en','zh'], help='language of the output')
    parser.add_argument('system_output_file', help='output json file')
    args = parser.parse_args()
    validate_file(args.system_output_file, args.language)
