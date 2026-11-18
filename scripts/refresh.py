"""Create a complete public snapshot and retain observed changes, without inventing history."""
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json,re
from urllib.parse import urljoin,urlsplit
from urllib.request import urlopen,Request
from bs4 import BeautifulSoup
from source import features,bounds

ROOT=Path(__file__).resolve().parents[1]
TOWNSHIP='https://services5.arcgis.com/frpHL0Fv8koQRVWY/arcgis/rest/services/DevelopmentActivity_WebApp2018_vw/FeatureServer/0'
CITY='https://www.langleycity.ca/business-development/development/development-application-portal'
FIELDS='OBJECTID,Project_Number,Folder_number,Application_Date,Subject,PURPOSE,FOLDER_STATUS,CommunityName,OurCityLink'

def text(value):return re.sub(r'\s+',' ',str(value or '')).strip()
def safe_url(value, base=CITY):
    if not value:return ''
    url=urljoin(base,str(value or ''));parts=urlsplit(url)
    if parts.scheme=='https' and parts.hostname and not parts.username:return url
    return ''

def township():
    records={}
    for f in features(TOWNSHIP,FIELDS):
        p=f['properties'];folder=text(p.get('Folder_number'))
        if not folder:raise ValueError('Missing Township folder number')
        key='township:'+folder
        record={'id':key,'jurisdiction':'Township','title':text(p.get('Subject')) or folder,'project':text(p.get('Project_Number')),
                'application':folder,'date':text(p.get('Application_Date'))[:10], 'status':text(p.get('FOLDER_STATUS')) or 'Not supplied',
                'community':text(p.get('CommunityName')) or 'Not supplied','description':text(p.get('PURPOSE')),
                'url':safe_url(p.get('OurCityLink')),'documents':[],'milestones':[],
                'geometry':f['geometry'],'bbox':bounds(f['geometry'])}
        if key in records:
            # A folder may cover multiple mapped parcels. Preserve every parcel.
            old=records[key]; geoms=[old['geometry'],record['geometry']];polys=[]
            for g in geoms:
                polys.extend(g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']])
            old['geometry']={'type':'MultiPolygon','coordinates':polys};old['bbox']=bounds(old['geometry'])
        else: records[key]=record
    return list(records.values())

def parse_city(html):
    soup=BeautifulSoup(html,'html.parser');records=[]
    for button in soup.select('button.accordion__trigger[aria-controls]'):
        title=text(button.get_text(' ',strip=True));section=soup.find(id=button['aria-controls'])
        if section is None:raise ValueError('Missing City project body')
        for br in section.select('br'):br.replace_with('\n')
        lines=[text(line) for p in section.select('p') for line in p.get_text(' ',strip=True).splitlines()]
        def field(label):
            labels=r'Current status|Description|Application type|Applicant contact|City staff contact|Application progress'
            match=re.search(r'(?:^|\s)'+re.escape(label)+r':\s*(.*?)(?=\s+(?:'+labels+r')\s*:|$)', ' '.join(lines), re.I)
            return match.group(1).strip() if match else ''
        status=field('Current status');description=field('Description')
        if not status or not description:raise ValueError('City project no longer matches expected schema: '+title)
        milestones=[]
        for p in section.select('p'):
            if 'application progress:' in text(p.get_text()).lower():
                ul=p.find_next_sibling('ul')
                if ul:milestones=[text(li.get_text(' ',strip=True)) for li in ul.find_all('li',recursive=False)]
        submitted=next((v.split(':',1)[1].strip() for v in milestones if v.lower().startswith('application submitted:')),'')
        try:date=datetime.strptime(submitted,'%B %d, %Y').date().isoformat()
        except ValueError:date=''
        documents=[];seen=set()
        for a in section.select('a[href]'):
            url=safe_url(a['href']);label=text(a.get_text(' ',strip=True))
            if url and label and url not in seen and not url.startswith('mailto:'):
                documents.append({'title':label,'url':url});seen.add(url)
        records.append({'id':'city:'+button['aria-controls'],'jurisdiction':'City','title':title,
                        'project':'','application':field('Application type'),'date':date,'status':status,
                        'community':'Langley City','description':description,'url':CITY+'#'+button['id'],
                        'documents':documents,'milestones':milestones,'geometry':None,'bbox':None})
    if len(records)<10:raise ValueError('City source unexpectedly small')
    return records

def city():
    with urlopen(Request(CITY,headers={'User-Agent':'CoolCode public-data explorer; https://coolcode.ca/'}),timeout=60) as response:
        return parse_city(response.read().decode('utf-8'))

TRACKED=('title','status','description','application','community','date','documents','milestones')
def reconcile(records, previous, day):
    old={r['id']:r for r in previous.get('records',[])};baseline=not old;result=[]
    if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate record IDs')
    for record in records:
        prior=old.pop(record['id'],None);r=dict(record)
        r['first_seen']=prior['first_seen'] if prior else day
        r['baseline']=prior.get('baseline',False) if prior else baseline
        r['history']=list(prior.get('history',[])) if prior else []
        if prior:
            changes={k:{'before':prior.get(k),'after':r.get(k)} for k in TRACKED if prior.get(k)!=r.get(k)}
            if prior.get('missing_since'):changes['listed']={'before':False,'after':True}
            if changes:r['history'].append({'date':day,'changes':changes})
        r['last_changed']=r['history'][-1]['date'] if r['history'] else ('' if r['baseline'] else day)
        r['missing_since']='';result.append(r)
    # Disappearance from a portal is not evidence of completion or cancellation.
    for r in old.values():
        r=dict(r)
        if not r.get('missing_since'):
            r['missing_since']=day
            r['last_changed']=day
            r['history']=list(r.get('history',[]))+[{'date':day,'changes':{'listed':{'before':True,'after':False}}}]
        result.append(r)
    return sorted(result,key=lambda r:r['id'])

def main():
    output=ROOT/'web/data/applications.json';previous=json.loads(output.read_text()) if output.exists() else {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(township);b=pool.submit(city);records=a.result()+b.result()
    for jurisdiction in ('City','Township'):
        count=sum(r['jurisdiction']==jurisdiction for r in records)
        old_count=sum(r['jurisdiction']==jurisdiction and not r.get('missing_since') for r in previous.get('records',[]))
        if old_count and count<old_count*.8:raise ValueError(f'{jurisdiction} source lost over 20%; review before replacing snapshot')
    now=datetime.now(timezone.utc).isoformat();day=now[:10]
    data={'retrieved_at':now,'tracking_started':previous.get('tracking_started',day),
          'sources':[{'name':'Township development activity map','url':TOWNSHIP},{'name':'City development application portal','url':CITY}],
          'records':reconcile(records,previous,day)}
    output.parent.mkdir(exist_ok=True);stage=output.with_suffix('.tmp');stage.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n');stage.replace(output)
    print('Refreshed',len(records),'listed applications;',len(data['records']),'including retained records')

if __name__=='__main__':main()
