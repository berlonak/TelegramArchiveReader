# copyright by berlonak
# telegram: @Kilax123
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tgarchive.app import PASS_HASHER, app
from tgarchive.db import connect, get_config, initialize, set_config
from tgarchive.importer import import_export, valid_relative_path


@pytest.fixture(autouse=True)
def clear_login_failures():
    from tgarchive.app import FAILED
    FAILED.clear()
    yield
    FAILED.clear()


@pytest.fixture
def archive(tmp_path, monkeypatch):
    monkeypatch.setenv('TGARCHIVE_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('TGARCHIVE_HTTPS', '0')
    source = tmp_path / 'export'
    source.mkdir()
    (source / 'photos').mkdir()
    (source / 'photos' / 'test.jpg').write_bytes(b'JPG public test content')
    content = {'personal_information': {'user_id': 200, 'first_name': 'Пользователь'},
        'chats': {'list': [
            {'name': 'Разговор', 'type': 'personal_chat', 'id': 123, 'messages': [
                {'id': 1, 'type': 'message', 'date': '2023-01-01T10:00:00+00:00', 'date_unixtime': '1672567200', 'from': 'Я', 'from_id': 'user200',
                 'text': 'Привет мир', 'text_entities': [{'type': 'plain', 'text': 'Привет мир'}], 'photo': 'photos/test.jpg'},
                {'id': 2, 'type': 'message', 'date': '2023-01-02T10:00:00+00:00', 'date_unixtime': '1672653600', 'from': 'Друг', 'from_id': 'user123',
                 'text': ['Новый ', {'type': 'bold', 'text': 'проект'}], 'reply_to_message_id': 1},
                {'id': 3, 'type': 'service', 'date': '2023-01-03T10:00:00+00:00', 'action': 'pin_message', 'actor': 'Друг', 'text': ''}
            ]}, {'name':'Новости', 'type':'public_channel', 'id':456, 'messages': [
                {'id': 1, 'type': 'message', 'date': '2023-01-02T10:00:00+00:00', 'text': 'Новости сегодня'}
            ]} ]}}
    (source / 'result.json').write_text(json.dumps(content, ensure_ascii=False), encoding='utf8')
    stats=import_export(source, progress=False)
    assert stats['messages'] == 4
    with connect() as conn:
        set_config(conn, 'password_hash', PASS_HASHER.hash('long-test-password-123'))
        conn.commit()
    with TestClient(app) as client:
        yield client, source


def sign_in(client):
    assert client.post('/api/auth/login', json={'password': 'long-test-password-123'}).status_code == 200


def test_private_routes(archive):
    client, source = archive
    chat = client.get('/api/chats')
    assert chat.status_code == 401
    media = client.get('/api/media/1')
    assert media.status_code == 401
    assert client.post('/api/auth/login', json={'password': 'wrong-password'}).status_code == 401
    sign_in(client)
    assert client.get('/api/auth/me').json()['authenticated']
    assert client.get('/api/stats').json()['messages'] == 4
    assert client.get('/api/stats').json()['me_id'] == '200'
    assert client.post('/api/auth/logout', json={}).status_code == 200
    assert client.get('/api/chats').status_code == 401


def test_chat_search_media_bookmarks(archive):
    client, source = archive
    sign_in(client)
    chats = client.get('/api/chats').json()['items']
    personal = next(c for c in chats if c['category'] == 'personal')
    assert personal['messages_count'] == 3
    cid = personal['id']
    messages = client.get(f'/api/chats/{cid}/messages?limit=2').json()
    assert len(messages['items']) == 2 and messages['has_more']
    assert messages['items'][-1]['body'] == 'pin message'
    all_msgs = client.get(f'/api/chats/{cid}/messages?limit=10').json()['items']
    first = all_msgs[0]
    assert first['media'] and first['media'][0]['kind'] == 'photo'
    media_id = first['media'][0]['id']
    assert client.get(f'/api/media/{media_id}').content == b'JPG public test content'
    assert client.get(f'/api/media/{media_id}?download=true').headers['content-disposition'].startswith('attachment')
    found = client.get('/api/search', params={'q':'Привет'}).json()
    assert found['items'][0]['id'] == first['id']
    assert client.get('/api/search', params={'q':'прое'}).json()['items']  # FTS prefix
    assert client.get('/api/search', params={'q':'новости','has':'photo'}).json()['items'] == []
    assert client.get('/api/search', params={'chat_id':cid,'after':'2023-01-01','before':'2023-01-01'}).json()['items']
    assert client.get('/api/search', params={'q':'" OR *'}).status_code == 200
    assert client.get('/api/gallery?kind=photo').json()['items'][0]['id'] == media_id
    assert client.get(f'/api/chats/{cid}/resolve',params={'tg_id':'1'}).json()['id'] == first['id']
    assert client.post(f'/api/bookmarks/{first["id"]}',json={}).json()['bookmarked']
    assert client.get('/api/bookmarks').json()['items']
    assert client.delete(f'/api/bookmarks/{first["id"]}').json()['bookmarked'] is False
    assert not client.get('/api/bookmarks').json()['items']
    assert client.get(f'/api/messages/{first["id"]}/raw').json()['photo'] == 'photos/test.jpg'


def test_incremental_import_preserves_old_media(archive):
    client, source = archive
    obj=json.loads((source/'result.json').read_text())
    del obj['chats']['list'][0]['messages'][0]['photo']
    obj['chats']['list'][0]['messages'].append({'id':4,'date':'2023-01-04T10:00:00+00:00','text':'Плюс запись'})
    nextdir=source.parent/'new-export';nextdir.mkdir()
    (nextdir/'result.json').write_text(json.dumps(obj,ensure_ascii=False),encoding='utf8')
    info=import_export(nextdir,progress=False)
    assert info['messages'] == 5
    sign_in(client)
    chats=client.get('/api/chats').json()['items']
    cid=next(x['id'] for x in chats if x['category']=='personal')
    assert client.get('/api/stats').json()['messages'] == 5  # deduplicated
    ms=client.get(f'/api/chats/{cid}/messages?limit=10').json()['items']
    assert ms[0]['media'] # preserved from earlier import
    assert client.get('/api/search',params={'q':'test.jpg'}).json()['items']  # still searchable after text-only import
    assert client.get(ms[0]['media'][0]['url']).status_code==200


def test_traversal_prevention(archive, tmp_path):
    client,source=archive
    for path in ('../passwd','/etc/passwd','C:/secrets','http://evil/file','\\\\server\\file','okay/../evil'):
        assert valid_relative_path(path) is None
    assert valid_relative_path('photos\\test.jpg') == 'photos/test.jpg'
    (source/'photos'/'test.jpg').unlink()
    (source/'photos'/'test.jpg').symlink_to('/etc/hosts')
    sign_in(client)
    assert client.get('/api/media/1').status_code==404


def test_origin_and_lockout(archive):
    client,_=archive
    assert client.post('/api/auth/login', json={'password':'long-test-password-123'},headers={'origin':'https://attacker.invalid'}).status_code==403
    for i in range(6):
        assert client.post('/api/auth/login',json={'password':'bad'}).status_code==401
    assert client.post('/api/auth/login',json={'password':'long-test-password-123'}).status_code==429


def test_contacts_index_without_reimport_and_authenticated_search(archive, monkeypatch):
    from tgarchive.importer import import_contacts_only
    client, source = archive
    content = json.loads((source / 'result.json').read_text(encoding='utf8'))
    content['contacts'] = {'list': [
        {'first_name': 'Иван', 'last_name': 'Тест', 'phone_number': '+111-222', 'user_id': 123},
        {'first_name': '<img src=x onerror=alert(1)>', 'phone_number': '%_\\', 'user_id': None},
    ]}
    (source / 'result.json').write_text(json.dumps(content, ensure_ascii=False), encoding='utf8')
    with connect() as conn:
        old_message_count = conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
        old_media_count = conn.execute('SELECT COUNT(*) FROM media').fetchone()[0]
    assert import_contacts_only(source / "result.json") == 2
    # Re-run is idempotent (does not reindex messages/media).
    assert import_contacts_only(source / "result.json") == 2
    with connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0] == old_message_count
        assert conn.execute('SELECT COUNT(*) FROM media').fetchone()[0] == old_media_count
        assert conn.execute('SELECT COUNT(*) FROM contacts').fetchone()[0] == 2
    assert client.get('/api/contacts').status_code == 401
    sign_in(client)
    assert len(client.get('/api/contacts').json()['items']) == 2
    assert len(client.get('/api/contacts', params={'q': 'Ива'}).json()['items']) == 1
    assert len(client.get('/api/contacts', params={'q': '%_\\'}).json()['items']) == 1
    assert len(client.get('/api/contacts', params={'q': "' OR TRUE--"}).json()['items']) == 0
    assert client.get('/api/contacts?limit=1').json()['has_more'] is True
    assert client.get('/api/contacts?offset=1&limit=1').json()['has_more'] is False
    assert client.get('/api/contacts?limit=9999').status_code == 422


