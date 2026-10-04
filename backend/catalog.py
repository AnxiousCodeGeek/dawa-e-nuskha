"""Local retail catalog: reference candidates, never handwriting confirmation."""
import json
import re
from collections import defaultdict
from pathlib import Path


def medicine_query(name):
    cleaned = re.sub(r'^(?:t\.|tab\.?|tablet|cap\.?|capsule|syp\.?|syrup)\s+', '', name.strip(), flags=re.I)
    return re.sub(r'[.…?]+$', '', cleaned).strip()[:200]


def normalized_name(name):
    return re.sub(r'[^a-z0-9]+', ' ', medicine_query(name).lower()).strip()


def grams(value):
    return {value[i:i+3] for i in range(max(0, len(value)-2))}


class Catalog:
    def __init__(self, path=None):
        rows = json.loads((Path(path) if path else Path(__file__).parent/'data/catalog-records.json').read_text())
        self.records, self.exact, self.postings = [], defaultdict(list), defaultdict(list)
        for row in rows:
            name, manufacturer, pack, url, number = row
            record = {'name': str(name), 'manufacturer': str(manufacturer), 'pack': str(pack),
                      'url': str(url), 'row': number, 'key': normalized_name(str(name))}
            record['grams'] = grams(record['key'])
            index = len(self.records)
            self.records.append(record)
            self.exact[record['key']].append(index)
            for gram in record['grams']:
                self.postings[gram].append(index)

    def lookup(self, name):
        query = normalized_name(name)
        if len(query) < 3 or len(query) > 80 or len(query.split()) > 6:
            return []
        found = [(i, 1) for i in self.exact.get(query, [])]
        if not found:
            query_grams, counts = grams(query), defaultdict(int)
            for gram in query_grams:
                for i in self.postings.get(gram, []):
                    counts[i] += 1
            for i, count in counts.items():
                rec = self.records[i]
                denominator = len(query_grams)+len(rec['grams'])
                score = .9 if rec['key'].startswith(query) and len(query) >= 4 else 2*count/denominator if denominator else 0
                if score >= .7:
                    found.append((i, score))
            found.sort(key=lambda item: (-item[1], item[0]))
        seen, output = set(), []
        for i, score in found:
            rec = self.records[i]
            key = rec['key'], rec['manufacturer'], rec['pack']
            if key in seen:
                continue
            seen.add(key)
            output.append({k: rec[k] for k in ('name', 'manufacturer', 'pack', 'url')} | {
                'id': f'pk-row-{rec["row"]}', 'country': 'Pakistan',
                'source': 'User-supplied Pakistani retail catalog — unverified',
                'review_status': 'unverified', 'match_method': 'exact_name' if score == 1 else 'similar_spelling'})
            if len(output) == 6:
                break
        return output
