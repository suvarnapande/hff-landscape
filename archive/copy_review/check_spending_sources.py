"""Cache public World Bank 2022 spending/PPP availability; do not fill site data."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode

out = Path(__file__).resolve().parent.parent / 'spending_source_review'
out.mkdir(exist_ok=True)
jobs = [('PRI;XKX;BMU;GRL', code) for code in
        ['SH.XPD.CHEX.PP.CD', 'SH.XPD.CHEX.GD.ZS', 'PA.NUS.PPP']]
jobs.append(('TWN', 'SH.XPD.CHEX.PP.CD'))
def fetch(job):
    countries, indicator = job
    url = f'https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}'
    try:
        url += '?' + urlencode({'format':'json','date':'2022','per_page':100})
        with urlopen(url, timeout=25) as response:
            data = json.load(response)
        (out / f'{countries.replace(";", "_")}_{indicator}.json').write_text(
            json.dumps({'url':url,'data':data}, ensure_ascii=False, indent=2), encoding='utf-8')
        return (indicator, [(v['country']['value'], v['date'], v['value']) for v in data[1]]
                if len(data)>1 and data[1] else data)
    except Exception as error:
        return indicator, str(error)
with ThreadPoolExecutor(max_workers=4) as executor:
    for result in executor.map(fetch,jobs):
        print(result,flush=True)
