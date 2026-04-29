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
  'questions':['현장체험학습 축소의 원인이 안전사고 우려인지, 교사 형사책임 부담인지, 비용 문제인지 구분해 보고했는가?','교사 개인에게 책임이 과도하게 집중되지 않도록 면책·보험·안전요원·표준계약을 어떻게 설계할 것인가?','소풍·수학여행을 가는 학교와 못 가는 학교 사이 교육 기회 격차를 어떻게 줄일 것인가?']},
 'disaster_safety': {
  'ministry':'행정안전부','queries':['산불 재난 안전','행안부 재난 안전','침수 지하차도 안전','화재 재난 안전'],
  'signals':['산불','재난','안전','화재','침수','지하차도','오송','행안부'],
  'questions':['최근 재난·안전 이슈에서 현장 책임과 국가 지원의 경계가 명확한가?','지자체 대응 역량이 부족한 곳을 어떻게 보강할 것인가?','이번 주 바로 점검해야 할 취약 지점과 국민 안내 체계는 무엇인가?']},
 'real_estate': {
  'ministry':'국토교통부','queries':['부동산 공급 전세','전월세 시장 불안','주택 공급 대책'],
  'signals':['부동산','주택','전세','월세','공급','정비사업','아파트'],
  'questions':['공급 대책이 실제 입주 가능 물량으로 이어지는 시점은 언제인가?','전월세 시장 불안과 실수요자 부담을 선제적으로 점검했는가?','수도권과 지방에서 정책 효과가 다르게 나타나는 부분은 무엇인가?']},
 'prices_livelihood': {
  'ministry':'기획재정부','queries':['물가 민생 지원','고유가 지원금 물가','민생경제 물가 부담'],
  'signals':['물가','민생','지원','고유가','경제','부담','추경','예산'],
  'questions':['물가·민생 부담이 어느 계층에 집중되는지 최신 지표로 확인했는가?','직접 지원, 보증, 세제, 예산 집행 중 어떤 수단이 가장 빠르고 효과적인가?','추가 재정 소요와 정책 효과를 비교해 설명할 수 있는가?']},
 'finance_rates': {
  'ministry':'금융위원회','queries':['금융 대출 금리','중금리대출 확대','서민금융 대출 부담'],
  'signals':['금융','대출','금리','은행','중금리','서민금융','취약계층'],
  'questions':['금리·대출 부담이 취약계층과 실수요자에게 어떻게 전가되고 있는가?','금융 지원이 투기 수요가 아니라 생산적·민생 분야로 흐르도록 장치를 뒀는가?']},
 'labor_jobs': {
  'ministry':'고용노동부','queries':['청년 일자리','산재 원청 책임','임금체불 하도급'],
  'signals':['일자리','청년','산재','원청','임금체불','하도급','노동'],
  'questions':['일자리 지표와 현장 체감 사이 괴리를 어떻게 설명할 것인가?','산재·임금체불·하도급 문제에서 원청 책임을 어떻게 실효화할 것인가?']},
 'justice_reform': {
  'ministry':'법무부','queries':['검찰개혁 법무부','범죄 수사 법무부','캄보디아 범죄 한국인'],
  'signals':['검찰','개혁','범죄','수사','법무부','재판','증거'],
  'questions':['범죄 대응 과정에서 증거 확보와 재판 가능성은 충분히 점검했는가?','부처 간 수사·외교·행정 협업 체계는 명확한가?']},
 'medical': {
  'ministry':'보건복지부','queries':['의료대란 전공의 복귀','의대 전공의 복귀','비상진료체계'],
  'signals':['의료','전공의','의대','비상진료','환자','병원'],
  'questions':['현장 의료 공백이나 환자 불편이 실제로 어느 정도인지 최신 지표로 확인했는가?','관계 부처와 협의가 끝난 쟁점과 아직 남은 쟁점은 무엇인가?','국민이 체감할 수 있는 단기 대책과 구조개혁 과제를 구분해 보고할 수 있는가?']},
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
        for q in p.get('question_synthesis',{}).get('questions',[]): lines.append(f"- **{q['move']}**: {q['question']}")
        lines += ['','### 후속 지시 후보',f"- {p.get('question_synthesis',{}).get('follow_up','')}",'','### 이슈별 보조 질문']
        for q in p['questions']: lines.append(f'- {q}')
        lines += ['','### 대표 기사']
        for it in p['items'][:6]: lines.append(f"- {it['pub_date']} · score {it.get('relevance_score',0)} · {it['title']}")
        lines.append('')
    OUT.write_text('\n'.join(lines)); print(OUT); print(JSON_OUT)
if __name__=='__main__': main()
