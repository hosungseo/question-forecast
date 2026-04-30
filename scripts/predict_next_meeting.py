#!/usr/bin/env python3
"""Generate next-cabinet-meeting issue radar from recent Naver News.

v2 improvements:
- merge duplicate issue queries into canonical issue groups
- filter election/personality-noise unless it is tied to a government policy issue
- score by policy signal, article volume, recency, and issue severity
- generate issue-specific question packets rather than only ministry templates
"""
from __future__ import annotations
import datetime as dt, html, json, os, re, time, urllib.parse, urllib.request
from collections import defaultdict, Counter
from pathlib import Path
from question_patterns import synthesize_questions
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'next_meeting_radar.md'
JSON_OUT=ROOT/'data'/'next_meeting_radar.json'
ISSUES={
 'school_field_trip': {
  'ministry':'교육부', 'queries':['초등학교 소풍 수학여행 교사 책임','현장체험학습 교사 책임','교육부 현장체험학습','소풍 수학여행 면책권'],
  'signals':['소풍','수학여행','현장체험학습','교사','면책','책임','안전사고','교육부'],
  'questions':['소풍이나 수학여행도 수업의 일부인데, 안전사고가 걱정된다고 아예 안 가는 식으로 굳어지면 교육 기회를 줄이는 것 아닌지?','현장에서는 교사가 책임질까 봐 못 움직이고, 학부모는 아이가 못 가서 불만이면 결국 제도 설계가 현장을 막고 있는 것 아닌지?','아이들이 학교에 따라 어떤 곳은 가고 어떤 곳은 못 가면, 이것도 교육 격차가 되는 것 아닌지?']},
 'disaster_safety': {
  'ministry':'행정안전부','queries':['산불 재난 안전','행안부 재난 안전','침수 지하차도 안전','화재 재난 안전'],
  'signals':['산불','재난','안전','화재','침수','지하차도','오송','행안부'],
  'questions':['침수나 산불 같은 것은 일이 터진 뒤 수습하는 것보다, 국민이 미리 피하게 만드는 게 국가의 역할 아닌지?','지자체가 현장을 제일 잘 안다고 하지만, 역량이 부족한 곳에서 사고가 반복되면 중앙정부가 그냥 지켜볼 수는 없는 것 아닌지?','위험 정보가 있는데도 국민 휴대전화와 내비게이션까지 제때 가지 않으면, 시스템이 있어도 없는 것과 같은 것 아닌지?']},
 'real_estate': {
  'ministry':'국토교통부','queries':['부동산 공급 전세','전월세 시장 불안','주택 공급 대책'],
  'signals':['부동산','주택','전세','월세','공급','정비사업','아파트'],
  'questions':['공급 대책을 발표해도 실제 입주까지 시간이 오래 걸리면, 국민 입장에서는 대책이 없는 것처럼 느끼는 것 아닌지?','집값과 전월세 문제는 숫자보다 불안 심리가 먼저 움직이는데, 정부가 시장의 기대를 어떻게 잡을 것인지?','수도권과 지방 문제가 전혀 다른데 하나의 처방으로 해결하려고 하면 효과가 떨어지는 것 아닌지?','공급을 늘린다고 했는데 국민이 들어가 살 집으로 이어지지 않으면 결국 행정 절차만 돈 것 아닌지?']},
 'prices_livelihood': {
  'ministry':'기획재정부','queries':['물가 민생 지원','고유가 지원금 물가','민생경제 물가 부담'],
  'signals':['물가','민생','지원','고유가','경제','부담','추경','예산'],
  'questions':['국민은 평균 물가가 아니라 장바구니와 기름값으로 고통을 느끼는데, 정부 대책도 그 체감 지점에서 출발해야 하는 것 아닌지?','지원은 했다고 하는데 실제 부담이 그대로면, 정책이 국민에게 도착하지 못한 것 아닌지?','어려울 때 쓰려고 재정이라는 제도가 있는 것인데, 지금 무엇을 아끼고 무엇은 과감히 써야 하는지 정리해야 하는 것 아닌지?','대책이 부처별로 흩어지면 국민은 아무도 책임지지 않는다고 느낄 텐데, 민생 대응의 중심을 어디에 둘 것인지?']},
 'finance_rates': {
  'ministry':'금융위원회','queries':['금융 대출 금리','중금리대출 확대','서민금융 대출 부담'],
  'signals':['금융','대출','금리','은행','중금리','서민금융','취약계층'],
  'questions':['금융이 필요한 사람에게는 안 가고 안전한 사람에게만 가면, 정책금융이라는 이름이 무색한 것 아닌지?','서민금융을 늘린다고 해도 실제로 부담이 줄지 않으면 은행권 관리만 한 것이지 국민을 도운 것은 아닌 것 아닌지?','금융 지원이 투기 쪽으로 흐르지 않고 생산과 민생으로 가게 하는 장치가 핵심 아닌지?','돈이 필요한 곳은 막히고 돈이 넘치는 곳에는 더 몰리면, 금융정책이 불평등을 키우는 것 아닌지?']},
 'labor_jobs': {
  'ministry':'고용노동부','queries':['청년 일자리','산재 원청 책임','임금체불 하도급'],
  'signals':['일자리','청년','산재','원청','임금체불','하도급','노동'],
  'questions':['현장에서 다치고 임금을 못 받는 사람이 계속 나오면, 숫자가 좋아도 국민은 좋아졌다고 느끼기 어려운 것 아닌지?','원청은 이익을 가져가고 책임은 하청과 노동자에게 내려가면, 그 구조를 그냥 시장 문제라고 볼 수는 없는 것 아닌지?','제재를 받아도 계속하는 게 이익이면, 제도가 오히려 위반을 허용하는 것 아닌지?','일하는 사람이 제일 약한 고리로 남아 있으면, 정부가 말하는 노동 보호가 현장에서는 빈말이 되는 것 아닌지?']},
 'justice_reform': {
  'ministry':'법무부','queries':['검찰개혁 법무부','범죄 수사 법무부','캄보디아 범죄 한국인'],
  'signals':['검찰','개혁','범죄','수사','법무부','재판','증거'],
  'questions':['기관 권한을 어떻게 나눌지가 아니라, 국민 입장에서 범죄 피해를 막고 재판까지 가게 하는 힘이 약해지면 안 되는 것 아닌지?','수사체계를 고친다고 하면서 실제 범죄 대응력이 떨어지면, 제도개혁의 목적을 놓치는 것 아닌지?','피해자 보호보다 기관 논쟁이 앞서면 국민은 국가가 누구 편인지 묻게 되는 것 아닌지?','권한을 나누는 문제보다 나쁜 사람이 빠져나가지 못하게 하는 것이 먼저 아닌지?']},
 'medical': {
  'ministry':'보건복지부','queries':['의료대란 전공의 복귀','의대 전공의 복귀','비상진료체계'],
  'signals':['의료','전공의','의대','비상진료','환자','병원'],
  'questions':['의료 문제는 제도 논쟁도 중요하지만, 국민 입장에서는 지금 아플 때 치료받을 수 있느냐가 먼저 아닌지?','비상진료가 오래가면 비상이 아니라 일상이 되는 것인데, 그렇게 두면 지역과 필수의료가 더 약해지는 것 아닌지?','의료인력 문제를 서로 책임 공방으로만 끌고 가면 환자 불편은 누가 책임지는 것인지?','지역에서는 병원을 찾아다니는 것 자체가 고통인데, 이걸 단순한 의료계 갈등으로만 볼 수는 없는 것 아닌지?']},
}
NOISE_TERMS=['출마','예비후보','후보','공천','선거사무소','단일화','여론조사','지지율','민주당','국민의힘','개혁신당','시장 선거','도지사','시의원','지선','영입']
POLICY_ALLOW=['정책','공급','물가','안전','교육','복지','의료','재난','대출','금리','검찰개혁','산재','임금체불','하도급','전공의','의대','전세','지하차도']

