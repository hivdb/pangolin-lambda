import os
import sys
import csv
import json
import boto3
import hashlib
import subprocess
from datetime import datetime

from pangolin import __version__ as pangolin_version
from pangolin_data import __version__ as pangodata_version


def main(event, context):
    version = 'pangolin: {}; pangolin-data: {}'.format(
        pangolin_version, pangodata_version)
    fasta = event.get('body') or ''
    runhash = hashlib.sha512(fasta.encode('utf-8')).hexdigest()
    with open('/tmp/input.fasta', 'w') as fp:
        fp.write(fasta)
    proc = subprocess.run(
        ['/var/lang/bin/pangolin',
         '/tmp/input.fasta',
         '-o', '/tmp',
         '--outfile', 'lineage-report.csv'],
        capture_output=True,
        encoding='UTF-8'
    )
    results = {
        "runHash": runhash,
        "version": version,
        "reportTimestamp": datetime.utcnow().isoformat() + "Z",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    rows = []
    if os.path.isfile('/tmp/lineage-report.csv'):
        with open('/tmp/lineage-report.csv') as fp:
            for row in csv.DictReader(fp):
                # explict list fields in case pangolin added more columns
                if row['conflict'] == 'NA':
                    conflict = None
                    probability = None
                else:
                    try:
                        conflict = float(row['conflict'])
                    except ValueError:
                        conflict = 0
                    probability = 1 - conflict
                rows.append({
                    'taxon': row['taxon'],
                    'lineage': row['lineage'],
                    'probability': probability,
                    'conflict': conflict,
                    'status': row['qc_status'],
                    'note': row['note'],
                })
    else:
        rows = []
        for line in fasta.splitlines():
            if line.startswith('>'):
                rows.append({
                    'taxon': line[1:],
                    'lineage': 'Unassigned',
                    'probability': 1,
                    'conflict': 0,
                    'status': 'failed',
                    'note': 'pangolin crashed'
                })
    results['reports'] = rows
    body = json.dumps(results)
    s3_client = boto3.client('s3')
    s3_client.put_object(
        Body=version.encode('utf-8'),
        Bucket='pangolin-assets.hivdb.org',
        Key='latest_version')
    s3_client.put_object(
        Body=body.encode('utf-8'),
        Bucket='pangolin-assets.hivdb.org',
        Key='reports/{}.json'.format(runhash))
    return {
        'statusCode': 200,
        'header': {
            'Content-Type': 'application/json'
        },
        'body': body
    }
