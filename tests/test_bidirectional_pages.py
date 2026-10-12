# copyright by berlonak
# telegram: @Kilax123
"""Bidirectional keyset-paging regression: identical timestamps and around boundaries."""
import json
from fastapi.testclient import TestClient
from tgarchive.app import app, PASS_HASHER
from tgarchive.db import connect,set_config
from tgarchive.importer import import_export


def test_bidirectional_exactly_once(tmp_path,monkeypatch):
    monkeypatch.setenv('TGARCHIVE_DATA_DIR',str(tmp_path / 'db'))
    monkeypatch.setenv('TGARCHIVE_HTTPS','0')
    source=tmp_path/'source';source.mkdir()
    messages=[]
    for i in range(1,178):
        messages.append({'id':i,'date_unixtime':str(1700000000+i//3),
                         'type':'message','text':f'message_{i}'})
    (source/'result.json').write_text(json.dumps({'chats':{'list':[
        {'id':777,'type':'personal_chat','name':'Fixture','messages':messages}]}}),encoding='utf8')
    import_export(source,progress=False)
    with connect() as conn:
        set_config(conn,'password_hash',PASS_HASHER.hash('offline-test-password'))
        conn.commit()
    with TestClient(app) as c:
        assert c.get('/api/chats/1/messages?after_ts=1700000001&after_id=1').status_code==401
        assert c.post('/api/auth/login',json={'password':'offline-test-password'}).status_code==200
        cid=c.get('/api/chats').json()['items'][0]['id']
        allids=[m['id'] for m in c.get(f'/api/chats/{cid}/messages?limit=100').json()['items']]
        assert len(allids)==100
        # From a centered search hit: request every newer and every older page.
        middle=c.get(f'/api/chats/{cid}/messages',params={'around':93,'limit':31})
        # Database IDs are sequential in this fixture. Resolve tg id to avoid assuming internals.
        mid=c.get(f'/api/chats/{cid}/resolve',params={'tg_id':'93'}).json()['id']
        initial=c.get(f'/api/chats/{cid}/messages',params={'around':mid,'limit':31}).json()
        assert initial['has_more'] and initial['has_newer']
        def gather(side):
            result=[m['id'] for m in initial['items']];cursor=result[0 if side=='older' else -1]
            flag='has_more' if side=='older' else 'has_newer'
            more=initial[flag]
            while more:
                m=next(m for m in (initial['items'] if cursor in [x['id'] for x in initial['items']] else last['items']) if m['id']==cursor)
                params=({'before_ts':m['ts'],'before_id':m['id']} if side=='older'
                        else {'after_ts':m['ts'],'after_id':m['id']})
                last=c.get(f'/api/chats/{cid}/messages',params={**params,'limit':11}).json()
                assert last['items'],(side,last)
                ids=[x['id'] for x in last['items']]
                result=ids+result if side=='older' else result+ids
                cursor=result[0 if side=='older' else -1]
                more=last[flag]
            return result
        older=gather('older');newer=gather('newer')
        assert len(set(older))==len(older)
        assert len(set(newer))==len(newer)
        assert older[0]==1 and newer[-1]==177
        assert len(older)==93+15 and len(newer)==177-(93-15)+1
        assert c.get(f'/api/chats/{cid}/messages?after_ts=123').status_code==422
        assert c.get(f'/api/chats/{cid}/messages?after_ts=1&after_id=1&before_ts=1&before_id=1').status_code==422
        assert c.get(f'/api/chats/{cid}/messages?around=987654').status_code==404
