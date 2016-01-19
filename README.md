# Official Github Repo for CoNLL 2016 Shared Task 


## Validator
The validator is provided to make sure the discourse parser output is in the right format. 
In this version of the task, language must be specified when validating the output.
Sample usage:

```
python2.7 validator.py en tutorial/output.json
```

If you would like to see what the error messages look like, try running:

```
python2.7 validator.py en tutorial/faulty_output.json
```

## Scorer
The official scorer for the final evaluation is used to calculate evaluation metrics for argument labeler, connective detection, sense classification, and overall parsing performance.
The scorer gives quite detailed scores for analytical purposes. We also provide scoring based on partial matching of argument. The detail on how partial matching criteria are computed can be found in the task blog.

The output should be validated without any error. The scorer will fail silently if the output is not in the right format or validated.

Sample usage:

```
python2.7 scorer.py tutorial/conll16st-en-01-12-16-trial/relations.json tutorial/output.json
```

## TIRA scorer
This is the scorer that is used in the TIRA evaluation platform. You should check this out and try to run this offline and see if your parser outputs the right kind of format. 

Sample usage:

First, run your parser on the dataset. Your parser should load the parses from `path/to/data_dir`, use `path/to/model_dir/` for model and other resources and produce the output file in `path/to/outputdir/output.json`. We will use the sample parser as an example:

```
python2.7 sample_parser.py path/to/data_dir path/to/model_dir path/to/output_dir
ls -l path/to/output_dir/output.json
```

Next, run the TIRA scorer on it:

```
python2.7 tira_eval.py path/to/data_dir path/to/output_dir path/to/result_dir
```

The evaluation will be done on the gold standard in `path/to/data_dir` and the predictions in `path/to/output_dir` and the results will be put in `path/to/result_dir/evaluation.prototext`, which looks like:

```
measure {
 key: "Parser precision"
 value: "0.0373"
}
measure {
 key: "Parser recall"
 value: "0.0418"
}
measure {
 key: "Parser f1"
 value: "0.0394"
}
...
```