def test_ip_headers_are_only_trusted_with_explicit_proxy_switch(monkeypatch):
    from types import SimpleNamespace
    from tgarchive.app import request_ip
    req = SimpleNamespace(client=SimpleNamespace(host='127.0.0.1'), headers={'x-real-ip': '203.0.113.4'})
    monkeypatch.delenv('TGARCHIVE_TRUST_PROXY', raising=False)
    assert request_ip(req) == '127.0.0.1'
    monkeypatch.setenv('TGARCHIVE_TRUST_PROXY', '1')
    assert request_ip(req) == '203.0.113.4'
    bad = SimpleNamespace(client=req.client, headers={'x-real-ip': 'untrusted, spoofed'})
    assert request_ip(bad) == '127.0.0.1'
    from_private_network = SimpleNamespace(client=SimpleNamespace(host='192.0.2.7'), headers=req.headers)
    assert request_ip(from_private_network) == '192.0.2.7'


def test_extra_security_for_contacts_raw_and_downloads(archive):
    from tgarchive.app import FAILED
    FAILED.clear()
    client, _ = archive
    for url in ('/api/contacts', '/api/gallery', '/api/chats/1/messages',
                '/api/media/1', '/api/avatar/1', '/api/messages/1/raw', '/api/stats'):
        assert client.get(url).status_code == 401
    sign_in(client)
    raw = client.get('/api/messages/1/raw')
    assert raw.status_code == 200
    assert raw.headers['cache-control'] == 'private, no-store'
    assert raw.headers['x-content-type-options'] == 'nosniff'
    assert raw.headers['x-frame-options'] == 'DENY'
    assert client.post('/api/bookmarks/1', json={},
                       headers={'origin': 'https://attacker.example'}).status_code == 403
    assert client.post('/api/bookmarks/1', data='{}',
                       headers={'content-type': 'text/plain'}).status_code == 415
    assert client.get('/api/media/1?download=true').headers['content-disposition'].startswith('attachment')
    assert client.get('/api/media/98765432').status_code == 404


