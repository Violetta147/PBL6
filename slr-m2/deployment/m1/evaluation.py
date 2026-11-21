"""Descriptive interval comparison against explicitly selected manual revisions."""
from pathlib import Path
from .common import read,write

def evaluate(run, revisions):
    run=Path(run)
    automatic=[s for s in read(run/'events.json') if s.get('status')=='complete']
    manual=[]
    for revision in revisions:
        path=(run/'annotations'/f'{revision}.json').resolve()
        if path.parent != (run/'annotations').resolve():
            raise ValueError('Invalid revision')
        manual.append(read(path))
    if not manual:
        raise ValueError('Select manual revision IDs for the reference intervals')
    manual.sort(key=lambda s:s['start'])
    if any(a['end']>b['start'] for a,b in zip(manual,manual[1:])):
        raise ValueError('Reference intervals overlap; select one revision per movement')
    def overlap(a,b):
        return max(0.,min(a['end'],b['end'])-max(a['start'],b['start']))
    rows=[]
    for reference in manual:
        matches=[s for s in automatic if overlap(s,reference)>0]
        intervals=sorted((max(s['start'],reference['start']),min(s['end'],reference['end'])) for s in matches)
        covered=0.; right=reference['start']
        for start,end in intervals:
            covered+=max(0.,end-max(start,right));right=max(right,end)
        rows.append(dict(revision=reference['revision'],matches=[s['segment_id'] for s in matches],
                         missed=not matches,coverage=covered/(reference['end']-reference['start']),
                         start_error=min((s['start'] for s in matches),default=reference['start'])-reference['start'] if matches else None,
                         end_error=max((s['end'] for s in matches),default=reference['end'])-reference['end'] if matches else None))
    unmatched=[s['segment_id'] for s in automatic if not any(overlap(s,m)>0 for m in manual)]
    report=dict(schema_version='m1.v1',references=rows,unmatched_automatic=unmatched,
                false_splits=sum(len(r['matches'])>1 for r in rows),
                false_merges=sum(sum(overlap(a,m)>0 for m in manual)>1 for a in automatic),
                recommendation='Review boundary failures and reserved recordings before M2',
                limitations=['Unmatched segments require review as idle triggers or omitted annotations.',
                             'Manual labels and reserved recording membership are not certified automatically.'])
    write(run/'evaluation.json',report)
    return report