def strip(s): return re.sub(r'<[^>]+>','',html.unescape(s or '')).strip()
def search(q,display=10):
    cid=os.environ['NAVER_CLIENT_ID']; sec=os.environ['NAVER_CLIENT_SECRET']
    url='https://openapi.naver.com/v1/search/news.json?'+urllib.parse.urlencode({'query':q,'display':display,'sort':'date'})
    req=urllib.request.Request(url,headers={'X-Naver-Client-Id':cid,'X-Naver-Client-Secret':sec,'User-Agent':'Mozilla/5.0'})
    data=json.load(urllib.request.urlopen(req,timeout=15)); time.sleep(0.08)
    out=[]
    for it in data.get('items',[]):
        try: pub=dt.datetime.strptime(it['pubDate'],'%a, %d %b %Y %H:%M:%S %z').date()
        except Exception: pub=None
        out.append({'query':q,'title':strip(it.get('title')),'desc':strip(it.get('description')),'pub_date':pub.isoformat() if pub else '', 'link':it.get('link',''), 'originallink':it.get('originallink','')})
    return out

def noisy_for_issue(text, issue_id):
    # Election/personality pieces usually distort cabinet-question prediction.
    if any(t in text for t in NOISE_TERMS) and not any(t in text for t in POLICY_ALLOW):
        return True
    # For labor/jobs, generic campaign job promises are noisy unless tied to labor-market institutions or workplace risk.
    if issue_id=='labor_jobs' and any(t in text for t in ['출마','후보','공약','시장','군수','시의원']) and not any(t in text for t in ['산재','임금체불','하도급','고용노동부','노동','일자리 지표']):
        return True
    # For justice, politician/personality fight is noisy unless tied to institutional reform or concrete crime response.
    if issue_id=='justice_reform' and any(t in text for t in ['추미애','한동훈','조국','하정우','김용남','천하람']) and not any(t in text for t in ['검찰개혁','중수청','수사','범죄','법무부','재판','증거','형사사법']):
        return True
    return False

