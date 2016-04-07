#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sample Discourse Relation Classifier

ready for evaluation on TIRA evaluation system (supplementary evaluation)

The parse should take three arguments

	$inputDataset = the folder of the dataset to parse.
		The folder structure is the same as in the tar file
		$inputDataset/parses.json
		$inputDataset/relations-no-senses.json

	$inputRun = the folder that contains the model file or other resources

	$outputDir = the folder that the parser will output 'output.json' to

Note that we have to fill in 'Type' field as Explicti and Implicit, 
but that will be overridden by the evaluator. 
"""
import codecs
import json
import random
import sys

import conll16st.validator

class DiscourseParser(object):
    """Sample discourse relation sense classifier
    
    This simply classifies each instance randomly. 
    """

    def __init__(self):
        pass

    def classify_sense(self, data_dir, output_dir, valid_senses):
        relation_file = '%s/relations-no-senses.json' % data_dir
        parse_file = '%s/parses.json' % data_dir
        parse = json.load(codecs.open(parse_file, encoding='utf8'))

        relation_dicts = [json.loads(x) for x in open(relation_file)]

        output = codecs.open('%s/output.json' % output_dir, 'wb', encoding ='utf8')
        random.seed(10)
        for i, relation_dict in enumerate(relation_dicts):
            sense = valid_senses[random.randint(0, len(valid_senses)-1)]
            relation_dict['Sense'] = [sense]
            relation_dict['Arg1']['TokenList'] = \
                    [x[2] for x in relation_dict['Arg1']['TokenList']]
            relation_dict['Arg2']['TokenList'] = \
                    [x[2] for x in relation_dict['Arg2']['TokenList']]
            relation_dict['Connective']['TokenList'] = \
                    [x[2] for x in relation_dict['Connective']['TokenList']]
            if len(relation_dict['Connective']['TokenList']) > 0:
                relation_dict['Type'] = 'Explicit'
            else:
                relation_dict['Type'] = 'Implicit'
            output.write(json.dumps(relation_dict) + '\n')

if __name__ == '__main__':
    language = sys.argv[1]
    input_dataset = sys.argv[2]
    input_run = sys.argv[3]
    output_dir = sys.argv[4]
    if language == 'en':
        valid_senses = validator.EN_SENSES
    elif language == 'zh':
        valid_senses = validator.ZH_SENSES
    parser = DiscourseParser()
    parser.classify_sense(input_dataset, output_dir, valid_senses)

