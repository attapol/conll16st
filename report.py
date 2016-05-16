"""Generate tsv format files from a directory of result zip files 

CoNLL 2016 Shared Task results are downloaded from TIRA and sent to
participants. This script generates tsv file that summarizes all zip files
in the same directory

python report.py dir_with_zip_files > result_table.tsv
"""
import zipfile
import glob
import re
import sys

def main(dir_name):
    file_names = glob.glob('%s/*.zip' % dir_name)
    first = True
    for file_name in file_names:
        z = zipfile.ZipFile(file_name)
        for x in z.namelist():
            if 'evaluation.prototext' in x:
                result_proto = z.open(x).read()
                result_tuples =  re.findall('key: "([^"]+)" \n value: "([^"]+)"', result_proto)
                if first:
                    print '\t'.join(['file'] + [k for k, _ in result_tuples])
                    first = False
                print '\t'.join([file_name] + [v for _, v in result_tuples])

if __name__ == '__main__':
    dir_name = sys.argv[1] 
    main(dir_name)