def key_terms(text):
    toks=re.findall(r'[가-힣A-Za-z0-9]{2,}',text)
    stop=set('관련 대한 하는 되는 있는 없는 정부 대통령 장관 기자 오늘 이번 뉴스 종합 단독 그리고 그러나 이를 통해 우리'.split())
    return [t for t,_ in Counter(t for t in toks if t not in stop).most_common(10)]

def recency_score(pub):
    try: d=dt.date.fromisoformat(pub)
    except Exception: return 0
    age=(dt.date.today()-d).days
    return max(0, 4-age)

def article_relevance(row, cfg, issue_id):
    text=row['title']+' '+row['desc']
    title=row['title']
    score=0
    hits=[s for s in cfg['signals'] if s in text]
    title_hits=[s for s in cfg['signals'] if s in title]
    score += len(hits)*2 + len(title_hits)*2
    score += recency_score(row.get('pub_date',''))
    # Prefer institutional/policy terms over personality/campaign chatter.
    policy_terms=['대책','법개정','면책','지원','책임','안전','예산','제도','개선','점검','브리핑','추진','확대','피해','부담','공급','수급','복구','대응']
    score += sum(2 for t in policy_terms if t in text)
    if issue_id=='school_field_trip':
        score += sum(3 for t in ['교사','면책','현장체험학습','수학여행','소풍','안전사고','법개정'] if t in text)
    if issue_id=='disaster_safety':
        score += sum(3 for t in ['산불','침수','지하차도','오송','재난','안전','통제','실시간'] if t in text)
    if issue_id=='labor_jobs':
        score += sum(3 for t in ['산재','원청','임금체불','하도급','노동부','고용노동부'] if t in text)
        if not any(t in text for t in ['산재','원청','임금체불','하도급','고용노동부','노동부','일자리 지표','고용률','실업률']):
            score -= 10
    if issue_id=='justice_reform':
        score += sum(3 for t in ['중수청','검찰개혁','형사사법','범죄','수사','재판','증거','법무부'] if t in text)
        if not any(t in text for t in ['중수청','검찰개혁','형사사법','범죄','수사','재판','증거','법무부','캄보디아']):
            score -= 10
    # Strongly demote election/personality noise unless direct policy signal is present.
    if any(t in text for t in NOISE_TERMS):
        score -= 8
    return score, hits