def test_portable_media_resolves_only_inside_configured_bundle(archive, monkeypatch, tmp_path):
    import sqlite3
    from fastapi import HTTPException
    from tgarchive.app import safe_file
    client, source = archive
    bundle = tmp_path / 'ready'
    export = bundle / 'exports' / 'first-export' / 'photos'
    export.mkdir(parents=True)
    (export / 'test.jpg').write_bytes(b'photo')
    monkeypatch.setenv('TGARCHIVE_BUNDLE_ROOT', str(bundle))
    with connect() as conn:
        conn.execute("UPDATE imports SET root=? WHERE id=1", ('@TGARCHIVE_BUNDLE@/exports/first-export',))
        conn.commit()
        assert safe_file(conn, 1, 'photos/test.jpg').read_bytes() == b'photo'
        for path in ('../../private.dat', '/etc/passwd', 'C:/windows.ini', '../photos/test.jpg'):
            with pytest.raises(HTTPException):
                safe_file(conn, 1, path)
        conn.execute('UPDATE imports SET root=? WHERE id=1', ('@TGARCHIVE_BUNDLE@/exports/../secrets',))
        conn.commit()
        with pytest.raises(HTTPException):
            safe_file(conn, 1, 'photos/test.jpg')


def test_sender_filter_escapes_like_wildcards_and_password_is_bounded(archive):
    client, _ = archive
    assert client.post('/api/auth/login', json={'password': 'x' * 1025}).status_code == 422
    sign_in(client)
    assert client.get('/api/search', params={'sender': 'Др'}).json()['items']
    assert client.get('/api/search', params={'sender': '%'}).json()['items'] == []
    assert client.get('/api/search', params={'sender': '_'}).json()['items'] == []


def test_https_configuration_script_is_present():
    script = (Path(__file__).parents[1] / 'deploy' / 'configure-https-ip.sh').read_text(encoding='utf-8')
    assert '--ip-address' in script and '--preferred-profile shortlived' in script
    assert 'proxy_set_header X-Real-IP' in script
    assert '127.0.0.1:8000' in script