def main():
    today=dt.date.today(); since=today-dt.timedelta(days=7)
    packets=[]
    global_seen=set()
    for issue_id,cfg in ISSUES.items():
        rows=[]
        for q in cfg['queries']:
            for r in search(q):
                if r['pub_date'] and r['pub_date']<since.isoformat(): continue
                key=(r['title'],r['originallink'] or r['link'])
                if key in global_seen: continue
                text=r['title']+' '+r['desc']
                if noisy_for_issue(text, issue_id): continue
                # Keep only articles that contain at least one configured policy signal for this issue.
                # This prevents broad query drift such as election/personality articles under labor/justice queries.
                rel, hits = article_relevance(r, cfg, issue_id)
                if not hits:
                    continue
                r['relevance_score']=rel
                r['signal_hits']=hits
                global_seen.add(key); rows.append(r)
        rows.sort(key=lambda r:(r.get('relevance_score',0), recency_score(r.get('pub_date',''))), reverse=True)
        # Drop low-relevance tail after scoring; keeps broad queries from polluting representative articles.
        rows=[r for r in rows if r.get('relevance_score',0) >= 4]
        blob=' '.join(r['title']+' '+r['desc'] for r in rows)
        signal_hits=[s for s in cfg['signals'] if s in blob]
        severity=sum(2 for s in signal_hits if s in ['소풍','수학여행','현장체험학습','면책','산불','침수','전세','물가','의료대란','전공의','산재','범죄'])
        priority=sum(max(0,r.get('relevance_score',0)) for r in rows[:8]) + len(rows) + len(signal_hits)*2 + severity
        synthesis=synthesize_questions(issue_id, signal_hits, priority=priority, count=len(rows))
        packets.append({'issue_id':issue_id,'ministry':cfg['ministry'],'priority':priority,'count':len(rows),'signals':signal_hits,'terms':key_terms(blob),'items':rows[:6],'questions':cfg['questions'],'question_synthesis':synthesis,'pattern_questions':synthesis['questions']})
    packets=[p for p in packets if p['count']>0]
    packets.sort(key=lambda x:(x['priority'],x['count']),reverse=True)
    JSON_OUT.write_text(json.dumps({'generated_at':dt.datetime.now().isoformat(),'since':since.isoformat(),'packets':packets},ensure_ascii=False,indent=2))
    lines=['# Next Cabinet Meeting Radar v2','',f'- generated_at: {dt.datetime.now().isoformat()}','- purpose: 최근 뉴스 기반 대통령 예상 질문 후보 패킷','- warning: 실제 의중 예측이 아니라 회의 전 검토용 이슈 레이더','- algorithm: canonical issue grouping + noise filter + signal/recency/volume priority','']
    for i,p in enumerate(packets[:10],1):
        lines += [f"## {i}. {p['ministry']} — {p['issue_id']}",f"- priority: {p['priority']} / recent articles: {p['count']}",f"- signal hits: {', '.join(p['signals'])}",f"- key terms: {', '.join(p['terms'])}",'',f"### 종합 판단",p.get('question_synthesis',{}).get('diagnosis',''),'','### 예상 질문']
        for q in p.get('question_synthesis',{}).get('questions',[]): lines.append(f"- **{q.get('move_label', q.get('move'))}**: {q['question']}")
        lines += ['','### 후속 지시 후보',f"- {p.get('question_synthesis',{}).get('follow_up','')}",'','### 이슈별 보조 질문']
        for q in p['questions']: lines.append(f'- {q}')
        lines += ['','### 대표 기사']
        for it in p['items'][:6]: lines.append(f"- {it['pub_date']} · score {it.get('relevance_score',0)} · {it['title']}")
        lines.append('')
    OUT.write_text('\n'.join(lines)); print(OUT); print(JSON_OUT)
if __name__=='__main__': main()
